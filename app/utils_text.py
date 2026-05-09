from __future__ import annotations

import re
from collections import Counter


_WORD_RE = re.compile(r"[a-z0-9][a-z0-9\-\+\.]{1,}", re.IGNORECASE)


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def tokenize(s: str) -> list[str]:
    s = s.lower()
    return _WORD_RE.findall(s)


def bag_of_words(s: str) -> Counter[str]:
    return Counter(tokenize(s))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def extract_int_minutes(text: str) -> int | None:
    """
    Extract a max duration constraint like '30 minutes', '<= 45 min', 'under 1 hour'.
    Returns minutes if found, else None.
    """
    t = text.lower()
    m = re.search(r"(<=|under|less than|within|max)\s*(\d{1,3})\s*(min|mins|minutes)\b", t)
    if m:
        return int(m.group(2))
    m = re.search(r"(\d{1,3})\s*(min|mins|minutes)\b", t)
    if m:
        return int(m.group(1))
    m = re.search(r"(<=|under|less than|within|max)\s*(\d{1,2})\s*(hour|hours|hr|hrs)\b", t)
    if m:
        return int(m.group(2)) * 60
    m = re.search(r"(\d{1,2})\s*(hour|hours|hr|hrs)\b", t)
    if m:
        return int(m.group(1)) * 60
    return None

