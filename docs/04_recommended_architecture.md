# 04 - Recommended Architecture

## Design principle

Use LLMs for language understanding and response phrasing, but keep eligibility, retrieval, ranking, schema, and catalog validation deterministic.

This assignment rewards reliability more than cleverness.

## High-level flow

```text
POST /chat
  -> validate request schema
  -> normalize full message history
  -> classify intent/safety
  -> extract NeedState from history
  -> route:
       vague -> clarify
       off-topic/injection -> refuse
       compare -> catalog lookup + compare
       recommend/refine -> retrieve + rank + validate + answer
  -> validate response schema
  -> return JSON
```

## Suggested tech stack

### Backend

- FastAPI
- Pydantic
- Uvicorn/Gunicorn

### Data

- catalog JSON checked into repo
- optional SQLite for simple local lookup
- optional FAISS/Chroma/Qdrant for vectors, but not required if dataset is small enough

### Retrieval

Recommended low-risk setup:

- `sentence-transformers` embeddings with a small model such as `all-MiniLM-L6-v2`;
- precomputed embeddings saved to disk;
- scikit-learn cosine similarity or FAISS;
- BM25 or token overlap score for exact skill matching;
- metadata reranking.

If deployment size is tight, use TF-IDF/BM25 plus metadata rules first, then add embeddings only if needed.

### LLM

Use an LLM only if available through a stable API key:

- structured extraction of conversation state;
- natural-language reply generation from retrieved evidence.

Always have deterministic fallback. The deployed API should not fail if the LLM rate-limits.

## Data model

### Catalog item

```python
class CatalogItem(BaseModel):
    id: str
    name: str
    url: str
    description: str | None = None
    job_levels: list[str] = []
    languages: list[str] = []
    assessment_length_minutes: int | None = None
    assessment_length_text: str | None = None
    test_type: str
    remote_testing: bool | None = None
    adaptive_irt: bool | None = None
    source_section: Literal["Individual Test Solutions"]
    search_text: str
```

### Conversation state

```python
class NeedState(BaseModel):
    role: str | None = None
    seniority: str | None = None
    skills: list[str] = []
    competencies: list[str] = []
    include_test_types: list[str] = []
    exclude_test_types: list[str] = []
    max_duration_minutes: int | None = None
    language: str | None = None
    remote_required: bool | None = None
    comparison_targets: list[str] = []
    intent: Literal["clarify", "recommend", "refine", "compare", "refuse"]
    confidence: float = 0.0
```

## Intent routing

### Refuse first

Before retrieval, detect:

- prompt injection;
- legal advice;
- general hiring process advice;
- non-SHL product recommendations;
- requests for private info or cheating on assessments.

### Compare second

If comparison targets are present, lookup products by:

- exact lowercase match;
- normalized match without punctuation;
- alias match, for example `OPQ` -> `Occupational Personality Questionnaire OPQ32r`;
- fuzzy match if high confidence.

### Clarify third

Clarify only when the user goal is too vague. Ask one question, not a questionnaire.

Good clarification order:

1. Role/function if absent.
2. Core skills or responsibilities if role is generic.
3. Seniority/job level if role is known.
4. Assessment type preference only if user implies it.

### Recommend/refine

When there is enough context:

- retrieve top 30 candidates;
- rerank with metadata;
- filter to catalog-only rows;
- return top 5 to 10 depending on confidence and breadth.

## Ranking formula

Example:

```text
score =
  0.45 * semantic_similarity
+ 0.25 * lexical_skill_overlap
+ 0.12 * job_level_match
+ 0.10 * requested_test_type_match
+ 0.05 * language_match
+ 0.03 * duration_fit
- penalties
```

Penalties:

- product is a report when the user needs an assessment;
- duration exceeds requested max;
- test type explicitly excluded;
- weak role relevance;
- duplicate/near-duplicate of already selected product.

## Recommendation diversity

For a software engineer role, a strong shortlist may include:

- language/framework skill test (`K`);
- broader programming or software engineering skill test (`K`);
- cognitive ability (`A`) if requested or implied by problem-solving potential;
- personality/behavior (`P`) if stakeholder/team fit is requested;
- simulation (`S`) if practical task performance is requested.

Do not force diversity if the user asks only for one assessment type.

## Deployment notes

Free-tier deployment risks:

- cold start;
- dependency size;
- model download at startup;
- external LLM latency;
- blocked scraping at runtime.

Mitigation:

- scrape offline and commit generated catalog files;
- precompute embeddings;
- load model/index at startup;
- keep `/health` simple;
- cache no conversation state, only global immutable catalog/index.

