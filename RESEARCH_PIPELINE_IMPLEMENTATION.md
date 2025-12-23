# Research-Enhanced Red Team Pipeline - Implementation Summary

## Overview

This document summarizes the complete implementation of the research-enhanced red team pipeline with VP-centric analysis, chunk deduplication, and intelligent confirmation generation.

## Implementation Phases

### ✅ Phase 1: Chunk Deduplication & Precedence

**Files Created:**
- `/app/core/chunk_deduplication.py` - Post-retrieval deduplication using semantic similarity
- `/app/db/chunk_management.py` - Status propagation from entities to chunks
- `/migrations/0011_chunk_metadata_indexes.sql` - Performance indexes for metadata filtering

**Files Modified:**
- `/app/db/phase0.py` - Added `vector_search_with_priority()` for status-aware search

**Key Features:**
- **Semantic Deduplication**: Removes chunks with >85% cosine similarity
- **Section Limits**: Max 3 chunks per section type (configurable)
- **MMR Reranking**: Balances relevance (70%) vs diversity (30%)
- **Priority Boosting**:
  - confirmed_client: 3x boost
  - confirmed_consultant: 2x boost
  - draft: 1x baseline

### ✅ Phase 2: Research Signal Ingestion

**Files Created:**
- `/app/core/research_validation.py` - Quality validation for research reports

**Files Modified:**
- `/app/api/research.py` - Enhanced ingestion with validation and metrics

**Key Features:**
- **Validation System**: 3 severity levels (info, warning, error)
- **Completeness Scoring**: 0-100% based on 12 key sections
- **Content Statistics**: Word counts, section counts, quality metrics
- **Section-Based Chunking**: Semantic sections (personas, features, risks, etc.)
- **Authority Tagging**: All research tagged with `authority="research"`

### ✅ Phase 3: VP-Centric Red Team Analysis

**Files Created:**
- `/app/core/vp_validation.py` - VP completeness validation

**Files Modified:**
- `/app/graphs/red_team_graph.py` - Integrated deduplication and priority search
- `/app/chains/red_team_research.py` - Complete prompt rewrite with 5-gate framework

**Key Features:**

#### 5-Gate Validation Framework:

1. **Gate 1: VP Completeness** (Critical - Can we build?)
   - Validates data schema (entities, fields, types)
   - Validates business logic (rules, special sauce)
   - Validates transition logic (triggers)
   - Blocks prototype if gaps found

2. **Gate 2: Market Validation** (Important - Is this optimal?)
   - Compares VP against research insights
   - Checks must-have features included
   - Validates UX best practices
   - Benchmarks time-to-value

3. **Gate 3: Assumption Testing** (Important - Are assumptions solid?)
   - Identifies embedded assumptions (connectivity, device, identity, persistence)
   - Tests assumptions against research
   - Estimates blast radius if assumptions change
   - Flags broken assumptions as CRITICAL

4. **Gate 4: Scope Protection** (Prevent distraction)
   - Identifies features without VP steps
   - Flags "amazing but complex" features for v2
   - Keeps VP focused on core first principles
   - De-prioritizes common features unless differentiators

5. **Gate 5: Wow Factor** (Client experience)
   - Evaluates time to first value
   - Assesses cognitive load per step
   - Identifies "magic moments"
   - Checks competitive advantage

#### VP-Centric Philosophy:
- **VP is THE product** (not documentation, the actual user journey)
- **Features enable VP steps** (no VP step = question if feature needed)
- **Research optimizes VP** (informs, validates, challenges)
- **Goal: 80% right** (minimize refinement sessions)
- **Prototype-ready focus** (client says "wow, they get me!")

### ✅ Phase 4: Insight Management & Application

**Files Modified:**
- `/app/api/insights.py` - Complete implementation of insight application and confirmation generation
- `/app/core/schemas_redteam.py` - Added `gate` field to RedTeamInsight schema

**Key Features:**

#### Insight Application (`/insights/{id}/apply`):
- Updates features (nested field support: `details.summary`)
- Creates new features from insights with evidence
- Updates PRD sections (adds client_needs items)
- Updates VP steps (enrichment + needed items)
- Creates state revisions for audit trail

#### Confirmation Generation (`/insights/{id}/confirm`):

**Email vs Meeting Recommendation:**
```python
Complexity Score =
  + Severity (critical=3, important=2, minor=1)
  + Targets (>3=+2, >1=+1)
  + Gate (completeness/assumption=+2, validation/wow=+1)
  + Category (logic/scope/security=+1)

If score >= 6: Meeting (high complexity)
If score >= 4: Meeting (multiple areas)
Else: Email (focused change)
```

**Client-Friendly Formatting:**
- **Critical** → "Important Decision: {title}"
- **Important** → "Strategic Input Needed: {title}"
- **Minor** → "Quick Question: {title}"

**Gate Context:**
- Completeness: "We want to make sure we have all the details..."
- Validation: "Based on our research, we want to validate..."
- Assumption: "We want to confirm an assumption..."
- Wow: "We have an idea that could improve..."
- Scope: "We want to clarify what should be in scope..."

### ✅ Phase 5: Pipeline Integration & Testing

**Files Modified:**
- `/app/api/enrich_vp.py` - Enhanced auto-trigger with research context

**Files Created:**
- `/tests/test_research_enhanced_pipeline.py` - Comprehensive end-to-end tests

**Key Features:**

#### Auto-Trigger Logic:
1. After VP enrichment completes, checks if all phases complete:
   - Features enriched ✓
   - PRD sections enriched ✓
   - VP steps enriched ✓

2. If all complete, triggers red team in background:
   - Checks baseline gate
   - Detects research signals automatically
   - Passes `include_research=True` if research exists
   - Creates job for tracking
   - Handles errors gracefully

#### Test Coverage:
- VP completeness validation (critical/important/minor gaps)
- Chunk deduplication (semantic similarity, section limits)
- MMR reranking (relevance vs diversity)
- Red team prompt construction (5 gates, VP-centric)
- Email/meeting recommendation (complexity scoring)
- Client-friendly formatting (severity, gate context)
- End-to-end integration (VP gaps → insights → confirmations)

## Usage Guide

### 1. Ingest Research Signals

```bash
POST /v1/ingest/research
{
  "project_id": "uuid",
  "source": "perplexity_deep_research",
  "reports": [
    {
      "id": "report_1",
      "title": "Market Analysis",
      "deal_id": "deal_123",
      "personas": [...],
      "features_must_have": [...],
      # ... other sections
    }
  ]
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "job_id": "uuid",
  "ingested": [
    {
      "report_id": "report_1",
      "title": "Market Analysis",
      "signal_id": "uuid",
      "chunks_inserted": 24
    }
  ]
}
```

### 2. Enrich VP Steps (Auto-triggers Red Team)

```bash
POST /v1/agents/enrich-vp
{
  "project_id": "uuid",
  "include_research": true,  # Use research context
  "top_k_context": 50
}
```

**What Happens:**
1. Enriches VP steps with data schemas, business logic, transitions
2. Checks if all enrichment phases complete
3. **Auto-triggers red team** with research context if complete
4. Red team runs 5-gate analysis
5. Generates insights with gate categories

### 3. Run Red Team Manually (if needed)

```bash
POST /v1/agents/red-team
{
  "project_id": "uuid",
  "include_research": true
}
```

**Response:**
```json
{
  "run_id": "uuid",
  "job_id": "uuid",
  "insights_count": 12,
  "insights_by_severity": {
    "critical": 2,
    "important": 6,
    "minor": 4
  },
  "insights_by_category": {
    "completeness": 3,
    "validation": 4,
    "assumption": 2,
    "scope": 2,
    "wow": 1
  }
}
```

### 4. Review Insights

```bash
GET /v1/insights?project_id=uuid&status=open&limit=50
```

**Example Insight:**
```json
{
  "id": "uuid",
  "severity": "critical",
  "gate": "completeness",
  "category": "data",
  "title": "Missing user data schema for signup flow",
  "finding": "The user signup VP step lacks data schema definition",
  "why": "Cannot build prototype without knowing what user data to collect",
  "suggested_action": "needs_confirmation",
  "targets": [
    {"kind": "vp_step", "id": null, "label": "User signup"}
  ],
  "evidence": [
    {
      "chunk_id": "uuid",
      "excerpt": "User signup requires email, password, and profile info",
      "rationale": "VP step enrichment context"
    }
  ],
  "status": "open"
}
```

### 5. Generate Confirmation (for client)

```bash
POST /v1/insights/{insight_id}/confirm
```

**Response:**
```json
{
  "confirmation_id": "uuid",
  "insight_id": "uuid",
  "status": "created",
  "recommended_channel": "meeting",
  "channel_rationale": "High complexity - requires discussion and alignment"
}
```

**Confirmation Item Created:**
```json
{
  "id": "uuid",
  "project_id": "uuid",
  "key": "insight_abc123",
  "prompt": "Important Decision: Missing user data schema for signup flow",
  "detail": "We want to make sure we have all the details needed to build this effectively.\n\nThe user signup VP step lacks data schema definition.\n\nWhy this matters: Cannot build prototype without knowing what user data to collect",
  "options": ["Approve", "Reject", "Modify"],
  "status": "open",
  "metadata": {
    "insight_id": "uuid",
    "recommended_channel": "meeting",
    "channel_rationale": "High complexity - requires discussion and alignment",
    "complexity_score": 7,
    "severity": "critical",
    "gate": "completeness",
    "category": "data"
  }
}
```

### 6. Apply Insight (consultant confirms)

```bash
PATCH /v1/insights/{insight_id}/apply
```

**What Happens:**
1. Loads insight and validates status = 'queued'
2. Applies changes to:
   - Features (modify fields or create new)
   - PRD sections (add client_needs items)
   - VP steps (update enrichment + needed items)
3. Marks insight as 'applied'
4. Creates state revision for audit

## Key Design Principles

### Never Auto-Confirm
- LLM proposes, humans approve
- Consultant confirms first
- Client sees only strategic decisions
- System recommends channel (email vs meeting)

### VP is THE Product
- Features exist to enable VP steps
- No VP step = question if feature needed
- Research optimizes VP, doesn't override client vision
- Goal: prototype-ready VP (80% right)

### Evidence-Based
- Every insight requires chunk_id + excerpt + rationale
- Every fact traces to source signal
- Status propagates from entities to chunks
- Audit trail via state revisions

### Minimize Client Burden
- Wrap questions in agenda
- Generate minimal confirmations
- Client-friendly language (no jargon)
- Strategic questions only (consultant handles tactical)

## Database Schema Updates

### Insights Table (enhanced)
- Added `gate` field: "completeness" | "validation" | "assumption" | "scope" | "wow"
- Status: "open" → "queued" → "applied" | "dismissed"

### Signal Chunks Metadata (enhanced)
```json
{
  "authority": "client" | "research",
  "confirmation_status": "draft" | "confirmed_consultant" | "confirmed_client",
  "section_type": "features_must_have" | "personas" | "risks" | ...
}
```

### Indexes Created
```sql
CREATE INDEX idx_signal_chunks_confirmation_status ON signal_chunks ((metadata->>'confirmation_status'));
CREATE INDEX idx_signal_chunks_authority ON signal_chunks ((metadata->>'authority'));
CREATE INDEX idx_signal_chunks_section_type ON signal_chunks ((metadata->>'section_type'));
```

Note: Project filtering happens via JOIN with signals table in the vector search function.

## Testing

Run comprehensive tests:

```bash
# Install dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/test_research_enhanced_pipeline.py -v

# Run specific test class
pytest tests/test_research_enhanced_pipeline.py::TestVPCompletenessValidation -v

# Run with coverage
pytest tests/test_research_enhanced_pipeline.py --cov=app --cov-report=html
```

## Monitoring & Debugging

### Logging
All operations log structured events with:
- `run_id`: Tracks entire operation
- `job_id`: Database job record
- `project_id`: Project being processed
- Key metrics: chunk counts, insight counts, completeness scores

### Key Metrics to Monitor
- Research signal completeness scores
- VP step completeness percentages
- Insight severity distribution
- Email vs meeting recommendation ratio
- Chunk deduplication effectiveness

### Debug Queries

**Check research signals:**
```sql
SELECT id, metadata->>'title', metadata->>'completeness_score'
FROM signals
WHERE signal_type = 'market_research'
  AND project_id = 'uuid';
```

**Check VP completeness:**
```sql
SELECT step_index, label,
  enrichment->>'data_schema' IS NOT NULL as has_data,
  enrichment->>'business_logic' IS NOT NULL as has_logic,
  enrichment->>'transition_logic' IS NOT NULL as has_transition
FROM vp_steps
WHERE project_id = 'uuid'
ORDER BY step_index;
```

**Check insight distribution:**
```sql
SELECT
  metadata->>'gate' as gate,
  metadata->>'severity' as severity,
  COUNT(*) as count
FROM insights
WHERE project_id = 'uuid'
  AND status = 'open'
GROUP BY gate, severity
ORDER BY gate, severity;
```

## Next Steps

### Future Enhancements (not implemented)
1. **Agenda Generation**: Wrap multiple confirmations into single meeting agenda
2. **Email Template Generation**: Generate ready-to-send client emails
3. **Web Search Integration**: Replace mock web_search with real API (Brave, Serper)
4. **Assumption Graph**: Visualize assumption dependencies and blast radius
5. **Prototype Auto-Generation**: Generate prototype payload from VP
6. **Real-time Status Updates**: WebSocket notifications for async operations

### Migration Path
1. Run database migration: `migrations/0011_chunk_metadata_indexes.sql`
2. Backfill chunk statuses: `bulk_update_chunk_status_for_project()`
3. Re-run red team on existing projects to generate gate-categorized insights
4. Review and apply insights to update state

## Support

For issues or questions:
- Check logs with structured search: `grep "run_id={uuid}"`
- Review job status: `SELECT * FROM jobs WHERE id = 'uuid'`
- Inspect state revisions: `SELECT * FROM state_revisions WHERE project_id = 'uuid' ORDER BY created_at DESC`

---

**Implementation completed:** 2025-12-22
**Total files created:** 6
**Total files modified:** 7
**Test coverage:** 14 test classes, 25+ test cases
**All phases complete:** ✅
