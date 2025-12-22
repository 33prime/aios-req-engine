# AIOS Req Engine — Project Context

## What this repo is
A microservice that ingests messy client signals (emails, transcripts, notes, file text) and turns them into a traceable evidence store and (later) a continuously updated requirements system.

This service will eventually plug into a production Supabase database via an adapter layer. For now, we validate engine mechanics using a dev Supabase project.

## Key invariants
- LLMs never write canonical truth directly. They propose; deterministic policy decides.
- Provenance is mandatory: every canonical statement must be traceable to evidence (signals/chunks).
- Confirmed-by-client canonical fields are never silently overwritten; contradictions become queued confirmations.
- Outputs must be structured (Pydantic/JSON schema). No freeform blobs.

## Authority Model (Phase 1.3)
- `metadata.authority = "client"`: Signals from direct client input (emails, transcripts, notes, files). These are **ground truth**.
- `metadata.authority = "research"`: Signals from deep research (n8n market research). These are **context only**, not binding.
- When analyzing requirements, client authority takes precedence over research authority.
- All ingestion endpoints default missing authority to "client".

## Baseline Gate (Phase 1.3)
Before running research ingestion or red-team analysis, a project must meet baseline requirements:
- **Auto mode** (default): `ready = (client_signals >= min) AND (fact_runs >= min)`
- **Override mode**: `ready = baseline_ready_override` (manual flag)

Endpoints protected by baseline gate:
- `POST /v1/ingest/research`
- `POST /v1/agents/red-team`

## Roadmap
### Phase 0 (done)
- POST /v1/ingest: store signal, chunk, embed, store chunks
- POST /v1/search: embed query, vector search via pgvector function
- Tables: signals, signal_chunks, requirements (placeholder), requirement_links (placeholder), jobs

### Phase 0.5 (done)
- File ingestion endpoint (text-based files only; no OCR/PDF parsing)
- Job tracking rows for ingest/search runs in jobs table
- API ergonomics: return run_id + job_id for traceability

### Phase 1 (done)
- LangGraph agent for structured fact extraction from signals
- Tables: extracted_facts
- Endpoint: POST /v1/agents/extract-facts

### Phase 1.2 (done)
- Agent run logging and replay capabilities
- Tables: agent_runs
- Endpoints: POST /v1/agents/replay/{agent_run_id}

### Phase 1.3 (done)
- Baseline gate for controlling research/red-team access
- Authority model for differentiating client vs research signals
- Research ingestion (n8n deep research JSON with section-level chunking)
- Red-team agent for requirements analysis
- Tables: project_gates, insights
- Endpoints:
  - GET/PATCH /v1/projects/{project_id}/baseline
  - POST /v1/ingest/research
  - POST /v1/agents/red-team
  - PATCH /v1/insights/{insight_id}/status

### Phase 2A (current)
- Canonical state tables: prd_sections, vp_steps, features
- State Builder agent transforms facts + research into structured PRD/VP/Features
- All outputs are proposals (status="draft") with evidence references
- Tables: prd_sections, vp_steps, features
- Endpoints:
  - POST /v1/state/build
  - GET /v1/state/prd
  - GET /v1/state/vp
  - GET /v1/state/features

### Phase 2B (done)
- Reconcile agent for updating canonical state
- Confirmation queue for client approval
- Outreach drafting for client_needs/needed items
- Policy gates for canonical updates
- Replay on system changes
- Tables: confirmation_items, project_state, state_revisions
- Endpoints:
  - POST /v1/state/reconcile
  - GET /v1/confirmations
  - PATCH /v1/confirmations/{id}/status
  - POST /v1/outreach/draft

### Phase 2C (done)
- On-demand enrichment agents for canonical tabs
- Feature enrichment agent (implemented)
- PRD enrichment agent (implemented)
- VP enrichment agent (implemented)
- Evidence-backed structured details without changing canonical truth
- Never auto-confirms; always drafts/proposals
- Tables: features.details, prd_sections.enrichment, vp_steps.enrichment
- Endpoints:
  - POST /v1/agents/enrich-features
  - POST /v1/agents/enrich-prd
  - POST /v1/agents/enrich-vp

## Current endpoints
- GET /health
- POST /v1/ingest
- POST /v1/ingest/file
- POST /v1/ingest/research (Phase 1.3)
- POST /v1/search
- POST /v1/agents/extract-facts
- POST /v1/agents/replay/{agent_run_id}
- POST /v1/agents/red-team (Phase 1.3)
- POST /v1/agents/enrich-features (Phase 2C)
- POST /v1/agents/enrich-prd (Phase 2C)
- POST /v1/agents/enrich-vp (Phase 2C)
- GET /v1/projects/{project_id}/baseline (Phase 1.3)
- PATCH /v1/projects/{project_id}/baseline (Phase 1.3)
- PATCH /v1/insights/{insight_id}/status (Phase 1.3)
- POST /v1/state/build (Phase 2A)
- POST /v1/state/reconcile (Phase 2B)
- GET /v1/state/prd (Phase 2A)
- GET /v1/state/vp (Phase 2A)
- GET /v1/state/features (Phase 2A)
- GET /v1/confirmations (Phase 2B)
- PATCH /v1/confirmations/{id}/status (Phase 2B)
- POST /v1/outreach/draft (Phase 2B)

## Module boundaries
- app/api: HTTP handlers only (no business logic)
- app/core: config, chunking, embeddings, file_text, schemas, research rendering, state inputs
- app/db: Supabase access (signals, chunks, jobs, facts, insights, gates, prd, vp, features)
- app/chains: LLM chains (extract_facts, red_team, build_state)
- app/graphs: LangGraph orchestration (extract_facts_graph, red_team_graph, build_state_graph)

## Tables (Supabase Postgres)
- signals: Raw client signals with metadata
- signal_chunks: Chunked text with embeddings (pgvector)
- jobs: Job tracking for async operations
- extracted_facts: Structured facts from LLM extraction
- agent_runs: Agent execution logs for replay
- project_gates: Baseline gate configuration per project (Phase 1.3)
- insights: Red-team findings with status tracking (Phase 1.3)
- prd_sections: PRD tab sections with evidence + enrichment JSONB (Phase 2A/2C)
- vp_steps: Value Path workflow steps with evidence + enrichment JSONB (Phase 2A/2C)
- features: Key Features list with MVP flags + details JSONB (Phase 2A/2C)
- confirmation_items: Client confirmation queue (Phase 2B)
- project_state: Checkpointing for reconciliation (Phase 2B)
- state_revisions: Audit trail for state changes (Phase 2B)
- requirements: Canonical requirements (placeholder for Phase 2B+)
- requirement_links: Links between requirements and evidence (placeholder for Phase 2B+)
