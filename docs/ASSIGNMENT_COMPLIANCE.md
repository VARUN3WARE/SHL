# Assignment compliance (SHL take-home)

Cross-check against the published brief: conversational recommender, **Individual Test Solutions** only, stateless FastAPI, schema, behaviors, and evaluator limits.

| Requirement | Status | Implementation notes |
|-------------|--------|----------------------|
| `GET /health` → `{"status":"ok"}` | Met | `app/main.py` + `HealthResponse` |
| `POST /chat` stateless (full `messages` each call) | Met | No server session; `build_state(messages)` |
| Response schema always (`reply`, `recommendations`, `end_of_conversation`) | Met | Pydantic + exception handlers return `ChatResponse` shape on errors |
| `recommendations` empty when clarifying / refusing | Met | `app/responses.py` |
| `recommendations` 1–10 when committing | Met | `recommendation_guard` + rank; empty → clarify-style reply if no rows |
| URLs from scraped catalog only | Met | Rows from `load_catalog()`; bind step drops unknown URLs |
| Clarify vague queries before recommending | Met | `enough_context` / `Intent.clarify` |
| Recommend when enough context | Met | `Intent.recommend` / `refine` |
| Refine on constraint changes | Met | `is_refinement` + re-rank |
| Compare from catalog data | Met | `Intent.compare` + `find_by_name_fuzzy` + fields only |
| Refuse off-topic / legal / injection (etc.) | Met | `app/safety.py` |
| **8-turn cap** (evaluator) | Met | At **≥7 messages** in history, **clarify → recommend** (best-effort) so the last turn can still be a shortlist |
| **30s** / call budget | Met | Middleware `wait_for` uses `CHAT_PROCESSING_TIMEOUT_S` (default 29s); still returns valid schema on timeout. **Render:** set ~55s if cold CPU needs margin; startup **embedding warmup** reduces first-request latency. |
| Individual Test Solutions only (not Pre-packaged Job Solutions) | Partial | Heuristic: drop multi-`keys` rows; drop **Precise Fit … Solution**-style bundles and **pre-packaged** wording in text/name. Without an explicit `solution_type` in the scrape, this cannot be perfect. |
| Recall@10 / grounded extraction | Improved | **Local** `sentence-transformers` embeddings over catalog text + **hybrid** fusion with lexical scores ([`app/embeddings.py`](app/embeddings.py), [`app/retrieval.py`](app/retrieval.py)). Optional **Groq** or **Gemini** JSON hints ([`app/gemini_extract.py`](app/gemini_extract.py)) — Groq first when `GROQ_API_KEY` is set; no model-chosen URLs; timeouts + fallback to rules-only. |
| 10 public traces + holdout | Partial | Use `data/sample_conversations` + zip when you have it; add golden tests per trace when labels are available. |
| Deployed URL + 2-page approach | Your side | `Dockerfile`, `render.yaml`; extend `docs/09_two_page_approach_draft.md` for submission. |

## Gaps to close for a “max score” attempt

1. **Tune** hybrid weights (`HYBRID_W_SEM` / `HYBRID_W_LEX`) and embedding model against the **10 labeled traces** (expected shortlists) when you have the zip.
2. **Verify** catalog filter against SHL’s official **Individual Test Solutions** facet if the API exposes a stable field.
3. **Rotate** any exposed API keys (Gemini, **Groq**, etc.); use `.env` locally only (see [`.env.example`](../.env.example)).

## Env vars (summary)

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Optional; Groq structured JSON hints (preferred when set) |
| `USE_GROQ` | `false` to skip Groq |
| `GROQ_MODEL` / `GROQ_TIMEOUT_S` | Groq model id and HTTP timeout |
| `GEMINI_API_KEY` | Optional; Gemini hints if Groq did not run or returned nothing |
| `USE_GEMINI` | `false` to disable Gemini calls |
| `GEMINI_MODEL` / `GEMINI_TIMEOUT_S` | Model id and client timeout |
| `EMBEDDING_MODEL` / `EMBEDDING_INDEX_PATH` | Sentence-transformers model and `.npz` index path |
| `HYBRID_W_SEM` / `HYBRID_W_LEX` | Hybrid fusion weights |

Rebuild `data/catalog_embeddings.npz` after catalog changes: `python scripts/build_embedding_index.py`.
