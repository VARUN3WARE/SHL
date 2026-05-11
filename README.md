# SHL Conversational Assessment Recommender

FastAPI service: **`GET /health`**, **`POST /chat`**. Stateless JSON in/out; loads a **local SHL catalog** (no live scraping on requests).

**Deployed API (Render):** [https://shl-dj0s.onrender.com](https://shl-dj0s.onrender.com)

| | URL |
|---|-----|
| Health | [https://shl-dj0s.onrender.com/health](https://shl-dj0s.onrender.com/health) |
| Chat | `POST` [https://shl-dj0s.onrender.com/chat](https://shl-dj0s.onrender.com/chat) |

Use `export BASE=https://shl-dj0s.onrender.com` in the **Verify with `curl`** section below. If your Render service name or domain changes, update this README.

**Requirements:** Python **3.12** (matches the Docker image). `git` and `curl` for the steps below.

---

## 1. Repository root and virtual environment

From the project root (`SHL/`):

```bash
python -m venv .venv
```

Activate the venv:

- **Linux / macOS:** `source .venv/bin/activate`
- **Windows (PowerShell):** `.\.venv\Scripts\Activate.ps1`
- **Windows (cmd):** `.\.venv\Scripts\activate.bat`

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 2. Catalog JSON (required for real recommendations)

The API **never** scrapes SHL at request time. It reads one local JSON file:

| Priority | How |
|----------|-----|
| 1 | If **`SHL_CATALOG_PATH`** is set, that file is used. |
| 2 | Else **`data/shl_product_catalog.json`**, then **`data/catalog.json`**. |

**Generate / refresh the catalog** — the scraper writes **`data/catalog.json`**:

```bash
python scripts/scrape_shl_catalog.py
```

If you instead maintain **`data/shl_product_catalog.json`** (or any copy) and it contains invalid JSON control characters, normalize offline (same repair logic as runtime):

```bash
python scripts/normalize_catalog.py --in data/shl_product_catalog.json --out data/shl_product_catalog.normalized.json
export SHL_CATALOG_PATH="$PWD/data/shl_product_catalog.normalized.json"   # Linux / macOS
# PowerShell: $env:SHL_CATALOG_PATH = "$PWD\data\shl_product_catalog.normalized.json"
```

Restart the server after changing `SHL_CATALOG_PATH`.

---

## 3. Run the API locally

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

For a LAN or container-friendly bind:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 4. Verify with `curl`

Point **`BASE`** at your server (local or deployed):

```bash
export BASE=http://127.0.0.1:8000    # Linux / macOS
# PowerShell: $env:BASE = "http://127.0.0.1:8000"
```

**Health** — expect `{"status":"ok"}`:

```bash
curl -sS "$BASE/health"
```

**Chat** — JSON body must include a non-empty `messages` array of `{ "role": "user"|"assistant", "content": "..." }`:

```bash
curl -sS "$BASE/chat" -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Personality assessment for executive leadership team, stakeholder communication, remote ok."}]}'
```

Successful responses match **`ChatResponse`**: `reply` (string), `recommendations` (array of `name`, `url`, `test_type`), `end_of_conversation` (boolean). To pretty-print if you have [jq](https://jqlang.org/) installed:

```bash
curl -sS "$BASE/chat" -H 'content-type: application/json' \
  -d '{"messages":[{"role":"user","content":"Personality assessment for executive leadership team, stakeholder communication, remote ok."}]}' \
  | jq .
```

**Note:** Invalid `/chat` bodies still return **HTTP 200** with the same JSON shape (empty `recommendations` and an explanatory `reply`) so automated evaluators always get a stable schema. See [`app/main.py`](app/main.py).

---

## 5. Semantic retrieval (optional, local embeddings)

Hybrid ranking uses a precomputed embedding index aligned with `load_catalog()` (same row order and filters):

```bash
python scripts/build_embedding_index.py
# Optional custom output:
# EMBEDDING_INDEX_PATH=/path/custom.npz python scripts/build_embedding_index.py --out /path/custom.npz
```

Tuning: **`HYBRID_W_SEM`**, **`HYBRID_W_LEX`**, and embedding paths in [`app/config.py`](app/config.py).

---

## 6. LLM hints (optional): Groq or Gemini

Structured **JSON-only** hints (skills, retrieval phrasing, test types) — **never** catalog URLs. On failure or when disabled, the service uses rule-based `NeedState` only.

- **Groq:** set **`GROQ_API_KEY`** (e.g. in `.env`). Uses OpenAI-compatible Chat Completions (`GROQ_MODEL`, default `llama-3.3-70b-versatile`). If Groq is configured, it is **tried first**; Gemini may still run if hints are missing and Gemini is enabled.
- **Gemini:** set **`GEMINI_API_KEY`**; disable with **`USE_GEMINI=false`**.

Do not commit real API keys.

---

## 7. Docker

The image installs **`requirements-prod.txt`** (no pytest). For development and CI, use **`requirements.txt`**.

Build and run (catalog must exist in the image or be mounted; set **`SHL_CATALOG_PATH`** when mounting a host file):

```bash
docker build -t shl-recommender .
docker run --rm -p 8000:8000 \
  -e SHL_CATALOG_PATH=/app/data/shl_product_catalog.json \
  -v "$PWD/data/shl_product_catalog.json:/app/data/shl_product_catalog.json:ro" \
  shl-recommender
```

On **Render / Fly.io / Railway**, the container listens on **`${PORT:-8000}`**. Set **`SHL_CATALOG_PATH`** in the dashboard if the catalog is not baked into the image.

This repo includes **`render.yaml`** as a starting point for [Render Blueprints](https://render.com/docs/blueprint-spec).

**Slow `/chat` on small instances:** The first load of **sentence-transformers** and the `.npz` index can take a long time on low RAM. The app **warms up embeddings at startup**. If you still hit timeouts, raise **`CHAT_PROCESSING_TIMEOUT_S`** (e.g. `55` in `render.yaml`) and/or increase instance memory. Local strict evaluators may keep **`29`** seconds—see [`app/config.py`](app/config.py).

---

## 8. Tests

```bash
pip install -r requirements.txt
python -m pytest tests/ -q
```
