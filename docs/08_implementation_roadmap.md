# 08 - Implementation Roadmap

Deadline in email: 11 May 2026, 6:00 PM.

## Phase 0 - Get missing links

Need:

- public trace zip;
- official assignment link if it contains extra requirements;
- submission form URL.

## Phase 1 - Repository setup

Suggested structure:

```text
app/
  main.py
  schemas.py
  settings.py
  catalog.py
  state.py
  safety.py
  retrieval.py
  ranker.py
  response_builder.py
scripts/
  scrape_catalog.py
  build_index.py
  evaluate_traces.py
data/
  catalog_raw.json
  catalog_clean.json
  catalog_embeddings.npy
  catalog_index_meta.json
tests/
  test_api_schema.py
  test_behavior.py
  test_catalog_validation.py
  test_retrieval_smoke.py
requirements.txt
README.md
```

## Phase 2 - Catalog scraping

Deliverables:

- scraper for Individual Test Solutions;
- clean catalog JSON;
- validation script;
- a small catalog quality report.

Important:

- scrape offline;
- do not scrape during `/chat`;
- preserve exact product names and URLs.

## Phase 3 - API skeleton

Implement:

- `GET /health`;
- `POST /chat`;
- Pydantic request/response models;
- global catalog loading at startup;
- deterministic error response with schema.

Example error-safe response:

```json
{
  "reply": "I can help with SHL assessment selection. Please share the role or skills you want to assess.",
  "recommendations": [],
  "end_of_conversation": false
}
```

## Phase 4 - State and safety

Implement:

- message validation;
- latest-user extraction;
- off-topic/prompt-injection classifier;
- need extraction rules;
- optional LLM structured extraction;
- stateless merge of full conversation.

## Phase 5 - Retrieval and ranking

Start simple:

- TF-IDF or sentence-transformers embeddings;
- top 30 retrieval;
- metadata reranker.

Then improve:

- synonyms;
- test-type boosts;
- duration/language filters;
- job-level mapping;
- diversity selection.

## Phase 6 - Behavior routes

Implement:

- clarify;
- recommend;
- refine;
- compare;
- refuse.

Keep all routes behind response schema validation.

## Phase 7 - Evaluation

Implement local probes:

- vague query;
- detailed query;
- refinement;
- comparison;
- refusal;
- catalog-only validation.

Run public traces once available.

## Phase 8 - Deployment

Good free/low-cost choices:

- Render web service;
- Railway;
- Fly.io;
- Hugging Face Space with Docker;
- Modal if familiar.

Deployment checklist:

- `PORT` env var respected;
- model/index files packaged;
- no runtime scraping;
- `/health` responds quickly;
- API URL remains public;
- logs do not expose API keys.

## Suggested timeline

### Day 1

- download traces;
- scrape catalog;
- build API skeleton;
- implement schema tests.

### Day 2

- implement state extraction, safety, retrieval, ranking;
- run behavior probes;
- tune against public traces.

### Day 3

- deploy;
- test deployed URL;
- write approach doc;
- final replay and submission.

## Fallback plan

If time runs short:

- skip frontend entirely;
- use TF-IDF/BM25 plus metadata ranking;
- avoid external LLM dependency;
- focus on schema, catalog grounding, behavior probes, and public-trace recall.

This will usually beat a fancier but unstable agent.

