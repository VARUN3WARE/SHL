from __future__ import annotations

from app.gemini_extract import fetch_gemini_hints
from app.models import ChatMessage, Intent, NeedState, Role


def test_fetch_gemini_hints_unparseable_json_returns_none(monkeypatch) -> None:
    monkeypatch.setenv("USE_GEMINI", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    class FakeResp:
        text = "not valid json {{{"

    class FakeModel:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def generate_content(self, prompt: str) -> FakeResp:
            return FakeResp()

    import google.generativeai as genai

    monkeypatch.setattr(genai, "configure", lambda **kwargs: None)
    monkeypatch.setattr(genai, "GenerativeModel", FakeModel)

    msgs = [ChatMessage(role=Role.user, content="Need a Java developer assessment.")]
    state = NeedState(intent=Intent.recommend, raw_text="Java developer")
    assert fetch_gemini_hints(msgs, state) is None
