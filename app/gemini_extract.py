from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout

from pydantic import BaseModel, Field, field_validator

from app.config import gemini_api_key, gemini_model, gemini_timeout_s, use_gemini
from app.models import ChatMessage, Intent, NeedState

logger = logging.getLogger(__name__)


class GeminiNeedHints(BaseModel):
    """Structured hints only — no product names or URLs from the model."""

    retrieval_query: str | None = Field(default=None, max_length=700)
    skills: list[str] = Field(default_factory=list, max_length=24)
    seniority: str | None = Field(default=None, max_length=80)
    desired_test_types: list[str] = Field(default_factory=list, max_length=8)
    max_duration_minutes: int | None = None

    @field_validator("desired_test_types", mode="before")
    @classmethod
    def upper_types(cls, v: object) -> list[str]:
        if v is None or v == []:
            return []
        if not isinstance(v, list):
            return []
        out: list[str] = []
        allowed = {"P", "K", "A", "S", "SJ", "C", "D", "U"}
        for x in v:
            s = str(x).strip().upper()[:4]
            if s in allowed:
                out.append(s)
        return out[:8]


def _format_transcript(messages: list[ChatMessage]) -> str:
    lines: list[str] = []
    for m in messages[-14:]:
        lines.append(f"{m.role.value}: {m.content}")
    return "\n".join(lines)[:14000]


def _parse_json_object(raw: str) -> dict[str, object] | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", raw)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


def fetch_gemini_hints(messages: list[ChatMessage], rule_state: NeedState) -> GeminiNeedHints | None:
    if not use_gemini():
        return None
    key = gemini_api_key()
    if not key:
        return None

    try:
        import google.generativeai as genai
    except ImportError:
        logger.warning("google-generativeai not installed")
        return None

    genai.configure(api_key=key)
    model = genai.GenerativeModel(
        gemini_model(),
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )

    transcript = _format_transcript(messages)
    prompt = (
        "You help retrieve SHL assessments. Output ONLY valid JSON matching this shape:\n"
        '{"retrieval_query": string or null, "skills": string[], "seniority": string or null, '
        '"desired_test_types": string[], "max_duration_minutes": number or null}\n'
        "desired_test_types must be zero or more of: P, K, A, S (personality, knowledge/skills, ability, simulation).\n"
        "Do NOT name SHL products, reports, or URLs. Use only the conversation.\n\n"
        f"Conversation:\n{transcript}\n\n"
        f"Rule-based draft (may be incomplete): role={rule_state.role_title!r} "
        f"seniority={rule_state.seniority!r} skills={rule_state.skills!r}\n"
    )

    def _call():
        return model.generate_content(prompt)

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_call)
            resp = fut.result(timeout=gemini_timeout_s())
    except FuturesTimeout:
        logger.warning("Gemini request timed out after %ss", gemini_timeout_s())
        return None
    except Exception:
        logger.exception("Gemini request failed")
        return None

    try:
        text = (resp.text or "").strip()
    except Exception:
        logger.warning("Gemini response had no text")
        return None

    data = _parse_json_object(text)
    if not data:
        logger.warning("Gemini returned unparseable JSON")
        return None
    try:
        return GeminiNeedHints.model_validate(data)
    except Exception:
        logger.warning("Gemini JSON failed validation: %s", text[:200])
        return None


def merge_hints(state: NeedState, hints: GeminiNeedHints) -> NeedState:
    u = state.model_copy(deep=True)
    if hints.retrieval_query and hints.retrieval_query.strip():
        add = hints.retrieval_query.strip()
        u.raw_text = (u.raw_text + "\n" + add).strip()[:20000]

    if hints.skills:
        merged = list(dict.fromkeys([*(u.skills or []), *[s.strip() for s in hints.skills if s.strip()]]))
        u.skills = merged[:14]

    if hints.seniority and hints.seniority.strip() and not u.seniority:
        u.seniority = hints.seniority.strip()[:80]

    if hints.desired_test_types:
        merged_t = sorted(set([*(u.desired_test_types or []), *hints.desired_test_types]))
        u.desired_test_types = merged_t[:8]

    if hints.max_duration_minutes is not None and u.max_duration_minutes is None:
        if 1 <= hints.max_duration_minutes <= 300:
            u.max_duration_minutes = hints.max_duration_minutes

    u.debug["gemini_hints"] = hints.model_dump()
    return u


def apply_gemini_hints(state: NeedState, messages: list[ChatMessage]) -> NeedState:
    if state.intent in (Intent.refuse, Intent.compare):
        return state
    hints = fetch_gemini_hints(messages, state)
    if hints is None:
        return state
    return merge_hints(state, hints)
