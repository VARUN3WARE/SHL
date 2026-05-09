# 03 - Existing Solution Landscape

## What already exists publicly

There are many public SHL assessment recommender projects from previous assignment cycles or similar tasks. Common patterns:

- scrape the SHL product catalog;
- build a CSV/JSON with product metadata;
- embed product descriptions with Sentence-BERT, Gemini embeddings, OpenAI embeddings, or similar;
- retrieve top matches using cosine similarity, FAISS, Chroma, or Qdrant;
- use an LLM such as Gemini, Groq/Llama, Cohere, Mistral/OpenRouter, or OpenAI for reranking or explanations;
- expose a Streamlit UI and sometimes a FastAPI endpoint.

Examples found publicly:

- `khushimadan/SHL_Assessment_Recommendation_System`: Streamlit-style recommender using Sentence-BERT and Gemini for feature extraction.
- `manojkp08/shl-assessment-recommendor`: FastAPI plus ChromaDB, sentence-transformers, Cohere, and Streamlit.
- public LinkedIn/GitHub/Hugging Face posts describing FastAPI + Streamlit + embeddings + LLM reranking solutions.

Sources:

- https://github.com/khushimadan/SHL_Assessment_Recommendation_System
- https://github.com/manojkp08/shl-assessment-recommendor
- https://github.com/Sanjay123sam456/shl-assessment-recommender
- https://awesome.ecosyste.ms/projects/github.com%2Faakashsharma7%2Fshl-assessment-recommendation-system

## Why those solutions may not score well on this assignment

This assignment is explicitly conversational and stateless. Many public projects solve a simpler problem:

- one-shot `/recommend` endpoint, not `/chat`;
- no strict schema matching the new assignment;
- no refusal behavior;
- no clarify-before-recommend behavior;
- no comparison behavior;
- no history-based refinement;
- weak guarantees that URLs come only from catalog;
- no local replay harness for multi-turn traces;
- over-reliance on LLM-generated explanations or metadata.

The differentiator is agent design, not only vector search.

## Baseline solution

A defensible baseline:

- scrape Individual Test Solutions into JSON/CSV;
- embed a combined text field;
- for detailed user input, return top 5 to 10 by hybrid score;
- for vague input, ask one clarification question;
- for comparison, lookup exact/near product names and compare fields;
- for refusal, deterministic classifier/rules plus LLM fallback.

This likely passes basic hard evals if schema and catalog validation are solid.

## Better-than-baseline solution

Add the following:

- conversation-state extractor that summarizes the full message history into a structured `NeedState`;
- constraint-aware retrieval and reranking;
- exact catalog membership validation before response;
- query expansion for role synonyms and technologies;
- special handling of "add personality", "add cognitive", "shorter than X minutes", "remote", "senior", "graduate", etc.;
- comparison lookup using product name aliases and fuzzy matching;
- behavior test suite with mocked public traces.

## Appreciable but realistic stretch features

These are hard enough to impress but still feasible:

### 1. Hybrid ranker with transparent scoring

Combine:

- semantic similarity;
- lexical/BM25 match on role and skill tokens;
- metadata boosts for requested test types;
- job-level match;
- duration/language/remote filters;
- diversity rules so the shortlist covers skills, cognitive, personality, and simulation when requested.

### 2. Deterministic state extraction schema

Use an LLM or rule parser to produce:

```json
{
  "role": "Java developer",
  "seniority": "Mid-Professional",
  "skills": ["Java", "stakeholder communication"],
  "include_test_types": ["K", "P"],
  "exclude_test_types": [],
  "max_duration_minutes": null,
  "language": "English (USA)",
  "needs_recommendation": true,
  "needs_comparison": false,
  "off_topic": false
}
```

Validate it with Pydantic. If the LLM output is bad, fall back to rules.

### 3. Golden trace replay harness

Implement a local evaluator that replays the public traces and behavior probes:

- schema validation every turn;
- no recommendations on vague query;
- final Recall@10 where labels are available;
- catalog URL validation;
- latency measurement;
- comparison hallucination checks.

### 4. Catalog quality report

Generate a small report after scraping:

- total Individual Test Solutions count;
- duplicate names;
- missing descriptions;
- missing duration;
- missing job levels;
- test-type distribution;
- broken URLs.

This demonstrates engineering rigor and helps prevent evaluator failures.

## What not to do

- Do not clone a public project blindly. The interview will likely probe your understanding.
- Do not make the LLM invent final recommendation rows.
- Do not depend on a slow cold-start model for every request if hosted on a free tier.
- Do not recommend Pre-packaged Job Solutions.
- Do not build a polished frontend at the expense of the API. The API is what gets evaluated.
- Do not include unsupported claims in comparison responses.

