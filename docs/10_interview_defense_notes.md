# 10 - Interview Defense Notes

## One-minute project explanation

I built a stateless FastAPI conversational recommender for SHL Individual Test Solutions. The main design choice was to separate language understanding from catalog selection: the agent extracts the user's need from conversation history, but final recommendations are selected deterministically from a validated scraped catalog. This lets the system clarify vague requests, refine constraints, compare products, and refuse out-of-scope prompts without hallucinating SHL products or URLs.

## Why not a pure LLM chatbot?

Because the hardest failure mode is hallucination. The evaluator explicitly checks catalog-only URLs and behavior probes. A pure LLM can sound good but invent products, URLs, durations, or unsupported comparison claims. I use the LLM only for bounded state extraction and reply wording, then validate everything.

## Why stateless design matters

The evaluator sends full conversation history on every request and expects no stored session state. Stateless design also makes deployment simpler and safer: any worker can answer any request from the provided messages.

## How clarification works

The agent asks a question only when key role/skill context is missing. It avoids long questionnaires because the evaluator has an 8-turn cap. Once it has enough context, it recommends rather than continuing to ask.

## How refinement works

The latest user turn is merged with earlier facts from the full history. If the user says "Actually add personality tests", the role and skill context are preserved, `P` is added as a desired test type, and ranking runs again.

## How comparison works

The agent first resolves product names through exact, normalized, acronym, and high-confidence fuzzy matching. It then compares only catalog fields: description, test type, duration, job levels, languages, and URLs. If a field is missing, it says the catalog does not specify it.

## How refusal works

Safety and scope run before retrieval. The agent refuses legal advice, general hiring advice, prompt injection, non-SHL products, and cheating guidance. Refusals always return empty recommendations and valid schema.

## Ranking choices to defend

Hybrid ranking is better than vector-only because:

- technical skills often need exact token matches (`Java`, `.NET`, `AWS`, `Excel`);
- user constraints like duration and personality/cognitive type are structured metadata;
- semantic search helps with vague phrasing and JD-style text;
- reranking lets the system balance role fit, test type, seniority, and constraints.

## Likely questions and answers

### Q: How do you ensure recommendations are from the catalog?

Every recommendation object is built from a catalog record loaded from `catalog_clean.json`. Before returning, response validation checks that the exact URL and name exist in the catalog and that the source section is Individual Test Solutions.

### Q: What happens if the LLM API fails?

The system falls back to rule-based state extraction and deterministic retrieval. The API still returns a schema-valid response.

### Q: How did you improve Recall@10?

I replayed public traces, inspected missed expected products, and adjusted synonyms, metadata boosts, and penalties. For example, stakeholder-heavy roles should boost behavior/personality assessments, while technical roles need exact skill matching.

### Q: How do you avoid over-asking questions?

I define "enough context" as role or job family plus at least one skill/responsibility/seniority signal. If the user provides a detailed job description, the system recommends immediately.

### Q: What are the main limitations?

Catalog pages can have sparse descriptions, so some recommendations rely heavily on names and metadata. Free-tier hosting can cold-start, so the app avoids runtime scraping and loads precomputed data. The public catalog may change, so the scraper and validation report should be rerun before final submission.

## What is hard but appreciable

- Robust stateless conversation-state reconstruction.
- Catalog-only validation on every response.
- Handling refinements without losing earlier constraints.
- Grounded comparison answers.
- Local behavior probes that match the evaluator's style.
- Trace-driven ranking improvements rather than only subjective testing.

