from __future__ import annotations

from app.models import ChatMessage, Intent
from app.state import ASSIGNMENT_MAX_MESSAGES, TURN_BUDGET_FORCE_RECOMMEND_AT_LEN, build_state


def test_evaluator_turn_cap_constants() -> None:
    assert ASSIGNMENT_MAX_MESSAGES == 8
    assert TURN_BUDGET_FORCE_RECOMMEND_AT_LEN == 7


def test_seventh_message_forces_recommend_when_would_otherwise_clarify() -> None:
    messages = [
        ChatMessage(role="user", content="I need an assessment."),
        ChatMessage(role="assistant", content="What role or skill area are you hiring for?"),
        ChatMessage(role="user", content="Not sure yet."),
        ChatMessage(role="assistant", content="What role or skill area are you hiring for?"),
        ChatMessage(role="user", content="Still figuring it out."),
        ChatMessage(role="assistant", content="What role or skill area are you hiring for?"),
        ChatMessage(role="user", content="Anything really."),
    ]
    assert len(messages) == 7
    state = build_state(messages)
    assert state.intent == Intent.recommend
    assert state.debug.get("turn_budget_forced_recommend") is True


def test_first_message_vague_stays_clarify() -> None:
    state = build_state(
        [ChatMessage(role="user", content="I need an assessment.")],
    )
    assert state.intent == Intent.clarify
    assert state.debug.get("turn_budget_forced_recommend") is not True
