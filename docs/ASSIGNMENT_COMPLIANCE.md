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
| **30s** / call budget | Met | Middleware `wait_for` ~29s; still returns valid schema on timeout |
| Individual Test Solutions only (not Pre-packaged Job Solutions) | Partial | Heuristic: drop multi-`keys` rows; drop **Precise Fit … Solution**-style bundles and **pre-packaged** wording in text/name. Without an explicit `solution_type` in the scrape, this cannot be perfect. |
| Recall@10 / LLM-grounded extraction | Partial | Deterministic BM25-like overlap + boosts; **no hosted LLM** in this repo (add API key + extractor if you want max recall). |
| 10 public traces + holdout | Partial | Use `data/sample_conversations` + zip when you have it; add golden tests per trace when labels are available. |
| Deployed URL + 2-page approach | Your side | `Dockerfile`, `render.yaml`; extend `docs/09_two_page_approach_draft.md` for submission. |

## Gaps to close for a “max score” attempt

1. Add a **bounded LLM** only for need extraction / query rewrite; keep **recommendation IDs deterministic** from catalog.
2. Add **embeddings + FAISS** (or similar) on catalog text for Recall@10.
3. **Tune** against the **10 labeled traces** (expected shortlists) once you have the zip.
4. **Verify** catalog filter against SHL’s official **Individual Test Solutions** facet if the API exposes a stable field.
