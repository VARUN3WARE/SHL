#!/usr/bin/env python3
"""
Offline repair: read a scraped SHL catalog JSON file, apply the same sanitizer as the API,
and write strict UTF-8 JSON (valid for any standard parser).

Usage:
  python scripts/normalize_catalog.py
  python scripts/normalize_catalog.py --in data/shl_product_catalog.json --out data/catalog.normalized.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow `python scripts/normalize_catalog.py` from repo root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.catalog import DATA_DIR, sanitize_catalog_json_text  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Normalize SHL catalog JSON for strict parsing.")
    p.add_argument(
        "--in",
        dest="in_path",
        type=Path,
        default=DATA_DIR / "shl_product_catalog.json",
        help="Input JSON file (array of product objects)",
    )
    p.add_argument(
        "--out",
        dest="out_path",
        type=Path,
        default=DATA_DIR / "shl_product_catalog.normalized.json",
        help="Output path for repaired JSON",
    )
    args = p.parse_args()

    src = args.in_path.expanduser().resolve()
    if not src.is_file():
        print(f"Input not found: {src}", file=sys.stderr)
        sys.exit(1)

    text = src.read_text(encoding="utf-8", errors="replace")
    data = json.loads(sanitize_catalog_json_text(text))
    if not isinstance(data, list):
        print("Expected top-level JSON array", file=sys.stderr)
        sys.exit(2)

    out = args.out_path.expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(data)} records to {out}")


if __name__ == "__main__":
    main()
