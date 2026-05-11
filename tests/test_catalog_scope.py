from __future__ import annotations

import app.catalog as catalog


def test_multi_key_individual_assessment_included() -> None:
    assert catalog._is_individual_test_solution(
        "Global Skills Assessment",
        ["Competencies", "Knowledge & Skills"],
        "Assessment that measures skills.",
    )


def test_multi_key_solution_excluded_from_scope() -> None:
    assert not catalog._is_individual_test_solution(
        "Entry Level Sales Solution",
        ["Competencies", "Personality & Behavior"],
        "Some description",
    )


def test_precise_fit_solution_name_excluded() -> None:
    assert not catalog._is_individual_test_solution(
        "Retail Sales Solution",
        ["Personality & Behavior"],
        "The Precise Fit Retail Sales Solution is for sellers.",
    )


def test_plain_individual_product_included() -> None:
    assert catalog._is_individual_test_solution(
        "Java 8 (New)",
        ["Knowledge & Skills"],
        "Multi-choice test that measures Java.",
    )
