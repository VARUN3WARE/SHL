from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from app.gemini_extract import fetch_groq_hints
from app.models import ChatMessage, Intent, NeedState, Role


def test_fetch_groq_hints_non_200_returns_none(monkeypatch) -> None:
    monkeypatch.setenv("USE_GROQ", "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    client_cm = MagicMock()
    client_cm.post.return_value = MagicMock(status_code=429, text="rate limited")
    client_cm.__enter__.return_value = client_cm
    client_cm.__exit__.return_value = None

    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: client_cm)

    msgs = [ChatMessage(role=Role.user, content="Need Java screening.")]
    state = NeedState(intent=Intent.recommend, raw_text="java")
    assert fetch_groq_hints(msgs, state) is None


def test_fetch_groq_hints_parses_json_body(monkeypatch) -> None:
    monkeypatch.setenv("USE_GROQ", "true")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"retrieval_query":null,"skills":["Leadership"],"seniority":null,"desired_test_types":["P"],"max_duration_minutes":null}'
                }
            }
        ]
    }
    client_cm = MagicMock()
    client_cm.post.return_value = resp
    client_cm.__enter__.return_value = client_cm
    client_cm.__exit__.return_value = None

    monkeypatch.setattr(httpx, "Client", lambda *a, **kw: client_cm)

    msgs = [ChatMessage(role=Role.user, content="Personality for leaders.")]
    state = NeedState(intent=Intent.recommend, raw_text="leaders")
    hints = fetch_groq_hints(msgs, state)
    assert hints is not None
    assert "Leadership" in hints.skills
    assert "P" in hints.desired_test_types
