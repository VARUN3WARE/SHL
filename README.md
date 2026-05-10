# SHL Conversational Assessment Recommender

Implements the take-home assignment described in `docs/`. See **`docs/ASSIGNMENT_COMPLIANCE.md`** for a requirement-by-requirement checklist and known gaps.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl -s localhost:8000/health
```

Chat:

```bash
curl -s localhost:8000/chat \
  -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Hiring a Java developer, mid-level, needs stakeholder communication. Prefer <=30 minutes."}]}'
```

## Catalog data

This service **never scrapes at runtime**. It loads a local catalog JSON file:

- optional override: set **`SHL_CATALOG_PATH`** to an absolute path to one JSON file (used exclusively when set)
- otherwise: `data/shl_product_catalog.json`, then `data/catalog.json`

Example:

```bash
export SHL_CATALOG_PATH=/path/to/shl_product_catalog.json
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

To generate it, run:

```bash
python scripts/scrape_shl_catalog.py
```

If the scrape contains invalid JSON control characters, normalize offline (same repair as runtime):

```bash
python scripts/normalize_catalog.py --in data/shl_product_catalog.json --out data/shl_product_catalog.normalized.json
export SHL_CATALOG_PATH="$PWD/data/shl_product_catalog.normalized.json"
```

Then restart the server.

## Docker

The image installs **`requirements-prod.txt`** (no pytest). For local development and CI, use **`requirements.txt`**.

Build and run locally (catalog must exist under `data/` at build time, or mount a file and set `SHL_CATALOG_PATH`):

```bash
docker build -t shl-recommender .
docker run --rm -p 8000:8000 \
  -e SHL_CATALOG_PATH=/app/data/shl_product_catalog.json \
  -v "$PWD/data/shl_product_catalog.json:/app/data/shl_product_catalog.json:ro" \
  shl-recommender
```

Platforms like **Render / Fly.io / Railway** inject **`PORT`**; the image listens on **`${PORT:-8000}`**. Set **`SHL_CATALOG_PATH`** in the dashboard if the catalog is not baked into the image.

This repo includes **`render.yaml`** as a starting point for [Render Blueprints](https://render.com/docs/blueprint-spec).

## Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
```
