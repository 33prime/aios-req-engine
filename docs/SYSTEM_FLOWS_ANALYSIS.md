# System Flows Analysis - Features, Personas, Foundation & Tasks

> **Analysis Date:** 2026-01-25
> **Status:** ✅ Comprehensive system documentation

---

## Table of Contents

1. [Features & Personas CRUD Flow](#1-features--personas-crud-flow)
2. [Task Generation System](#2-task-generation-system)
3. [Strategic Foundation System](#3-strategic-foundation-system)
4. [Signal Processing Architecture](#4-signal-processing-architecture)
5. [Backend Launch Commands](#5-backend-launch-commands)

---

## 1. Features & Personas CRUD Flow

### 1.1 Feature Lifecycle

**Database Schema:** `features` table
- **Core fields**: name, category, is_mvp, confidence, status, evidence
- **Lifecycle fields**: lifecycle_stage (discovered → refined → confirmed)
- **Confirmation fields**: confirmation_status (ai_generated, confirmed_consultant, confirmed_client)
- **Enrichment fields**: overview, target_personas, user_actions, system_behaviors, ui_requirements, rules, integrations

#### Feature Creation Flow

```
New Signal Added
    ↓
Signal Pipeline (app/graphs/build_state_graph.py)
    ├─ Load facts digest
    ├─ Retrieve chunks (vector search)
    ├─ Call LLM (app/chains/build_state.py)
    └─ Extract features with evidence
    ↓
Smart Bulk Replace (app/db/features.py:bulk_replace_features)
    ├─ Check for confirmed features
    ├─ IF confirmed features exist:
    │   ├─ Delete only ai_generated features
    │   ├─ Preserve confirmed features
    │   ├─ Check similarity of new features to confirmed
    │   └─ IF similar → MERGE evidence into confirmed feature
    └─ IF no confirmed features:
        └─ Full bulk replace (delete all, insert new)
    ↓
Derive Confirmation Status from Signal Authority
    ├─ client signals → confirmed_client
    ├─ consultant signals → confirmed_consultant
    └─ research/ai signals → ai_generated
    ↓
Feature Created with Evidence Attribution
```

**Key Functions:**
- `bulk_replace_features()` - Smart merge preserving confirmed features
- `_is_similar_to_any()` - Multi-strategy similarity matching
- `_derive_confirmation_status()` - Auto-confirm from signal authority
- `_detect_feature_conflicts()` - Creates cascade_events for conflicts

#### Feature Updates

**File:** `app/db/features.py`

1. **Lifecycle progression** (lines 404-472)
   ```python
   update_feature_lifecycle(feature_id, lifecycle_stage, confirmed_evidence)
   # Stages: discovered → refined → confirmed
   # Refreshes readiness cache on update
   ```

2. **Status updates** (lines 560-616)
   ```python
   update_feature_status(feature_id, status)
   # Updates BOTH status and confirmation_status columns
   # Triggers readiness cache refresh
   ```

3. **Field updates** (lines 619-703)
   ```python
   update_feature(feature_id, updates, run_id, source_signal_id, trigger_event)
   # Generic field updater used by A-Team agent
   # Tracks changes via change_tracking system
   # Refreshes readiness cache
   ```

4. **V2 Enrichment** (lines 706-782)
   ```python
   update_feature_enrichment(feature_id, overview, target_personas, ...)
   # Structured enrichment with 7 fields
   # Sets enrichment_status='enriched', enriched_at=now()
   # Refreshes readiness cache
   ```

**Enrichment Chain:** `app/chains/enrich_features_v2.py`
- Analyzes feature + project context
- Extracts: overview, target personas, user actions, system behaviors, UI requirements, rules, integrations
- Evidence-based extraction from signal chunks

---

### 1.2 Persona Lifecycle

**Database Schema:** `personas` table
- **Core fields**: name, slug, role, description
- **Demographics**: {age_range, location, industry, company_size}
- **Psychographics**: {tech_savvy, risk_tolerance, decision_making_style}
- **Goals**: Array of goal strings
- **Pain points**: Array of pain point strings
- **Confirmation**: confirmation_status, is_primary

#### Persona Creation Flow

```
New Signal Added
    ↓
State Builder (build_state_graph.py)
    ├─ Extracts personas from signals
    ├─ Derives confirmation_status from signal authority
    └─ Returns persona list
    ↓
Upsert Personas (app/db/personas.py:upsert_persona)
    ├─ Upsert by slug (unique per project)
    ├─ Merges new data with existing
    └─ Preserves confirmed fields
    ↓
Persona Created/Updated
```

**Key Functions:**
- `upsert_persona()` - Create or update by slug
- `update_persona()` - Generic field updater
- `set_primary_persona()` - Mark as primary (only one per project)

#### Primary Persona Extraction

**Chain:** `app/chains/extract_primary_persona.py`
- Analyzes signals to identify THE primary user
- Extracts demographics, psychographics, goals, pain points
- Saves to foundation table (separate from personas table!)
- Used by DI Agent for foundation building

**Enrichment:** `app/chains/enrich_personas_v2.py`
- Deep persona enrichment with behavioral patterns
- Jobs-to-be-done analysis
- Feature interaction preferences

---

### 1.3 Similarity Matching

**File:** `app/core/similarity.py`

Multi-strategy cascade for deduplication:

1. **Exact match** - Exact string equality
2. **Normalized match** - Lowercase, trimmed
3. **Fuzzy match** - Levenshtein distance (threshold: 0.85)
4. **Token set match** - Order-independent word matching
5. **Semantic match** - OpenAI embeddings (cosine similarity > 0.88)
6. **Substring match** - One name contains the other (80% threshold)

**Usage:**
- Feature deduplication during bulk_replace
- Persona merging
- Business driver deduplication
- Competitor ref deduplication

---

## 2. Task Generation System

### 2.1 Task Sources

**File:** `app/api/tasks.py`

Tasks are **computed dynamically** based on project state, NOT stored in a database. Each request computes fresh task list.

#### Task Categories & Triggers

| Category | Trigger | Priority | Example |
|----------|---------|----------|---------|
| **Discovery** | Unconfirmed prep questions | High | "Review discovery prep questions: 3 pending" |
| **Discovery** | All confirmed, portal disabled | High | "Send discovery prep to client" |
| **Confirmations** | Open confirmation items | Medium | "Review open confirmations: 5 items" |
| **Client** | Unreviewed client responses | High | "Review client responses: 2 new responses" |
| **Baseline** | Features ≥ 3, Personas ≥ 1, not finalized | Medium | "Finalize baseline for prototype phase" |
| **Meetings** | Scheduled meeting without agenda | Medium | "Prepare agenda for Discovery Kickoff" |
| **Proposals** | Pending proposals | Medium | "Review pending proposals: 4 awaiting decision" |

#### Task Structure

```typescript
interface ProjectTask {
  id: string                 // Unique task identifier
  title: string              // Task title
  description: string        // Task description
  priority: "high" | "medium" | "low"
  category: string           // Task category
  action_url: string         // Navigation URL
  action_type: string        // Action type (review, send, prepare, finalize)
  entity_id?: string         // Related entity ID
  entity_type?: string       // Related entity type
}
```

### 2.2 Task Computation Flow

```
GET /projects/{project_id}/tasks
    ↓
Verify project exists
    ↓
Query multiple tables for state:
    ├─ discovery_prep_questions (count confirmed vs total)
    ├─ confirmation_items (count status='open')
    ├─ info_requests (count status='complete' AND reviewed_at IS NULL)
    ├─ project_gates (check baseline_ready)
    ├─ features, personas (count for baseline check)
    ├─ meetings (upcoming without agenda)
    └─ proposals (count status='pending')
    ↓
Build task list based on conditions
    ↓
Sort by priority (high → medium → low)
    ↓
Return {tasks, total}
```

**Note:** Tasks are ephemeral - they reflect current state and are recalculated on each request.

---

## 3. Strategic Foundation System

### 3.1 Foundation Structure

**Database:** `project_foundation` table (one row per project)

**JSONB Columns (7 Gates):**

| Gate | Type | Purpose | Extracted By |
|------|------|---------|--------------|
| `core_pain` | CorePain | THE singular core problem | extract_core_pain |
| `primary_persona` | PrimaryPersona | THE primary user | extract_primary_persona |
| `wow_moment` | WowMoment | THE defining moment of value | identify_wow_moment |
| `design_preferences` | DesignPreferences | Design system preferences | Manual/DI Agent |
| `business_case` | BusinessCase | ROI, stakeholders, timeline | extract_business_case |
| `budget_constraints` | BudgetConstraints | Budget, timeline, resource limits | extract_budget_constraints |
| `confirmed_scope` | ConfirmedScope | MVP scope boundaries | Manual confirmation |

**Related Tables:**
- `business_drivers` - Pains, goals, KPIs extracted from signals
- `competitor_refs` - Competitors, design inspiration, feature inspiration
- `stakeholders` - Project stakeholders with roles and influence
- `constraints` - Technical, compliance, business constraints

---

### 3.2 Foundation Creation & Updates

#### New Project → Foundation

```
Project Created (empty foundation)
    ↓
Signal Added
    ↓
DI Agent Invoked (/di command)
    ↓
DI Agent Analyzes State
    ├─ OBSERVE: Checks what foundation elements exist
    ├─ THINK: Identifies gaps (no core_pain, no primary_persona)
    └─ DECIDE: Calls run_foundation tool
    ↓
run_foundation Tool Executes (app/agents/di_agent_tools.py:119)
    ├─ Calls run_strategic_foundation(project_id)
    └─ Returns extraction counts
    ↓
Strategic Foundation Chain (app/chains/run_strategic_foundation.py)
    ├─ 1. Enrich company info (Firecrawl + LLM)
    ├─ 2. Link stakeholders to project members (email matching)
    ├─ 3. Extract business drivers from signals
    ├─ 4. Extract competitor refs from signals
    └─ 5. Invalidate state snapshot
    ↓
Foundation Elements Created in business_drivers, competitor_refs, stakeholders
```

**Note:** The `run_strategic_foundation` chain does NOT directly populate the 7 gates. It populates supporting tables (business_drivers, competitors, stakeholders).

#### Core Pain Extraction

**Chain:** `app/chains/extract_core_pain.py`

```
DI Agent calls extract_core_pain tool
    ↓
Load project signals (up to 50, use 10 most recent)
    ↓
Build signal context (2000 chars per signal)
    ↓
Call LLM with SYSTEM_PROMPT (lines 21-92)
    ├─ Identify THE singular core pain
    ├─ Extract: statement, trigger, stakes, who_feels_it
    ├─ Confidence scoring (0-1)
    └─ Evidence references
    ↓
Parse JSON response → CorePain model
    ↓
Save to foundation table (app/db/foundation.py:save_foundation_element)
    ├─ Upsert to project_foundation.core_pain
    └─ Invalidate caches (state snapshot, readiness)
    ↓
Core Pain Extracted ✓
```

**Similar Patterns for:**
- `extract_primary_persona` → foundation.primary_persona
- `identify_wow_moment` → foundation.wow_moment
- `extract_business_case` → foundation.business_case
- `extract_budget_constraints` → foundation.budget_constraints

---

### 3.3 New Signal → Foundation Update

```
New Signal Added to Project
    ↓
Signal processed through heavyweight path (if >1000 chars)
    ↓
Build State Graph runs (optional)
    └─ Updates features, personas, VP steps, PRD sections
    ↓
DI Agent Invoked (manual or automatic)
    ↓
DI Agent OBSERVE phase
    ├─ Loads state snapshot (includes foundation summary)
    ├─ Checks: core_pain exists? primary_persona exists?
    └─ Analyzes new signal content
    ↓
DI Agent THINK phase
    ├─ "New signal discusses pain points..."
    ├─ "Current core_pain is X, new signal suggests Y"
    └─ "Should we update core_pain or is it still accurate?"
    ↓
DI Agent DECIDE phase
    ├─ Option 1: extract_core_pain (if pain changed)
    ├─ Option 2: stop_with_guidance (if no change needed)
    └─ Option 3: run_research (if unclear)
    ↓
IF extract_core_pain chosen:
    ├─ Chain runs with ALL signals (including new one)
    ├─ LLM sees existing core_pain as context
    ├─ Decides: keep existing OR update with new insight
    └─ Saves updated core_pain to foundation
    ↓
Foundation Updated ✓
```

**Key Insight:** Foundation extraction chains ALWAYS analyze ALL signals, not just the new one. This ensures the LLM can decide whether to update or preserve existing foundation elements.

---

### 3.4 Foundation Elements vs Business Drivers

**Foundation (7 Gates):**
- Stored in `project_foundation` table (JSONB columns)
- Represents THE consolidated strategic foundation
- One record per element type (THE core pain, THE primary persona, etc.)
- Extracted by DI Agent tools
- High-confidence, consultant-reviewed

**Business Drivers:**
- Stored in `business_drivers` table (multiple rows)
- Represents ALL pains, goals, KPIs extracted from signals
- Many records per project
- Extracted automatically from signals via fact extraction
- Lower-level granularity, may include duplicates/variations

**Flow:**
```
Signals
  ↓
Fact Extraction
  ↓
business_drivers table (pains, goals, KPIs)
  ↓
DI Agent Consolidation
  ↓
project_foundation.core_pain (THE singular pain)
```

---

### 3.5 Confirmation Workflow

**Foundation elements support confirmation:**

```python
{
  "statement": "Can't see which customers are about to churn",
  "trigger": "Lost 3 enterprise customers in Q4",
  "stakes": "$2M ARR at risk",
  "who_feels_it": "Customer Success Manager",
  "confidence": 0.85,
  "evidence": ["signal_123", "signal_456"],
  "confirmed_by": null  // ← Set by consultant/client
}
```

**Confirmation Flow:**
1. DI Agent extracts foundation element
2. Element shown to consultant in UI
3. Consultant reviews and confirms (sets `confirmed_by`)
4. Confirmed elements are protected from automatic updates
5. New signals may trigger proposals instead of direct updates

---

## 4. Signal Processing Architecture

### 4.1 Lightweight vs Heavyweight Paths

**Lightweight Path** (fast, incremental):
- Short signals (<1000 chars)
- Fact extraction only
- Updates business_drivers, competitor_refs
- No feature/persona generation

**Heavyweight Path** (comprehensive, slower):
- Long signals (>1000 chars)
- Full state builder graph
- Generates features, personas, VP steps, PRD sections
- Smart merge with confirmed entities

### 4.2 Signal → Entity Flow

```
Signal Added
    ↓
Signal Classification
    ├─ Lightweight: extract_facts → business_drivers, competitors
    └─ Heavyweight: build_state → features, personas, VP, PRD
    ↓
Similarity Matching
    ├─ Check for existing similar entities
    ├─ IF similar and confirmed → MERGE evidence
    └─ IF not similar → CREATE new entity
    ↓
Confirmation Status Derivation
    ├─ Signal authority = client → confirmed_client
    ├─ Signal authority = consultant → confirmed_consultant
    └─ Signal authority = research/ai → ai_generated
    ↓
Entity Created/Updated with Attribution
    ├─ evidence[] field links to signal_chunks
    └─ Change tracking records the modification
```

---

## 5. Backend Launch Commands

### 5.1 Standard Launch

```bash
# From repository root
uv run uvicorn app.main:app --reload --port 8000
```

### 5.2 Common Issues & Solutions

#### Issue: Similarity search library not loading

**Problem:** The `rapidfuzz` library (used for fuzzy matching) may have import issues.

**Solution:**
```bash
# Reinstall dependencies
uv pip install --force-reinstall rapidfuzz

# Or clear cache and reinstall all
uv cache clean
uv sync
```

#### Issue: Database connection errors

**Problem:** Supabase connection failing

**Solution:**
```bash
# Check .env file has correct Supabase credentials
cat .env | grep SUPABASE

# Should see:
# SUPABASE_URL=https://...
# SUPABASE_KEY=eyJ...
```

#### Issue: Vector search errors

**Problem:** pgvector extension not loaded

**Solution:**
```sql
-- Run in Supabase SQL editor
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5.3 Development Workflow

```bash
# Terminal 1 - Backend
cd /Users/matt/aios-req-engine
uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 - Frontend
cd /Users/matt/aios-req-engine/apps/workbench
npm run dev

# Terminal 3 - Tests (optional)
cd /Users/matt/aios-req-engine
uv run pytest tests/ -v
```

### 5.4 Environment Variables

**Required:**
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...
```

**Optional:**
```bash
PERPLEXITY_API_KEY=pplx-...  # For research agent
FIRECRAWL_API_KEY=fc-...     # For company enrichment
```

---

## 6. Key Architectural Patterns

### 6.1 Smart Merge Pattern

Used for features, personas, business drivers:

1. Load existing entities
2. Separate confirmed vs ai_generated
3. Delete only ai_generated entities
4. Check similarity of new entities to confirmed
5. IF similar → MERGE evidence
6. IF not similar → CREATE new entity

**Benefit:** Preserves human-confirmed data while allowing AI to add new insights.

### 6.2 Evidence Attribution

All entities link back to source signals:

```python
{
  "id": "feature_uuid",
  "name": "Churn prediction dashboard",
  "evidence": [
    {
      "chunk_id": "chunk_uuid",
      "signal_id": "signal_uuid",
      "quote": "We need to predict churn before it happens",
      "relevance": 0.95
    }
  ]
}
```

**Benefits:**
- Traceability: Every entity can be traced to source
- Confidence: Evidence count indicates strength
- Updates: New signals add evidence to existing entities

### 6.3 Confirmation Cascade

```
Entity extracted (ai_generated)
    ↓
Consultant reviews → confirmed_consultant
    ↓
Client reviews → confirmed_client
    ↓
Protected from bulk replace
    ↓
New signals merge evidence instead of replacing
```

### 6.4 Cache Invalidation

**Triggers:**
- Foundation element saved → invalidate state_snapshot, readiness_cache
- Feature updated → invalidate readiness_cache
- Persona updated → invalidate readiness_cache
- Business driver added → invalidate state_snapshot

**Cache TTLs:**
- State snapshot: 5 minutes
- Readiness cache: Updated on entity changes

---

## 7. Common Workflows

### 7.1 Initial Project Setup

```
1. Create project
2. Add initial signal (email, transcript)
3. Run /di command
4. DI Agent extracts foundation elements
5. Review & confirm core_pain, primary_persona
6. Add more signals
7. Run /analyze to build features, personas
```

### 7.2 Adding a New Feature Manually

```
POST /api/features
{
  "project_id": "uuid",
  "name": "Feature name",
  "category": "core",
  "is_mvp": true,
  "confirmation_status": "confirmed_consultant",
  "evidence": []
}
```

### 7.3 Enriching a Feature

```
1. Feature exists (confirmed or ai_generated)
2. Run /enrich-features command
3. Chain analyzes feature + project context
4. Extracts structured enrichment
5. Updates feature with overview, user_actions, etc.
```

### 7.4 Updating Foundation After Client Meeting

```
1. Add meeting transcript as signal
2. Run /di command
3. DI Agent analyzes new transcript
4. Decides: update core_pain or merge evidence
5. Extracts updated foundation elements
6. Consultant reviews & confirms changes
```

---

## 8. Database Schema Summary

### Core Tables

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `projects` | Project metadata | name, stage, portal_enabled |
| `signals` | Raw input (emails, transcripts) | content, signal_type, authority |
| `signal_chunks` | Vector-indexed chunks | content, embedding, signal_id |
| `features` | Product features | name, category, is_mvp, confirmation_status |
| `personas` | User personas | name, slug, is_primary, goals, pain_points |
| `project_foundation` | 7 strategic gates | core_pain, primary_persona, wow_moment, etc. |
| `business_drivers` | Pains, goals, KPIs | driver_type, description, priority |
| `competitor_refs` | Competitors & inspiration | reference_type, name, research_notes |
| `stakeholders` | Project stakeholders | name, role, stakeholder_type, influence |

### Supporting Tables

| Table | Purpose |
|-------|---------|
| `vp_steps` | Value path steps |
| `prd_sections` | PRD sections |
| `confirmation_items` | Pending confirmations |
| `proposals` | AI suggestions awaiting review |
| `cascade_events` | Entity change suggestions |
| `change_tracking` | Entity change history |

---

## 9. Troubleshooting Guide

### Issue: Features not appearing after signal added

**Check:**
1. Signal was heavyweight (>1000 chars)?
2. Build state graph completed successfully?
3. Features not filtered out by similarity matching?
4. Check logs for extraction errors

### Issue: Core pain extraction returns low confidence

**Causes:**
- Insufficient signal content
- Signals lack pain/problem statements
- Signals are mostly solution-focused

**Solutions:**
- Add more client-authored signals
- Add discovery call transcripts
- Run /research to gather context

### Issue: Duplicate features appearing

**Causes:**
- Similarity threshold too low
- Features described differently in signals
- Confirmation status preventing merge

**Solutions:**
- Check similarity matching logs
- Manually merge via UI
- Adjust similarity threshold in config

---

## 10. Performance Considerations

### Optimization Strategies

1. **State Snapshot Caching** - 5-minute TTL reduces DB calls
2. **Readiness Caching** - Computed once, cached until entity change
3. **Parallel Loading** - Load foundation elements concurrently
4. **Evidence Deduplication** - Prevent duplicate chunk references
5. **Lazy Loading** - Only load enrichment data when needed

### Bottlenecks

1. **Vector Search** - Large signal_chunks table can slow semantic search
2. **LLM Calls** - Foundation extraction requires multiple OpenAI calls
3. **Similarity Matching** - Checking all confirmed features for similarity
4. **Build State Graph** - Full rebuild can take 30-60 seconds

**Mitigation:**
- Use Haiku for simple extractions
- Batch LLM calls where possible
- Cache similarity results
- Run heavyweight builds asynchronously

---

## Conclusion

The AIOS Req Engine uses a sophisticated multi-layer architecture:

1. **Signals** - Raw input from various sources
2. **Extraction** - Facts, features, personas, foundation elements
3. **Consolidation** - Similarity matching, merging, deduplication
4. **Confirmation** - Human review and approval
5. **Enrichment** - Deep analysis and structured data
6. **Attribution** - Evidence trails back to source signals

**Key Strengths:**
- ✅ Smart merge preserves confirmed data
- ✅ Evidence attribution enables traceability
- ✅ Multi-strategy similarity prevents duplicates
- ✅ Confirmation workflow protects human input
- ✅ DI Agent orchestrates complex workflows

**Recommended Reading Order:**
1. This document (system flows)
2. `docs/STATE_SNAPSHOT_ANALYSIS.md` (DI Agent context)
3. `docs/PERFORMANCE_OPTIMIZATION.md` (caching strategies)
4. `CLAUDE.md` (development patterns)

---

**Last Updated:** 2026-01-25
**Maintainer:** Development Team
