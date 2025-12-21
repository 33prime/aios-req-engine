# aios-req-engine

LangGraph-based requirements compilation and management microservice.

## Architecture

This service follows clean architecture principles:

- **app/api**: HTTP endpoints (request validation + orchestration)
- **app/graphs**: LangGraph orchestration workflows
- **app/chains**: LLM prompts and parsers
- **app/core**: Configuration, schemas, policy, logging
- **app/db**: Supabase/Postgres database access layer
- **tests**: Unit and integration tests

## Local Development

### Prerequisites

- Python 3.11 or higher
- pip and venv

### Setup

1. **Create and activate virtual environment:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

2. **Install dependencies:**

```bash
pip install -e ".[dev]"
```

3. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

4. **Run the service:**

```bash
uvicorn app.main:app --reload
```

The service will be available at `http://localhost:8000`

- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`

### Testing

Run tests:

```bash
pytest -q
```

Run with verbose output:

```bash
pytest -v
```

### Code Quality

Lint and format code:

```bash
ruff check .
ruff format .
```

Auto-fix issues:

```bash
ruff check . --fix
```

## Project Structure

```
aios-req-engine/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── api/                 # HTTP endpoints
│   ├── chains/              # LLM prompts & parsers
│   ├── core/                # Config, schemas, policy
│   ├── db/                  # Database access
│   └── graphs/              # LangGraph workflows
├── tests/
│   └── test_health.py
├── migrations/              # SQL migrations
├── pyproject.toml
├── .env.example
└── README.md
```

## Phase 0: Signal Ingestion & Vector Search

Phase 0 implements a minimal Supabase-backed ingestion pipeline with pgvector for semantic search.

### Database Setup

Before using the API, run the migration in your Supabase SQL editor:

1. Open your Supabase project SQL editor
2. Copy contents of `migrations/0001_phase0.sql`
3. Execute the SQL to create tables and functions
4. Verify tables created: `signals`, `signal_chunks`, `requirements`, `requirement_links`, `jobs`

### API Endpoints

#### POST /v1/ingest

Ingest a signal (email, transcript, note, or file), chunk it, generate embeddings, and store in Supabase.

**Request:**
```json
{
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "signal_type": "email",
  "source": "user@example.com",
  "raw_text": "Your email or document text here...",
  "metadata": {
    "subject": "Project requirements",
    "date": "2024-01-15"
  }
}
```

**Response:**
```json
{
  "run_id": "789e4567-e89b-12d3-a456-426614174000",
  "signal_id": "456e4567-e89b-12d3-a456-426614174000",
  "chunks_inserted": 5
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "signal_type": "note",
    "source": "meeting-notes.txt",
    "raw_text": "User wants a dashboard with real-time analytics...",
    "metadata": {"meeting": "kickoff", "date": "2024-01-15"}
  }'
```

#### POST /v1/search

Search for similar signal chunks using semantic vector search.

**Request:**
```json
{
  "query": "What are the dashboard requirements?",
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "top_k": 5
}
```

**Response:**
```json
{
  "results": [
    {
      "signal_id": "456e4567-e89b-12d3-a456-426614174000",
      "chunk_id": "789e4567-e89b-12d3-a456-426614174000",
      "chunk_index": 0,
      "content": "User wants a dashboard with real-time analytics...",
      "similarity": 0.89,
      "start_char": 0,
      "end_char": 150,
      "metadata": {"meeting": "kickoff", "date": "2024-01-15"}
    }
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "dashboard requirements",
    "project_id": "123e4567-e89b-12d3-a456-426614174000",
    "top_k": 10
  }'
```

### Environment Variables

Required environment variables (add to `.env`):

```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=sk-your-openai-key

# Optional
REQ_ENGINE_ENV=dev
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIM=1536
```

### Features

- **Text Chunking**: Splits text into overlapping chunks (default: 1200 chars, 120 overlap)
- **Vector Embeddings**: Uses OpenAI text-embedding-3-small (1536 dimensions)
- **Semantic Search**: pgvector cosine similarity search
- **Structured Logging**: All operations logged with run_id for traceability
- **Type Safety**: Full Pydantic validation on all inputs/outputs

## Phase 1: Structured Fact Extraction

Phase 1 adds a LangGraph agent that extracts structured facts from ingested signals with full provenance tracking.

### Database Setup

Before using Phase 1 endpoints, run the migration in your Supabase SQL editor:

1. Open your Supabase project SQL editor
2. Copy contents of `migrations/0002_phase1_extracted_facts.sql`
3. Execute the SQL to create the `extracted_facts` table

### API Endpoints

#### POST /v1/agents/extract-facts

Extract structured facts from an ingested signal. This endpoint:
- Loads the signal and its chunks from Supabase
- Selects and truncates chunks deterministically
- Calls an OpenAI model to extract structured facts
- Validates output against strict Pydantic schemas
- Persists results to `extracted_facts` table

**Request:**
```json
{
  "signal_id": "456e4567-e89b-12d3-a456-426614174000",
  "project_id": "123e4567-e89b-12d3-a456-426614174000",
  "top_chunks": 10
}
```

- `signal_id` (required): UUID of the signal to extract facts from
- `project_id` (optional): If provided, validates it matches the signal's project_id
- `top_chunks` (optional): Override max chunks to process (default: 20)

**Response:**
```json
{
  "run_id": "789e4567-e89b-12d3-a456-426614174000",
  "job_id": "abc12345-e89b-12d3-a456-426614174000",
  "extracted_facts_id": "def67890-e89b-12d3-a456-426614174000",
  "summary": "Extracted 3 facts about user authentication and budget constraints.",
  "facts_count": 3,
  "open_questions_count": 2,
  "contradictions_count": 0
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/v1/agents/extract-facts \
  -H "Content-Type: application/json" \
  -d '{
    "signal_id": "456e4567-e89b-12d3-a456-426614174000"
  }'
```

### Extracted Facts Schema

Facts are stored as structured JSONB containing:

- **summary**: Brief summary of extracted content
- **facts**: List of `FactItem` objects with:
  - `fact_type`: feature, constraint, persona, kpi, process, data_requirement, integration, risk, assumption
  - `title`: Short fact title
  - `detail`: Detailed description
  - `confidence`: low, medium, high
  - `evidence`: List of chunk references with excerpts
- **open_questions**: Questions needing answers (evidence optional)
- **contradictions**: Conflicts found in the signal (evidence required)

### Environment Variables (Phase 1)

Additional environment variables for fact extraction:

```bash
# Fact Extraction Model
FACTS_MODEL=gpt-4o-mini
FACTS_PROMPT_VERSION=facts_v1
FACTS_SCHEMA_VERSION=facts_v1
MAX_FACT_CHUNKS=20
MAX_FACT_CHARS_PER_CHUNK=900
```

### Key Invariants

- **Proposals only**: Phase 1 extracts facts but does NOT update the canonical `requirements` table
- **Evidence required**: Every fact and contradiction MUST include at least one evidence reference
- **Deterministic**: Chunk selection is in-order by chunk_index, capped and truncated
- **Linear execution**: LangGraph agent is strictly linear (no loops)
- **Job tracking**: All operations are tracked in the `jobs` table

## Phase 1.2: Agent Run Logging & Replay

Phase 1.2 adds comprehensive run logging and replay capabilities for all agent executions.

### Database Setup

Run the migration in your Supabase SQL editor:

1. Open your Supabase project SQL editor
2. Copy contents of `migrations/0003_phase1_2_agent_runs.sql`
3. Execute the SQL to create the `agent_runs` table

### Agent Run Logging

All agent executions are automatically logged to the `agent_runs` table with:
- **Input**: Safe replay input (identifiers only, no raw prompts)
- **Output**: Execution summary (not full results)
- **Status**: queued → processing → completed/failed
- **Timing**: started_at, completed_at for performance analysis
- **Provenance**: Links to job_id, run_id, signal_id, project_id

### Prompt Capture Policy

For privacy and storage efficiency, agent_runs stores:
- ✅ **Identifiers**: signal_id, project_id, top_chunks
- ✅ **Summaries**: counts, preview of first 5 facts
- ❌ **NOT stored**: raw signal text, chunk content, full prompts

Replay can re-fetch these from the database using stored identifiers.

### API Endpoints

#### POST /v1/agents/replay/{agent_run_id}

Replay a previous agent run with optional overrides. Creates a NEW run (preserves audit trail).

**Request:**
```json
{
  "override_model": "gpt-4o",
  "override_top_chunks": 10
}
```

- `override_model` (optional): Use a different model (e.g., "gpt-4o" instead of "gpt-4o-mini")
- `override_top_chunks` (optional): Override chunk count for replay

**Response:** Same as extract-facts (ExtractFactsResponse)

**Example: Replay with default settings**
```bash
curl -X POST http://localhost:8000/v1/agents/replay/<agent_run_id>
```

**Example: Replay with model override**
```bash
curl -X POST http://localhost:8000/v1/agents/replay/<agent_run_id> \
  -H "Content-Type: application/json" \
  -d '{
    "override_model": "gpt-4o",
    "override_top_chunks": 15
  }'
```

### Use Cases

**Debugging**: Inspect what went into and came out of any agent run
```sql
SELECT * FROM agent_runs WHERE status = 'failed' ORDER BY created_at DESC;
```

**Performance Analysis**: Measure agent execution times
```sql
SELECT 
  agent_name,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_seconds
FROM agent_runs 
WHERE status = 'completed'
GROUP BY agent_name;
```

**Replay for Testing**: Re-run with different model to compare results
```bash
# Original run used gpt-4o-mini
# Replay with gpt-4o to compare quality
curl -X POST http://localhost:8000/v1/agents/replay/<agent_run_id> \
  -H "Content-Type: application/json" \
  -d '{"override_model": "gpt-4o"}'
```

## Phase 2C: Enrichment Agents

**Status**: ✅ Implemented (Feature, PRD, and VP Enrichment Agents)

Phase 2C adds on-demand enrichment agents that make canonical "tabs" feel alive by providing structured detail + evidence WITHOUT changing canonical truth or statuses.

### Architecture

Enrichment agents follow the established patterns:
- **DB Layer**: `app/db/*.py` - Stores enrichment in dedicated JSONB columns
- **Core**: `app/core/*_enrich_inputs.py` - Context retrieval and prompt building
- **Chains**: `app/chains/enrich_*.py` - OpenAI SDK with safe parsing
- **Graphs**: `app/graphs/enrich_*_graph.py` - LangGraph linear workflows
- **API**: `app/api/enrich_*.py` - POST `/v1/agents/enrich-*` endpoints

### Key Features

✅ **Evidence Discipline**: Every enrichment item includes `EvidenceRef` with chunk_id, excerpt (≤280 chars), rationale

✅ **Never Auto-Confirm**: Enrichment outputs are ALWAYS drafts/proposals - consultant remains final arbiter

✅ **Safe Enrichment**: Does not modify canonical fields (name, is_mvp, status, etc.)

✅ **Idempotent**: Re-running does not create spam - material change detection prevents duplicate updates

✅ **Authority Respect**: Client signals inform enrichment but don't auto-confirm; research optional based on baseline gate

### API Usage

#### POST /v1/agents/enrich-features

Enrich features with structured details from project context.

**Request:**
```json
{
  "project_id": "uuid",
  "feature_ids": ["uuid1", "uuid2"],  // optional - null = all features
  "only_mvp": false,                  // optional - true = only MVP features
  "include_research": false,          // optional - true = include research signals
  "top_k_context": 24                 // optional - chunks to retrieve
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "job_id": "uuid",
  "features_processed": 5,
  "features_updated": 3,
  "summary": "Processed 5 features, successfully updated 3 features"
}
```

**Example - Enrich all features:**
```bash
curl -X POST http://localhost:8000/v1/agents/enrich-features \
  -H "Content-Type: application/json" \
  -d '{"project_id": "your-project-uuid"}'
```

**Example - Enrich only MVP features:**
```bash
curl -X POST http://localhost:8000/v1/agents/enrich-features \
  -H "Content-Type: application/json" \
  -d '{"project_id": "your-project-uuid", "only_mvp": true}'
```

### Enrichment Details Structure

Features get enriched with structured details in the `details` JSONB column:

```json
{
  "summary": "AI-generated summary of feature purpose and scope",
  "data_requirements": [
    {
      "entity": "User",
      "fields": ["id", "email"],
      "notes": "Required for authentication",
      "evidence": [
        {
          "chunk_id": "uuid",
          "excerpt": "Users need email for login...",
          "rationale": "Supports user data requirement"
        }
      ]
    }
  ],
  "business_rules": [...],
  "acceptance_criteria": [...],
  "dependencies": [...],
  "integrations": [...],
  "telemetry_events": [...],
  "risks": [...]
}
```

### Database Schema

**Migration 0008**: Added `details` JSONB column to `features` table:

```sql
ALTER TABLE public.features
ADD COLUMN IF NOT EXISTS details jsonb NOT NULL DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS details_model text null,
ADD COLUMN IF NOT EXISTS details_prompt_version text null,
ADD COLUMN IF NOT EXISTS details_schema_version text null,
ADD COLUMN IF NOT EXISTS details_updated_at timestamptz null;
```

### Configuration

Added to `app/core/config.py`:
- `FEATURES_ENRICH_MODEL`: Model for enrichment (default: gpt-4o-mini)
- `FEATURES_ENRICH_PROMPT_VERSION`: Prompt version tracking
- `FEATURES_ENRICH_SCHEMA_VERSION`: Schema version tracking
- `MAX_ENRICH_CHUNKS`: Max chunks per enrichment (default: 24)
- `MAX_ENRICH_CHARS_PER_CHUNK`: Max chars per chunk (default: 900)

### Testing

Comprehensive test suite includes:
- `tests/test_feature_enrich_parsing.py`: Schema validation and evidence constraints
- `tests/test_feature_enrich_agent_mock.py`: Mocked agent behavior testing
- `tests/test_feature_enrich_idempotent.py`: Idempotency verification

All tests pass with `pytest` and follow established mocking patterns.

### PRD Enrichment Agent

#### POST /v1/agents/enrich-prd

Enrich PRD sections with enhanced content and proposed client needs.

**Request:**
```json
{
  "project_id": "uuid",
  "section_slugs": ["personas", "key_features"],  // optional - null = all sections
  "include_research": false,                       // optional - true = include research signals
  "top_k_context": 24                              // optional - chunks to retrieve
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "job_id": "uuid",
  "sections_processed": 3,
  "sections_updated": 2,
  "summary": "Processed 3 PRD sections, successfully updated 2 sections"
}
```

### VP Enrichment Agent

#### POST /v1/agents/enrich-vp

Enrich Value Path steps with detailed implementation guidance.

**Request:**
```json
{
  "project_id": "uuid",
  "step_ids": ["uuid1", "uuid2"],  // optional - null = all steps
  "include_research": false,        // optional - true = include research signals
  "top_k_context": 24               // optional - chunks to retrieve
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "job_id": "uuid",
  "steps_processed": 4,
  "steps_updated": 3,
  "summary": "Processed 4 VP steps, successfully updated 3 steps"
}
```

### Database Schema

**Migration 0008**: Added `details` JSONB column to `features` table
**Migration 0009**: Added `enrichment` JSONB column to `prd_sections` table
**Migration 0010**: Added `enrichment` JSONB column to `vp_steps` table

### Configuration

Added to `app/core/config.py`:
- `FEATURES_ENRICH_MODEL`: Model for feature enrichment (default: gpt-4o-mini)
- `PRD_ENRICH_MODEL`: Model for PRD enrichment (default: gpt-4o-mini)
- `VP_ENRICH_MODEL`: Model for VP enrichment (default: gpt-4o-mini)
- Plus corresponding prompt/schema version settings

### Testing

Test suites for each agent:
- Schema validation and evidence constraints
- Mocked agent behavior testing
- Idempotency verification

All tests pass with `pytest` and follow established mocking patterns.

## Engineering Standards

See the following documentation for detailed engineering guidelines:

- `00_CORE_ENGINEERING_RULES.md` - Core principles and standards
- `10_LANGGRAPH_SERVICE.md` - LangGraph architecture rules
- `20_SUPABASE_PGVECTOR.md` - Database guidelines
- `30_TESTING_QUALITY.md` - Testing strategy
