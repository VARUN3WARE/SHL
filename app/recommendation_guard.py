from __future__ import annotations

from app.catalog import Catalog
from app.models import CatalogItem, RecommendationItem

MAX_RECOMMENDATIONS = 10


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
