from __future__ import annotations

from app.catalog import Catalog
from app.models import CatalogItem, Intent, NeedState
from app.retrieval import rank, rank_hybrid


def _tiny_catalog() -> Catalog:
    return Catalog(
        [
            CatalogItem(
                name="Java 8 (New)",
                url="https://www.shl.com/products/product-catalog/view/java-8-new/",
                test_type="K",
                description="Knowledge test for Java programming language.",
            ),
            CatalogItem(
                name="Occupational Personality Questionnaire OPQ32r",
                url="https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/",
                test_type="P",
                description="Workplace personality and behavioral style questionnaire.",
            ),
        ]
    )


def test_rank_hybrid_falls_back_when_no_semantic() -> None:
    cat = _tiny_catalog()
    need = NeedState(
        intent=Intent.recommend,
        raw_text="We need Java technical screening for developers.",
    )
    a = rank(cat, need, top_k=10)
    b = rank_hybrid(cat, need, None, top_k=10)
    assert [x.item.url for x in a] == [x.item.url for x in b]


def test_rank_hybrid_boosts_high_semantic_item() -> None:
    cat = _tiny_catalog()
    need = NeedState(
        intent=Intent.recommend,
        raw_text="leadership personality assessment for executives",
        skills=["leadership"],
    )
    sem = {
        "https://www.shl.com/products/product-catalog/view/occupational-personality-questionnaire-opq32r/": 0.99,
        "https://www.shl.com/products/product-catalog/view/java-8-new/": 0.1,
    }
    out = rank_hybrid(cat, need, sem, top_k=2)
    assert "opq32r" in str(out[0].item.url).lower()
