from __future__ import annotations

from app.gemini_extract import GeminiNeedHints, merge_hints
from app.models import Intent, NeedState


def test_merge_hints_appends_retrieval_and_merges_skills() -> None:
    base = NeedState(intent=Intent.recommend, raw_text="Hiring a developer.")
    hints = GeminiNeedHints(
        retrieval_query="Emphasis on Java backend and stakeholder communication.",
        skills=["Java", "communication"],
        desired_test_types=["K", "P"],
    )
    merged = merge_hints(base, hints)
    assert "Java backend" in merged.raw_text
    assert "Java" in merged.skills
    assert "K" in merged.desired_test_types
    assert "P" in merged.desired_test_types
    assert "gemini_hints" in merged.debug
