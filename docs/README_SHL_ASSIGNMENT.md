# SHL Conversational Assessment Recommender - Working Pack

This folder contains a research and execution pack for the SHL Research Intern, AI take-home assignment.

## What the assignment is really asking

Build a deployed FastAPI service that behaves like a grounded conversational recommender for SHL Individual Test Solutions. It must:

- expose `GET /health` and `POST /chat`;
- accept full stateless conversation history on every `/chat` call;
- clarify vague requests before recommending;
- recommend 1 to 10 catalog assessments only when enough context exists;
- refine earlier recommendations when the user changes constraints;
- compare assessments using catalog data only;
- refuse off-topic, legal, general hiring advice, and prompt-injection attempts;
- return the exact required JSON schema every time.

The evaluator is not a fixed script. It replays conversations with an LLM-simulated user, so the system needs robust conversation-state extraction from the message history, not stored memory.

## Files in this pack

- `01_assignment_requirements.md` - Requirements, hard constraints, scoring, and hidden traps.
- `02_company_and_people_research.md` - SHL context, leadership, SHL Labs, products, and why this task matches their work.
- `03_existing_solution_landscape.md` - Public solution patterns, what already exists, and where they are weak for this assignment.
- `04_recommended_architecture.md` - Practical system architecture under the assignment constraints.
- `05_catalog_data_strategy.md` - How to scrape, normalize, validate, and use the SHL catalog safely.
- `06_agent_behavior_design.md` - Conversation policy, clarification/refinement/comparison/refusal behavior, and prompt design.
- `07_evaluation_plan.md` - Local tests and metrics to maximize Recall@10 and behavior-probe pass rate.
- `08_implementation_roadmap.md` - Day-by-day and module-by-module plan to finish before the deadline.
- `09_two_page_approach_draft.md` - A concise submission approach document draft.
- `10_interview_defense_notes.md` - Notes to defend design choices in a technical deep-dive.

## Recommended build direction

Use a mostly deterministic retrieval/ranking system with an LLM used only for bounded tasks:

- parse conversation history into a structured hiring need;
- rewrite/refine the query;
- produce natural-language replies from retrieved evidence.

Keep catalog membership, schema validation, refusal logic, and recommendation JSON deterministic. This is more reliable than letting an LLM free-form the final recommendation list.

## Immediate missing inputs

The pasted assignment references hidden links named `Assignment-Details`, `Form`, `Link`, and the public trace zip, but the actual URLs are not visible in the email text. Get/download these before implementation:

- the official assignment page, if different from the PDF text;
- the 10 public conversation traces zip;
- the submission form URL;
- any explicit evaluator examples or rubric details in the linked materials.

