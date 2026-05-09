from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class HealthResponse(BaseModel):
    """Contract for GET /health."""

    status: Literal["ok"] = "ok"


class Role(str, Enum):
    user = "user"
    assistant = "assistant"


class ChatMessage(BaseModel):
    role: Role
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)


class RecommendationItem(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    url: HttpUrl
    test_type: str = Field(min_length=1, max_length=20)


class ChatResponse(BaseModel):
    reply: str
    recommendations: list[RecommendationItem]
    end_of_conversation: bool


class Intent(str, Enum):
    clarify = "clarify"
    recommend = "recommend"
    refine = "refine"
    compare = "compare"
    refuse = "refuse"


class SafetyDecision(BaseModel):
    refuse: bool = False
    reason: Optional[str] = None
    category: Optional[
        Literal[
            "prompt_injection",
            "legal",
            "general_hiring_advice",
            "cheating",
            "privacy",
            "out_of_scope",
        ]
    ] = None


class NeedState(BaseModel):
    intent: Intent
    raw_text: str

    role_title: Optional[str] = None
    seniority: Optional[str] = None
    skills: list[str] = Field(default_factory=list)
    desired_test_types: list[str] = Field(default_factory=list)
    target_job_levels: list[str] = Field(default_factory=list)
    max_duration_minutes: Optional[int] = None
    languages: list[str] = Field(default_factory=list)
    remote_required: Optional[bool] = None

    comparison_targets: list[str] = Field(default_factory=list)

    # Conversation closure (for end_of_conversation); set in build_state from message history.
    user_signaled_done: bool = False
    prior_assistant_substantive: bool = False

    debug: dict[str, Any] = Field(default_factory=dict)


class CatalogItem(BaseModel):
    name: str
    url: HttpUrl
    test_type: str

    description: Optional[str] = None
    job_levels: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    duration_minutes: Optional[int] = None
    remote_testing: Optional[bool] = None
    adaptive: Optional[bool] = None

    # Source metadata
    solution_type: Optional[str] = None
    scraped_at: Optional[str] = None

