# SHL Conversational Assessment Recommender

Implements the take-home assignment described in `docs/`.

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

Then restart the server.
