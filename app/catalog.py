from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from app.models import CatalogItem


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEFAULT_CATALOG_PATHS = [
    DATA_DIR / "shl_product_catalog.json",
    DATA_DIR / "catalog.json",
]


def catalog_path_candidates() -> list[Path]:
    """
    If SHL_CATALOG_PATH is set, use only that file (single source of truth for deploys).
    Otherwise try default locations under data/.
    """
    override = os.environ.get("SHL_CATALOG_PATH", "").strip()
    if override:
        return [Path(override).expanduser().resolve()]
    return list(DEFAULT_CATALOG_PATHS)


class Catalog:
    def __init__(self, items: list[CatalogItem]):
        self.items = items
        self.by_url = {str(i.url): i for i in items}
        self.by_name_lower = {i.name.lower(): i for i in items}

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0


_MIN_RE = re.compile(r"(\d{1,3})\s*(?:min|mins|minutes)\b", re.IGNORECASE)


def _parse_minutes(duration: str) -> int | None:
    if not duration:
        return None
    m = _MIN_RE.search(duration)
    return int(m.group(1)) if m else None


def _yn_to_bool(v: Any) -> bool | None:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in {"yes", "y", "true", "1"}:
        return True
    if s in {"no", "n", "false", "0"}:
        return False
    return None


def _infer_test_type(keys: list[str]) -> str:
    """
    Map SHL 'keys' category to a compact test_type string.
    The API only requires a short string; we keep it stable/deterministic.
    """
    kset = {k.strip().lower() for k in (keys or []) if k}
    if "knowledge & skills".lower() in kset:
        return "K"
    if "personality & behavior".lower() in kset:
        return "P"
    if "ability & aptitude".lower() in kset:
        return "A"
    if "simulations".lower() in kset or "assessment exercises".lower() in kset:
        return "S"
    if "biodata & situational judgment".lower() in kset:
        return "SJ"
    if "competencies".lower() in kset:
        return "C"
    if "development & 360".lower() in kset:
        return "D"
    return "U"  # unknown/other


def _is_individual_test_solution(name: str, keys: list[str]) -> bool:
    """
    Practical filter to exclude pre-packaged job solutions.
    In the scraped catalog, those typically appear as *Solution* items with multiple 'keys'.
    """
    if not keys:
        return True
    if len(keys) > 1:
        return False
    # If it's explicitly a 'Solution' with a single key, keep it; some catalogs contain
    # single-key solutions that are still individual instruments/reports.
    return True


def _load_first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def load_catalog(path: Path | None = None) -> Catalog:
    path = path or _load_first_existing(catalog_path_candidates())
    if path is None or not path.exists():
        return Catalog([])

    text = path.read_text(encoding="utf-8", errors="replace")

    # Some scraped exports contain invalid JSON due to raw newlines/control characters inside strings.
    # We sanitize by:
    # - removing non-whitespace control chars outside of strings
    # - converting control chars *inside* strings into escaped sequences
    def _sanitize_json(s: str) -> str:
        out: list[str] = []
        in_str = False
        escape = False
        for ch in s:
            if in_str:
                if escape:
                    out.append(ch)
                    escape = False
                    continue
                if ch == "\\":
                    out.append(ch)
                    escape = True
                    continue
                if ch == '"':
                    out.append(ch)
                    in_str = False
                    continue
                # Any control char inside a JSON string is invalid unless escaped.
                if unicodedata.category(ch) == "Cc":
                    if ch == "\n":
                        out.append("\\n")
                    elif ch == "\r":
                        out.append("\\r")
                    elif ch == "\t":
                        out.append("\\t")
                    else:
                        # drop other controls rather than failing
                        continue
                else:
                    out.append(ch)
            else:
                if ch == '"':
                    out.append(ch)
                    in_str = True
                    continue
                # Outside strings: allow standard whitespace; drop other control chars.
                if unicodedata.category(ch) == "Cc" and ch not in "\n\r\t":
                    continue
                out.append(ch)
        return "".join(out)

    raw = json.loads(_sanitize_json(text))
    if not isinstance(raw, list):
        raise ValueError(f"{path.name} must be a JSON array")

    items: list[CatalogItem] = []
    seen_urls: set[str] = set()
    for obj in raw:
        if not isinstance(obj, dict):
            continue

        # Supports both normalized catalog.json and scraped shl_product_catalog.json
        name = (obj.get("name") or "").strip()
        url = (obj.get("url") or obj.get("link") or "").strip()
        keys = obj.get("keys") or []
        if not isinstance(keys, list):
            keys = []

        if not name or not url:
            continue
        if not _is_individual_test_solution(name, keys):
            continue

        test_type = (obj.get("test_type") or "").strip() or _infer_test_type(keys)
        duration_minutes = obj.get("duration_minutes")
        if duration_minutes is None:
            duration_minutes = _parse_minutes(str(obj.get("duration") or obj.get("duration_raw") or ""))

        item = CatalogItem(
            name=name,
            url=url,
            test_type=test_type,
            description=(obj.get("description") or None),
            job_levels=list(obj.get("job_levels") or []),
            languages=list(obj.get("languages") or []),
            duration_minutes=duration_minutes,
            remote_testing=_yn_to_bool(obj.get("remote") if "remote" in obj else obj.get("remote_testing")),
            adaptive=_yn_to_bool(obj.get("adaptive")),
            solution_type=("individual_test_solution"),
            scraped_at=(obj.get("scraped_at") or None),
        )

        u = str(item.url)
        if u in seen_urls:
            continue
        seen_urls.add(u)
        items.append(item)

    return Catalog(items)

