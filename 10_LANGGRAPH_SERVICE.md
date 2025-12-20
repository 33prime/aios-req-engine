# LangGraph Service Rules (AIOS Req Engine)

## Mental model
This service is a requirements compiler:
(signal) -> (facts) -> (proposed deltas) -> (policy-gated updates) -> (canonical state)

## Graph boundaries
- Graph nodes can call:
  - deterministic functions (policy, derivations)
  - tools (DB read/write helpers)
  - LLM chains (structured output only)
- Graph nodes must NOT:
  - embed SQL in the node
  - perform complex DB logic inline
  - mutate global state

## Required graphs (v1)
- ingest_signal: normalize -> chunk/embed -> extract_facts -> persist_facts
- reconcile_facts: load_state -> retrieve_candidates -> propose_delta -> apply_policy -> persist_updates
- enrich_requirements: select_targets -> generate_enrichments -> validate -> persist
- red_team: load_state -> generate_insights -> validate -> persist

## LLM usage rules
- Use structured outputs (Pydantic) for every LLM response.
- Keep prompts short and specific.
- Prefer 1–3 LLM calls per request; avoid long sequential chains.
- On schema failure: one retry with a "fix-to-schema" prompt, then hard fail.

## Policy rules (must be deterministic)
- Never auto-edit confirmed_client canonical fields.
- Contradictions create a queued confirmation item, not a silent overwrite.
- Enrichments write to separate enrichment records/fields.

## Traceability
Every run has:
- run_id (uuid)
- model name
- prompt_version
- schema_version
Saved alongside outputs.

## Prompt discipline
- No chain > 200 lines; prompts versioned.
- No monolith prompt files.

