from __future__ import annotations

from dataclasses import dataclass

from app.catalog import Catalog
from app.config import hybrid_weight_lexical, hybrid_weight_semantic
from app.models import CatalogItem, NeedState
from app.utils_text import bag_of_words, jaccard, tokenize


@dataclass(frozen=True)
class ScoredItem:
    item: CatalogItem
    score: float
    why: list[str]


def _field_text(i: CatalogItem) -> str:
    parts = [i.name]
    if i.description:
        parts.append(i.description)
    parts.extend(i.job_levels)
    parts.extend(i.languages)
    return " ".join([p for p in parts if p])


def lexical_score_item(need: NeedState, it: CatalogItem) -> tuple[float, list[str]]:
    """Single-item lexical relevance (same formula as `rank`)."""
    q = need.raw_text
    q_tokens = set(tokenize(q))
    q_bow = bag_of_words(q)

    preferred_types = set([t.upper() for t in need.desired_test_types])
    preferred_langs = set([l.lower() for l in need.languages])
    target_job_levels = set([j.lower() for j in (need.target_job_levels or [])])
    leadership_intent = any(s.lower() == "leadership" for s in (need.skills or [])) or (
        "leadership" in need.raw_text.lower()
    )
    looks_technical = any(
        kw in need.raw_text.lower()
        for kw in [
            "java",
            "python",
            "javascript",
            "react",
            "node",
            "sql",
            "c++",
            "developer",
            "engineer",
            "coding",
        ]
    )

    why: list[str] = []
    text = _field_text(it)
    it_tokens = set(tokenize(text))

    overlap = jaccard(q_tokens, it_tokens)
    bow_score = sum(min(q_bow[w], 2) for w in it_tokens) / max(10.0, len(it_tokens))
    score = 2.0 * overlap + 3.0 * bow_score

    if preferred_types:
        if it.test_type.upper() in preferred_types:
            score += 0.6
            why.append(f"matches test_type={it.test_type}")
        else:
            score -= 0.1

    if leadership_intent:
        if it.test_type.upper() in {"P", "C", "D", "A"}:
            score += 0.25
        if not looks_technical and it.test_type.upper() == "K":
            score -= 0.7
            why.append("penalize technical skill test for leadership intent")
        if "opq" in it.name.lower():
            score += 0.5
            why.append("OPQ match")

    if need.max_duration_minutes is not None and it.duration_minutes is not None:
        if it.duration_minutes <= need.max_duration_minutes:
            score += 0.3
            why.append(f"duration {it.duration_minutes}m <= {need.max_duration_minutes}m")
        else:
            score -= 0.4
            why.append(f"duration {it.duration_minutes}m > {need.max_duration_minutes}m")

    if preferred_langs and it.languages:
        it_langs = set([l.lower() for l in it.languages])
        if it_langs & preferred_langs:
            score += 0.2
            why.append("language match")

    if target_job_levels and it.job_levels:
        it_levels = set([j.lower() for j in it.job_levels])
        if it_levels & target_job_levels:
            score += 0.25
            why.append("job level match")

    if need.remote_required is True and it.remote_testing is True:
        score += 0.15
        why.append("remote testing")
    if need.remote_required is False and it.remote_testing is False:
        score += 0.05

    return score, why


def rank(catalog: Catalog, need: NeedState, top_k: int = 10) -> list[ScoredItem]:
    """
    Deterministic ranking over full catalog (lexical only).
    """
    scored: list[ScoredItem] = []
    for it in catalog.items:
        score, why = lexical_score_item(need, it)
        scored.append(ScoredItem(item=it, score=score, why=why))

    scored.sort(key=lambda s: s.score, reverse=True)
    cap = max(1, min(top_k, len(scored), 500))
    return scored[:cap]


def rank_hybrid(
    catalog: Catalog,
    need: NeedState,
    semantic_url_scores: dict[str, float] | None,
    *,
    k_sem: int = 40,
    k_lex: int = 40,
    top_k: int = 40,
) -> list[ScoredItem]:
    """
    Fuse local semantic similarity (precomputed index) with lexical scores.
    If `semantic_url_scores` is empty/None, falls back to lexical `rank`.
    """
    if not semantic_url_scores:
        return rank(catalog, need, top_k=top_k)

    w_sem = hybrid_weight_semantic()
    w_lex = hybrid_weight_lexical()
    s_sum = w_sem + w_lex
    if s_sum > 0:
        w_sem, w_lex = w_sem / s_sum, w_lex / s_sum

    # Lexical top-K for candidate pool
    lex_ranked = rank(catalog, need, top_k=max(k_lex, top_k))
    lex_top = lex_ranked[:k_lex]

    # Semantic URLs (top k_sem already in dict order not guaranteed — take top by score)
    sem_sorted = sorted(semantic_url_scores.items(), key=lambda x: -x[1])[:k_sem]

    candidates: dict[str, CatalogItem] = {}
    for s in lex_top:
        candidates[str(s.item.url)] = s.item
    for url, _ in sem_sorted:
        u = url.rstrip("/")
        it = catalog.by_url.get(url) or catalog.by_url.get(u)
        if it is None:
            for key, val in catalog.by_url.items():
                if key.rstrip("/") == u:
                    it = val
                    break
        if it is not None:
            candidates[str(it.url)] = it

    if not candidates:
        return rank(catalog, need, top_k=top_k)

    lex_raw: list[float] = []
    fused_rows: list[tuple[CatalogItem, float, list[str]]] = []
    for url, it in candidates.items():
        lx, why = lexical_score_item(need, it)
        lex_raw.append(lx)
        sem_sc = semantic_url_scores.get(url, 0.0)
        # also try alternate url form
        if sem_sc == 0.0:
            for su, sc in semantic_url_scores.items():
                if su.rstrip("/") == url.rstrip("/"):
                    sem_sc = sc
                    break
        fused_rows.append((it, lx, why, sem_sc))

    lo, hi = min(lex_raw), max(lex_raw)
    span = hi - lo + 1e-9

    out: list[ScoredItem] = []
    for it, lx, why, sem_sc in fused_rows:
        lex_norm = (lx - lo) / span
        fuse = w_sem * float(sem_sc) + w_lex * lex_norm
        why_h = list(why)
        why_h.append(f"hybrid sem={sem_sc:.3f} lex_norm={lex_norm:.3f}")
        out.append(ScoredItem(item=it, score=fuse, why=why_h))

    out.sort(key=lambda s: s.score, reverse=True)
    return out[: max(1, min(top_k, len(out)))]


def find_by_name_fuzzy(catalog: Catalog, name_like: str) -> CatalogItem | None:
    target = name_like.strip().lower()
    if not target:
        return None
    if target in catalog.by_name_lower:
        return catalog.by_name_lower[target]

    for it in catalog.items:
        if target in it.name.lower():
            return it
    return None
