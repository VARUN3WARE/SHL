# Approach: SHL Conversational Assessment Recommender

**Summary.** Stateless FastAPI service over a **fixed SHL catalog** (Individual Test Solutions–oriented scrape). Each `POST /chat` receives the **full** `messages` array; the server reconstructs intent and need, optionally enriches with **bounded LLM JSON hints** (Groq or Gemini), retrieves with **hybrid lexical + local embeddings**, then returns a strict **`ChatResponse`** with catalog-grounded `recommendations` (1–10 items) or an empty list when clarifying or refusing.

---

## 1. Objectives and constraints

- **Grounding:** Names and URLs always come from `load_catalog()` in [`app/catalog.py`](app/catalog.py). Nothing is invented at inference time.
- **Statelessness:** No session storage; [`build_state`](app/state.py) derives `NeedState` from the transcript every call.
- **Evaluator limits:** Eight-message turn budget (forced recommend near the cap), bounded processing time ([`CHAT_PROCESSING_TIMEOUT_S`](app/config.py), middleware in [`app/main.py`](app/main.py)), and valid JSON even on errors or timeout.
- **Safety:** [`app/safety.py`](app/safety.py) refuses off-scope, legal, cheating, injection, and similar patterns before any optional LLM call.

---

## 2. Data and offline preparation

- **Catalog JSON** under `data/` (configurable via `SHL_CATALOG_PATH`). Runtime **never** scrapes SHL; scraping is a separate offline step ([`scripts/scrape_shl_catalog.py`](scripts/scrape_shl_catalog.py) when used).
- **Filtering:** Heuristics drop non–individual-test rows (e.g. multi-key bundles, pre-packaged solution wording). See [`docs/ASSIGNMENT_COMPLIANCE.md`](docs/ASSIGNMENT_COMPLIANCE.md); the filter is best-effort without a perfect upstream `solution_type` for every row.
- **Embedding index:** [`scripts/build_embedding_index.py`](scripts/build_embedding_index.py) writes `data/catalog_embeddings.npz` in **the same row order** as `load_catalog()`. Docker runs this at **image build** so production does not pay model-download time on first user request beyond RAM load. **Startup warmup** in [`app/main.py`](app/main.py) loads the index and runs one encode so the first `/chat` stays within timeout on small hosts (e.g. Render free).

---

## 3. Request pipeline (high level)

1. **`GET /health`** — Liveness; no heavy imports.
2. **`POST /chat`** — In order:
   - Load catalog.
   - **`build_state(messages)`** — safety → compare detection → `extract_need` → intent (`clarify` / `recommend` / `refine` / `compare` / `refuse`) and turn-budget adjustment.
   - **`apply_gemini_hints`** ([`app/gemini_extract.py`](app/gemini_extract.py)) — if intent allows: **Groq** first (OpenAI-compatible chat completions + JSON schema), else **Gemini**; Pydantic validation; on failure, rules-only state. LLM outputs **hints only** (retrieval phrasing, skills, test-type hints)—never catalog URLs.
   - **`refresh_intent_after_hints`** — may upgrade `clarify` → `recommend` when merged hints yield `enough_context`.
   - **`semantic_top_urls`** ([`app/embeddings.py`](app/embeddings.py)) for `recommend` / `refine` when catalog non-empty.
   - **`respond`** ([`app/responses.py`](app/responses.py)) — `rank_hybrid` + diversification + catalog bind + templated `reply`.

Refuse and compare paths **skip** LLM hints to save latency and risk.

---

## 4. Retrieval and ranking

- **Lexical:** Token overlap and bag-of-words style signals with boosts/penalties for test type, leadership vs technical K-tests, duration, languages, job levels, remote flags ([`lexical_score_item`](app/retrieval.py)).
- **Semantic:** Precomputed L2-normalized rows; query vector from the same `SentenceTransformer` model; cosine as dot product; top-`k` URL scores.
- **Hybrid:** [`rank_hybrid`](app/retrieval.py) fuses normalized lexical score with semantic score using `HYBRID_W_SEM` / `HYBRID_W_LEX` from config. If the index is missing or encoding fails, falls back to lexical-only `rank`.
- **Post-processing:** [`diversify_ranked_items` / binding](app/recommendation_guard.py) keeps names and URLs canonical and applies diversity rules.

---

## 5. Why not a “pure LLM recommender”?

A single generative model picking the shortlist risks **hallucinated URLs** and unstable behavior under adversarial or vague prompts. This design keeps **selection and URLs deterministic** from the catalog while still using an LLM (when configured) for **structured, validated hints** merged into `NeedState`, plus semantic recall for paraphrases.

---

## 6. Deployment

- **Container:** [`Dockerfile`](Dockerfile) — Python slim, `requirements-prod.txt`, `COPY app`, `data`, `scripts`, optional index build, `uvicorn` on `$PORT`.
- **Render:** [`render.yaml`](render.yaml) blueprint with `SHL_CATALOG_PATH`, `CHAT_PROCESSING_TIMEOUT_S` headroom for weak CPUs, and optional `GROQ_MODEL`. Secrets (`GROQ_API_KEY`, `GEMINI_API_KEY`) are set in the dashboard, not in git.
- **Local:** `.env` from [`.env.example`](.env.example); see [`README.md`](README.md) for curl examples and embedding rebuild.

---

## 7. Evaluation and known gaps

- **Automated:** `pytest` covers API contract, behavior probes, hybrid fallback, Groq/Gemini invalid JSON fallbacks, and merge logic.
- **Traces:** When the official **10 public traces** zip is available, replay against the deployed URL and tune weights or `enough_context` heuristics against labeled shortlists ([`docs/ASSIGNMENT_COMPLIANCE.md`](docs/ASSIGNMENT_COMPLIANCE.md) tracks this as partial until run).
- **Catalog facet:** Perfect “Individual Test Solutions only” alignment would need a stable field from the source listing; current behavior is documented as partial in the compliance checklist.

---

## 8. One-line takeaway

**Rules and catalog ground truth decide what can be recommended; embeddings improve recall; optional Groq/Gemini JSON improves slot-filling and retrieval wording—all with timeouts, fallbacks, and schema-safe error paths.**
