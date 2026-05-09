"""Contract tests: health + /chat always matches ChatResponse."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import ChatResponse, HealthResponse

client = TestClient(app)


def test_health_ok_and_shape() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    body = HealthResponse.model_validate(r.json())
    assert body.status == "ok"


def test_chat_invalid_body_still_chat_response() -> None:
    r = client.post("/chat", json={})
    assert r.status_code == 200
    ChatResponse.model_validate(r.json())


def test_chat_minimal_messages_chat_response() -> None:
    r = client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "I need an assessment for a software engineer."}]},
    )
    assert r.status_code == 200
    out = ChatResponse.model_validate(r.json())
    assert isinstance(out.reply, str)
    assert isinstance(out.recommendations, list)
    assert isinstance(out.end_of_conversation, bool)
    for item in out.recommendations:
        assert item.name
        assert str(item.url).startswith("http")
        assert item.test_type
