from __future__ import annotations

from app.models import CatalogItem
from app.recommendation_guard import diversify_ranked_items


def test_diversify_caps_opq_family_then_backfills() -> None:
    opq = [
        CatalogItem(
            name=f"OPQ Report {i}",
            url=f"https://www.shl.com/products/product-catalog/view/opq-{i}/",
            test_type="P",
        )
        for i in range(8)
    ]
    other = [
        CatalogItem(
            name="Enterprise Leadership Report 1.0",
            url="https://www.shl.com/products/product-catalog/view/enterprise-leadership-report/",
            test_type="P",
        ),
        CatalogItem(
            name="Java 8 (New)",
            url="https://www.shl.com/products/product-catalog/view/java-8-new/",
            test_type="K",
        ),
    ]
    ranked = opq + other
    out = diversify_ranked_items(ranked, max_per_family=3, max_total=5)
    assert len(out) == 5
    assert sum(1 for x in out if "opq" in x.name.lower()) <= 3
