from __future__ import annotations

from fastapi import FastAPI

from app.catalog import load_catalog
from app.models import ChatRequest, ChatResponse
from app.responses import respond
from app.state import build_state


app = FastAPI(title="SHL Conversational Assessment Recommender")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    catalog = load_catalog()
    state = build_state(req.messages)
    return respond(catalog, state)

