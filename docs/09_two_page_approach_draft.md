# 09 - Two-Page Approach Draft

## Conversational SHL Assessment Recommender - Approach

### Objective

The goal is to build a stateless FastAPI service that helps recruiters select relevant SHL Individual Test Solutions through conversation. The system accepts full conversation history on every request, decides whether to clarify, recommend, refine, compare, or refuse, and returns a strict JSON response containing a natural-language reply plus catalog-grounded recommendations when appropriate.

### Catalog and data preparation

I scrape the SHL product catalog restricted to `Individual Test Solutions`, excluding pre-packaged job solutions. For each assessment I store the exact catalog name, URL, test type, description, job levels, languages, duration, remote-testing flag, adaptive/IRT flag, and raw source text. I preserve exact names and URLs for output, while also creating normalized aliases for lookup, such as lowercase names, punctuation-free names, and common acronyms like OPQ and GSA.

The cleaned catalog is validated before deployment: every item must have a name, SHL catalog URL, allowed test-type code, and Individual Test Solutions source section. Recommendations are selected only from this validated catalog, so the API cannot return fabricated products or URLs. The catalog and retrieval index are built offline and shipped with the service to avoid runtime scraping and reduce latency.

### Retrieval and ranking

The recommendation engine uses hybrid retrieval. Each catalog item has a searchable text field combining product name, description, test type, job levels, languages, duration, and controlled synonyms. A first-stage retriever returns broad candidates using semantic similarity and/or lexical similarity. A deterministic reranker then applies metadata-aware scoring:

- role and skill overlap;
- requested assessment type, such as knowledge/skills, personality, cognitive ability, or simulation;
- job-level fit;
- duration and language constraints;
- remote/adaptive preferences where present;
- penalties for report-only products when the user asks for an assessment;
- diversity rules when the role benefits from multiple assessment dimensions.

This keeps the final shortlist explainable and stable while still handling natural-language job descriptions.

### Conversation and agent design

The API is stateless. On every `/chat` call, the system reconstructs the current user need from the full message history. The extracted state includes role, seniority, skills, competencies, desired test types, excluded test types, duration limit, language, remote preference, comparison targets, and intent.

Routing is deterministic:

1. Safety and scope checks run first.
2. Comparison requests are handled by exact/alias/fuzzy catalog lookup.
3. Vague requests trigger a single focused clarification question.
4. Detailed requests trigger retrieval and ranking.
5. Refinements merge the latest user change with previously stated requirements and rerun ranking.

The agent asks for clarification only when a recommendation would be arbitrary. If enough role or skill context exists, it recommends within the 8-turn conversation cap. When refusing off-topic, legal, or prompt-injection requests, it returns an in-scope redirect and an empty recommendations array.

### Prompting strategy

LLMs, if used, are limited to bounded tasks: structured state extraction and concise response wording. They do not generate the final recommendation rows. Product names, URLs, and test types always come from deterministic catalog lookup. LLM outputs are validated with Pydantic; invalid outputs fall back to rule-based extraction. This reduces hallucination risk while preserving conversational flexibility.

### Evaluation

I evaluate in three layers. First, hard API tests verify schema compliance, catalog membership, empty recommendations during clarification/refusal, and stable behavior for malformed input. Second, behavior probes test vague-query clarification, detailed-query recommendation, refinement, comparison, refusal, prompt-injection resistance, and duration/test-type constraints. Third, the public conversation traces are replayed locally and final Recall@10 is computed against the labeled shortlists.

For every missed expected assessment, I inspect whether the issue came from missing catalog data, poor synonym coverage, or ranking weights. I then update synonyms, metadata boosts, and penalties, while rerunning behavior probes to avoid regressions.

### What did not work well

A pure LLM recommender was too risky because it could invent product URLs or over-explain unsupported catalog facts. A pure vector search baseline was also insufficient because it missed constraints such as "add personality", "under 30 minutes", and job-level fit. The final design combines semantic retrieval with deterministic catalog validation and metadata-aware ranking.

### Deployment

The service is deployed as a FastAPI app with `GET /health` and `POST /chat`. The cleaned catalog and retrieval index are loaded at startup. The service performs no per-conversation storage and no runtime scraping, keeping it compatible with the evaluator's stateless replay and 30-second timeout.

