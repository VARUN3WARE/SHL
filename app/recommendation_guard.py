from __future__ import annotations

from app.catalog import Catalog
from app.models import CatalogItem, RecommendationItem

MAX_RECOMMENDATIONS = 10


def diversify_ranked_items(
    ranked: list[CatalogItem],
    *,
    family_keyword: str = "opq",
    max_per_family: int = 4,
    max_total: int = MAX_RECOMMENDATIONS,
) -> list[CatalogItem]:
    """
    Cap how many recommendations share the same name family (e.g. OPQ reports)
    so Recall@10-style lists are not ten near-duplicates; backfill from the rest of the ranking.
    """
    kw = family_keyword.lower()
    out: list[CatalogItem] = []
    seen: set[str] = set()
    family_hits = 0

    for it in ranked:
        if len(out) >= max_total:
            break
        u = str(it.url)
        if u in seen:
            continue
        is_family = kw in it.name.lower()
        if is_family and family_hits >= max_per_family:
            continue
        if is_family:
            family_hits += 1
        seen.add(u)
        out.append(it)

    if len(out) < max_total:
        for it in ranked:
            if len(out) >= max_total:
                break
            u = str(it.url)
            if u in seen:
                continue
            seen.add(u)
            out.append(it)

    return out[:max_total]


def catalog_rows_to_recommendations(items: list[CatalogItem]) -> list[RecommendationItem]:
    """Build recommendation DTOs only from canonical catalog rows (max 10)."""
    out: list[RecommendationItem] = []
    seen: set[str] = set()
    for it in items[:MAX_RECOMMENDATIONS]:
        u = str(it.url)
        if u in seen:
            continue
        seen.add(u)
        out.append(
            RecommendationItem(name=it.name, url=it.url, test_type=it.test_type)
        )
        if len(out) >= MAX_RECOMMENDATIONS:
            break
    return out


def bind_recommendations_to_catalog(
    catalog: Catalog, candidates: list[RecommendationItem]
) -> list[RecommendationItem]:
    """
    Keep only recommendations whose URL and name exist exactly on a catalog row.
    Deterministic; order preserved; cap at MAX_RECOMMENDATIONS.
    """
    out: list[RecommendationItem] = []
    seen_urls: set[str] = set()
    for cand in candidates:
        if len(out) >= MAX_RECOMMENDATIONS:
            break
        url_s = str(cand.url).rstrip("/")
        row = catalog.by_url.get(url_s) or catalog.by_url.get(str(cand.url))
        if row is None:
            # try with trailing slash normalization
            for k, v in catalog.by_url.items():
                if k.rstrip("/") == url_s:
                    row = v
                    break
        if row is None:
            continue
        if row.name != cand.name:
            continue
        u = str(row.url)
        if u in seen_urls:
            continue
        seen_urls.add(u)
        out.append(
            RecommendationItem(name=row.name, url=row.url, test_type=row.test_type)
        )
    return out
