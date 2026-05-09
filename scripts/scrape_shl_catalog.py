from __future__ import annotations

"""
Offline scraper to build `data/catalog.json`.

This script is intentionally conservative:
- it is meant to run manually, not at API runtime
- it only writes normalized fields and never invents missing data

Because SHL's site structure can change, this is best-effort and may need tweaks.
"""

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from bs4 import BeautifulSoup


OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "catalog.json"


CATALOG_URL = "https://www.shl.com/solutions/products/product-catalog/"


@dataclass
class Item:
    name: str
    url: str
    test_type: str
    description: Optional[str] = None
    job_levels: list[str] = None
    languages: list[str] = None
    duration_minutes: Optional[int] = None
    remote_testing: Optional[bool] = None
    adaptive: Optional[bool] = None
    solution_type: Optional[str] = None
    scraped_at: Optional[str] = None


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def _maybe_minutes(s: str) -> Optional[int]:
    s = s.lower()
    m = re.search(r"(\d{1,3})\s*(min|mins|minutes)\b", s)
    return int(m.group(1)) if m else None


def fetch(url: str) -> str:
    with httpx.Client(timeout=30.0, follow_redirects=True, headers={"user-agent": "shl-assignment-scraper"}) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.text


def parse_catalog_listing(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "lxml")
    links: list[tuple[str, str]] = []

    # Heuristic: product catalog cards anchor into /view/<slug>/
    for a in soup.select("a"):
        href = a.get("href") or ""
        if "/product-catalog/view/" in href:
            name = _text(a)
            if not name:
                continue
            if href.startswith("/"):
                href = "https://www.shl.com" + href
            links.append((name, href))

    # De-dup by URL
    seen = set()
    out: list[tuple[str, str]] = []
    for n, u in links:
        if u in seen:
            continue
        seen.add(u)
        out.append((n, u))
    return out


def parse_product_page(name_hint: str, url: str, html: str) -> Item:
    soup = BeautifulSoup(html, "lxml")

    # Name
    h1 = soup.find(["h1", "h2"])
    name = _text(h1) or name_hint

    # Attempt to read structured fields if present
    page_text = _text(soup)

    # Test type: best-effort extraction; may need adjustment to SHL layout.
    test_type = "K"
    if re.search(r"\bpersonality\b|\bopq\b", page_text, re.IGNORECASE):
        test_type = "P"
    elif re.search(r"\bcognitive\b|\bability\b|\bgca\b", page_text, re.IGNORECASE):
        test_type = "A"
    elif re.search(r"\bsimulation\b|\bin[- ]?basket\b|\bcase\b", page_text, re.IGNORECASE):
        test_type = "S"

    # Description
    desc = ""
    for sel in ["div.product-catalog__description", "div.product-description", "article"]:
        el = soup.select_one(sel)
        if el:
            desc = _text(el)
            break
    desc = desc[:2000] if desc else None

    duration_minutes = _maybe_minutes(page_text)

    # Languages/job levels: best-effort; may be absent.
    languages: list[str] = []
    job_levels: list[str] = []
    for label, acc in [
        ("languages", languages),
        ("job levels", job_levels),
    ]:
        m = re.search(rf"{label}\s*:\s*([^\n]+)", page_text, re.IGNORECASE)
        if m:
            vals = [v.strip() for v in re.split(r",|;", m.group(1)) if v.strip()]
            acc.extend(vals[:20])

    remote_testing = None
    if re.search(r"\bremote\b|\bonline\b|\bunsupervised\b", page_text, re.IGNORECASE):
        remote_testing = True

    adaptive = None
    if re.search(r"\badaptive\b", page_text, re.IGNORECASE):
        adaptive = True

    return Item(
        name=name,
        url=url,
        test_type=test_type,
        description=desc,
        job_levels=job_levels,
        languages=languages,
        duration_minutes=duration_minutes,
        remote_testing=remote_testing,
        adaptive=adaptive,
        solution_type=None,
        scraped_at=datetime.now(timezone.utc).isoformat(),
    )


def main() -> None:
    listing_html = fetch(CATALOG_URL)
    products = parse_catalog_listing(listing_html)

    items: list[Item] = []
    for name, url in products:
        try:
            html = fetch(url)
            items.append(parse_product_page(name, url, html))
        except Exception:
            continue

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps([asdict(i) for i in items], indent=2), encoding="utf-8")
    print(f"Wrote {len(items)} items to {OUT_PATH}")


if __name__ == "__main__":
    main()

