from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.catalog import load_catalog
from app.models import ChatRequest, ChatResponse, HealthResponse
from app.responses import respond
from app.state import build_state

logger = logging.getLogger(__name__)

app = FastAPI(title="SHL Conversational Assessment Recommender")

# Assignment-style SLA: keep /chat under typical evaluator limits (leave margin).
CHAT_PROCESSING_TIMEOUT_S = 29.0


def _is_chat_path(request: Request) -> bool:
    return request.url.path.rstrip("/").endswith("/chat")


def _chat_schema_error_response(reply: str) -> JSONResponse:
    """Always return assignment ChatResponse JSON (even on bad input / errors)."""
    body = ChatResponse(
        reply=reply,
        recommendations=[],
        end_of_conversation=False,
    ).model_dump(mode="json")
    return JSONResponse(status_code=status.HTTP_200_OK, content=body)


@app.middleware("http")
async def chat_processing_time_limit(request: Request, call_next):
    if request.method == "POST" and _is_chat_path(request):
        try:
            return await asyncio.wait_for(
                call_next(request), timeout=CHAT_PROCESSING_TIMEOUT_S
            )
        except asyncio.TimeoutError:
            logger.warning(
                "POST /chat exceeded %.1fs processing budget", CHAT_PROCESSING_TIMEOUT_S
            )
            return _chat_schema_error_response(
                "The request took too long to process. Try again with fewer messages "
                "or a shorter conversation history."
            )
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def chat_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    if _is_chat_path(request):
        logger.warning("POST /chat validation error: %s", exc.errors())
        return _chat_schema_error_response(
            "Request did not match the expected format. Send JSON with a non-empty "
            "`messages` array of {role, content} objects (role: user or assistant)."
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def chat_unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    if _is_chat_path(request):
        logger.exception("POST /chat unhandled error")
        return _chat_schema_error_response(
            "Something went wrong processing your request. Please try again."
        )
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    catalog = load_catalog()
    state = build_state(req.messages)
    return respond(catalog, state)

