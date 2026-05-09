from __future__ import annotations

from dataclasses import dataclass

from app.catalog import Catalog
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


def rank(catalog: Catalog, need: NeedState, top_k: int = 10) -> list[ScoredItem]:
    """
    Deterministic ranking:
    - token overlap between need text and item fields
    - soft boosts for test_type preferences, duration constraint, languages, remote flag
    """
    q = need.raw_text
    q_tokens = set(tokenize(q))
    q_bow = bag_of_words(q)

    preferred_types = set([t.upper() for t in need.desired_test_types])
    preferred_langs = set([l.lower() for l in need.languages])
    target_job_levels = set([j.lower() for j in (need.target_job_levels or [])])
    leadership_intent = any(s.lower() == "leadership" for s in (need.skills or [])) or ("leadership" in need.raw_text.lower())
    looks_technical = any(
        kw in need.raw_text.lower()
        for kw in ["java", "python", "javascript", "react", "node", "sql", "c++", "developer", "engineer", "coding"]
    )

    scored: list[ScoredItem] = []
    for it in catalog.items:
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
            # For leadership selection, personality/competency instruments and reports are typically more relevant
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

        scored.append(ScoredItem(item=it, score=score, why=why))

    scored.sort(key=lambda s: s.score, reverse=True)
    return scored[: max(1, min(top_k, 10))]


def find_by_name_fuzzy(catalog: Catalog, name_like: str) -> CatalogItem | None:
    target = name_like.strip().lower()
    if not target:
        return None
    if target in catalog.by_name_lower:
        return catalog.by_name_lower[target]

    # fallback: contains match
    for it in catalog.items:
        if target in it.name.lower():
            return it
    return None

