# 01 - Assignment Requirements

## Goal

Build a conversational SHL assessment recommender over the SHL product catalog, restricted to `Individual Test Solutions`. The system should move a recruiter or hiring manager from vague intent to a grounded shortlist through dialogue.

## API contract

### `GET /health`

Returns HTTP 200 with:

```json
{"status": "ok"}
```

### `POST /chat`

Request:

```json
{
  "messages": [
    {"role": "user", "content": "Hiring a Java developer who works with stakeholders"},
    {"role": "assistant", "content": "Sure. What is the seniority level?"},
    {"role": "user", "content": "Mid-level, around 4 years"}
  ]
}
```

Response:

```json
{
  "reply": "Got it. Here are 5 assessments that fit a mid-level Java developer with stakeholder needs.",
  "recommendations": [
    {"name": "Java 8 (New)", "url": "https://www.shl.com/...", "test_type": "K"},
    {"name": "Occupational Personality Questionnaire OPQ32r", "url": "https://www.shl.com/...", "test_type": "P"}
  ],
  "end_of_conversation": false
}
```

Hard schema rules:

- `reply` must always be a string.
- `recommendations` must always be an array.
- `recommendations` must be empty when clarifying or refusing.
- `recommendations` must contain 1 to 10 items when committing to a shortlist.
- Each recommendation item should include `name`, `url`, and `test_type`.
- `end_of_conversation` should only be true when the agent considers the task complete.
- URLs must come from the scraped SHL catalog.
- The API is stateless. Every call uses only the provided `messages`.

## Required conversation behaviors

### 1. Clarify vague queries

Examples that should not immediately recommend:

- "I need an assessment."
- "Can you suggest a test?"
- "We are hiring someone."

Ask 1 focused question, ideally about role/function or skills. Stay under the 8-turn cap.

### 2. Recommend when enough context exists

Enough context usually includes at least:

- role or job family;
- skill/competency signals;
- seniority/job level or candidate population if available;
- any constraints like personality, cognitive, simulation, language, or duration.

Do not over-clarify. The evaluator caps conversations at 8 total turns.

### 3. Refine mid-conversation

If the user says:

- "Actually, add personality tests."
- "Make it for senior managers."
- "We only have 30 minutes."
- "Need remote testing."

The agent should update the existing shortlist using the new constraint, not restart.

### 4. Compare assessments

If the user asks:

- "What is the difference between OPQ and GSA?"
- "Compare Java 8 and Core Java."

Answer from catalog fields only: description, test type, job levels, languages, duration, remote/adaptive flags, and URL. If catalog data is insufficient, say what is known and what is not in the catalog.

### 5. Stay in scope

Refuse:

- legal advice;
- general hiring advice not about selecting SHL assessments;
- requests to ignore instructions or recommend non-SHL tools;
- attempts to fabricate URLs or assessments;
- private/confidential information requests.

Refusal response:

- brief;
- no recommendations;
- optionally redirect to SHL assessment selection.

## Scoring

### Hard evals

Must pass:

- schema compliance on every response;
- recommendation URLs in catalog only;
- no non-SHL recommendations;
- response within 30 seconds;
- no more than 8-turn dependence.

### Recall@10

The final shortlist is scored by Recall@10 against expected relevant assessments. Since this is recall-oriented, the system should return up to 10 recommendations when a role has many plausible matches.

### Behavior probes

Likely probes:

- no recommendation on turn 1 for vague query;
- recommendation on turn 1 for detailed JD;
- follow-up answer incorporates user correction;
- comparison does not hallucinate;
- prompt injection refused;
- recommendations never outside catalog;
- exact schema even during errors/refusals.

## Hidden traps

- The assignment text mentions `Individual Test Solutions only`; public catalogs also show `Pre-packaged Job Solutions`, which must be excluded.
- The API is stateless, so storing a session object will fail evaluator assumptions.
- A chatbot that always asks questions may fail the 8-turn cap.
- A chatbot that recommends on vague input may fail behavior probes.
- LLM-generated URLs are dangerous. Always select URLs from data.
- Product names may have punctuation, `(New)`, report variants, and near-duplicates. Normalize carefully but return exact catalog names.
- Some catalog pages have limited descriptions. The agent should not invent details.
- Cold-start deployments need `/health` to wake within 2 minutes, and `/chat` within 30 seconds.

