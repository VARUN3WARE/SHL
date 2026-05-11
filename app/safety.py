from __future__ import annotations

import re

from app.models import SafetyDecision


_INJECTION_PATTERNS = [
    r"\bignore (all|any|previous|prior) (instructions|rules)\b",
    r"\b(system prompt|developer message|hidden prompt)\b",
    r"\breturn (a )?fake\b",
    r"\bmake up\b.*\burl\b",
    r"\bbypass\b.*\bpolicy\b",
]

_CHEATING_PATTERNS = [
    r"\bcheat\b",
    r"\banswers?\b.*\b(test|assessment)\b",
    r"\bhow to pass\b.*\b(opq|gsa|assessment|test)\b",
    r"\bgame\b.*\bassessment\b",
]

_LEGAL_PATTERNS = [
    r"\blegal advice\b",
    r"\blegally required\b",
    r"\blawyer\b",
    r"\bcompliance\b.*\bemployment\b",
    r"\bhipaa\b.*\brequired\b",
    r"\bis this legal\b",
]

_GENERAL_HIRING_ADVICE = [
    r"\bwrite (a )?job description\b",
    r"\binterview questions\b",
    r"\bsalary\b",
    r"\bcompensation\b",
    r"\btermination\b",
]


def classify_safety(text: str) -> SafetyDecision:
    t = text.lower()

    for p in _INJECTION_PATTERNS:
        if re.search(p, t):
            return SafetyDecision(refuse=True, category="prompt_injection", reason="Prompt injection attempt.")

    for p in _CHEATING_PATTERNS:
        if re.search(p, t):
            return SafetyDecision(refuse=True, category="cheating", reason="Requests to game assessments are disallowed.")

    for p in _LEGAL_PATTERNS:
        if re.search(p, t):
            return SafetyDecision(refuse=True, category="legal", reason="Legal advice is out of scope.")

    for p in _GENERAL_HIRING_ADVICE:
        if re.search(p, t):
            return SafetyDecision(refuse=True, category="general_hiring_advice", reason="General hiring advice is out of scope.")

    return SafetyDecision(refuse=False)

