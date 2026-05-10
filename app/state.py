from __future__ import annotations

import re
from typing import Iterable

from app.models import ChatMessage, Intent, NeedState
from app.safety import classify_safety
from app.utils_text import extract_int_minutes, normalize_space


# Evaluator caps the whole conversation at 8 messages (user + assistant). Avoid burning
# the last turn on a clarification — the harness may not get another user reply.
ASSIGNMENT_MAX_MESSAGES = 8
# If history already has this many messages, do not return clarify-only; recommend best-effort.
TURN_BUDGET_FORCE_RECOMMEND_AT_LEN = ASSIGNMENT_MAX_MESSAGES - 1

_COMPARE_RE = re.compile(
    r"\b(compare|difference between|vs\.?|versus)\b", re.IGNORECASE
)

# User appears to close the task (used with prior substantive assistant turn).
_CLOSURE_RE = re.compile(
    r"^(thanks|thank you)\b"
    r"|\bthat'?s perfect\b"
    r"|\bperfect,?\s+that'?s what we need\b"
    r"|\bthat covers it\b"
    r"|\bthat works\b"
    r"|\ball set\b"
    r"|\bwe'?re good\b"
    r"|\bconfirmed\.?\b"
    r"|\bwe'?re done\b",
    re.IGNORECASE,
)


def user_signals_conversation_done(latest_user_text: str) -> bool:
    t = latest_user_text.strip()
    return bool(t and _CLOSURE_RE.search(t))


def prior_assistant_was_substantive(prior_assistant_text: str) -> bool:
    """
    True if the last assistant turn likely delivered value (recommendations, comparison, etc.).
    Client history often stores only `reply` text, not structured URLs — match our phrasing too.
    """
    p = prior_assistant_text.strip().lower()
    if not p:
        return False
    if "shl.com" in p:
        return True
    if any(
        k in p
        for k in (
            "shortlist",
            "here are",
            "recommendation",
            "assessments from the catalog",
            "catalog-based comparison",
            "catalog match",
        )
    ):
        return True
    return False


def _last_user(messages: list[ChatMessage]) -> str:
    for m in reversed(messages):
        if m.role.value == "user":
            return m.content
    return messages[-1].content


def _combine(messages: Iterable[ChatMessage], role: str) -> str:
    parts = [m.content for m in messages if m.role.value == role]
    return normalize_space("\n".join(parts))


def detect_comparison_targets(latest_user: str) -> list[str]:
    if not _COMPARE_RE.search(latest_user):
        return []

    # Very lightweight heuristic: capture quoted names or TitleCase-ish spans around "vs".
    t = latest_user.strip()
    quoted = re.findall(r"\"([^\"]{2,200})\"", t)
    if quoted:
        return [normalize_space(x) for x in quoted][:4]

    # Split on vs/versus
    parts = re.split(r"\bvs\.?\b|\bversus\b", t, flags=re.IGNORECASE)
    parts = [normalize_space(p) for p in parts if len(normalize_space(p)) >= 2]
    if len(parts) >= 2:
        # take the last chunk of each side to avoid leading 'compare'
        left = re.sub(r"(?i)\b(compare|difference between)\b", "", parts[0]).strip()
        right = parts[1].strip()
        left = normalize_space(left)
        right = normalize_space(right)
        if left and right:
            return [left[:200], right[:200]]

    return []


def extract_need(full_user_text: str) -> NeedState:
    t = normalize_space(full_user_text)
    lower = t.lower()

    max_mins = extract_int_minutes(lower)

    remote_required = None
    if re.search(r"\bremote\b|\bonline\b|\bunsupervised\b", lower):
        remote_required = True
    if re.search(r"\bon[- ]?site\b|\bin[- ]person\b", lower):
        remote_required = False

    # crude seniority capture (prefer higher-signal exec/director cues over generic "senior")
    seniority = None
    if re.search(r"\bcxo(s)?\b|\bexecutive\b", lower):
        seniority = "executive"
    elif re.search(r"\bdirector\b", lower):
        seniority = "director"
    else:
        for s in ["intern", "junior", "entry", "graduate", "mid", "mid-level", "senior", "lead", "manager"]:
            if re.search(rf"\b{s}\b", lower):
                seniority = s
                break

    # desired test type hints
    desired_test_types: list[str] = []
    if re.search(r"\bpersonality\b|\bbehavior(al)?\b|\bopq\b", lower):
        desired_test_types.append("P")
    if re.search(r"\bcognitive\b|\bability\b|\bgca\b|\bverify\b", lower):
        desired_test_types.append("A")
    if re.search(r"\bskills?\b|\bcoding\b|\bjava\b|\bpython\b|\bexcel\b|\btyping\b|\bknowledge\b", lower):
        desired_test_types.append("K")
    if re.search(r"\bsimulation\b|\bin[- ]?basket\b|\bcase\b|\bscenario\b", lower):
        desired_test_types.append("S")

    # languages
    languages: list[str] = []
    for lang in ["english", "spanish", "french", "german", "italian", "portuguese", "arabic", "hindi", "japanese", "korean", "chinese"]:
        if re.search(rf"\b{lang}\b", lower):
            languages.append(lang.title())

    # role title heuristic: look for "hiring a/an X" or "for a X"
    role_title = None
    m = re.search(r"\bhiring (an?|for)\s+([a-z0-9 \-\/]{2,60})", lower)
    if m:
        role_title = normalize_space(m.group(2)).title()
    else:
        m = re.search(r"\bfor (an?|a)\s+([a-z0-9 \-\/]{2,60})", lower)
        if m:
            role_title = normalize_space(m.group(2)).title()

    # skills: extract a small set of salient tokens (non-stopword-ish)
    raw_skills: list[str] = []
    for kw in [
        "java",
        "python",
        "javascript",
        "react",
        "node",
        "sql",
        "excel",
        "sales",
        "customer service",
        "leadership",
        "stakeholder",
        "communication",
        "analysis",
        "problem solving",
        "coding",
        "engineering",
        "developer",
        "manager",
    ]:
        if kw in lower:
            raw_skills.append(kw)

    skills = sorted(set([s.title() if len(s) > 3 else s.upper() for s in raw_skills]))[:12]

    target_job_levels: list[str] = []
    if seniority in {"executive", "director"}:
        target_job_levels = ["Executive", "Director"]
    elif seniority in {"manager", "lead"}:
        target_job_levels = ["Manager", "Front Line Manager", "Supervisor"]
    elif seniority in {"mid", "mid-level"}:
        target_job_levels = ["Mid-Professional", "Professional Individual Contributor"]
    elif seniority in {"entry", "junior", "graduate", "intern"}:
        target_job_levels = ["Entry-Level", "Graduate"]

    return NeedState(
        intent=Intent.clarify,  # decided later
        raw_text=t,
        role_title=role_title,
        seniority=seniority,
        skills=skills,
        desired_test_types=sorted(set(desired_test_types)),
        target_job_levels=target_job_levels,
        max_duration_minutes=max_mins,
        languages=languages,
        remote_required=remote_required,
    )


def enough_context(need: NeedState) -> bool:
    # Intentional: keep threshold low to avoid over-clarifying under 8-turn cap.
    if need.role_title:
        return True
    if need.seniority in {"director", "executive"} and any(s.lower() in {"leadership", "stakeholder", "communication"} for s in need.skills):
        return True
    if len(need.skills) >= 2:
        return True
    return False


def apply_evaluator_turn_budget(messages: list[ChatMessage], extracted: NeedState) -> None:
    """Mutate intent when we are one message away from the 8-message cap."""
    n = len(messages)
    extracted.debug["message_count"] = n
    if n >= TURN_BUDGET_FORCE_RECOMMEND_AT_LEN and extracted.intent == Intent.clarify:
        extracted.intent = Intent.recommend
        extracted.debug["turn_budget_forced_recommend"] = True


def is_refinement(latest_user: str, prior_assistant_text: str) -> bool:
    t = latest_user.lower()
    if re.search(r"\bactually\b|\binstead\b|\bchange\b|\badd\b|\bremove\b|\bonly\b|\bexclude\b", t):
        return True
    if prior_assistant_text and re.search(r"\brecommendations?\b|\bshortlist\b", prior_assistant_text.lower()):
        # If agent already recommended earlier, many follow-ups are refinements.
        return True
    return False


def build_state(messages: list[ChatMessage]) -> NeedState:
    latest_user = _last_user(messages)
    full_user = _combine(messages, "user")
    prior_assistant = _combine(messages, "assistant")
    done_signal = user_signals_conversation_done(latest_user)
    prior_ok = prior_assistant_was_substantive(prior_assistant)

    safety = classify_safety(latest_user)
    if safety.refuse:
        st = NeedState(
            intent=Intent.refuse,
            raw_text=latest_user,
            user_signaled_done=done_signal,
            prior_assistant_substantive=prior_ok,
        )
        st.debug["safety"] = safety.model_dump()
        return st

    comparison_targets = detect_comparison_targets(latest_user)
    if comparison_targets:
        st = NeedState(
            intent=Intent.compare,
            raw_text=full_user,
            comparison_targets=comparison_targets,
            user_signaled_done=done_signal,
            prior_assistant_substantive=prior_ok,
        )
        st.debug["comparison_targets"] = comparison_targets
        return st

    extracted = extract_need(full_user)
    if is_refinement(latest_user, prior_assistant) and enough_context(extracted):
        extracted.intent = Intent.refine
    elif enough_context(extracted):
        extracted.intent = Intent.recommend
    else:
        extracted.intent = Intent.clarify

    apply_evaluator_turn_budget(messages, extracted)

    extracted.user_signaled_done = done_signal
    extracted.prior_assistant_substantive = prior_ok
    extracted.debug["latest_user"] = latest_user
    return extracted

