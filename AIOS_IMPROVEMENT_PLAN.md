# AIOS System Improvement Plan

## Overview

Transform AIOS into a cleaner, more efficient system by:
1. **Adding** persona enrichment (missing capability)
2. **Replacing** stored PRD sections with on-demand report generation
3. **Removing** redundant PRD infrastructure (~85 files, ~15,000+ lines)

## Design Principles

- **Single Source of Truth**: Each piece of information lives in ONE place
- **Canonical Entities**: Features, Personas, VP Steps, Strategic Foundation (Business Drivers)
- **Generated Artifacts**: PRD becomes a compiled report, not stored data
- **No Data Loss**: Migrate any unique PRD content before removal

---

## Architecture: Before & After

### BEFORE (Current)
```
Signals
  └─→ Extract Facts
        ├─→ PRD Sections (stored, enriched separately) ❌ REDUNDANT
        ├─→ Features (stored, enriched)
        ├─→ Personas (stored, NOT enriched) ❌ GAP
        ├─→ VP Steps (stored, enriched)
        └─→ Strategic Foundation (goals, KPIs, pain points)
```

### AFTER (Target)
```
Signals
  └─→ Extract Facts
        ├─→ Features (stored, enriched) ✅
        ├─→ Personas (stored, enriched) ✅ NEW
        ├─→ VP Steps (stored, enriched) ✅
        └─→ Strategic Foundation (goals, KPIs, pain points) ✅

Reports (Generated On-Demand, Not Stored)
  └─→ PRD Report = compile(Features + Personas + VP + Strategic)
  └─→ Executive Summary = summarize(PRD Report)
```

---

## Phase 1: Persona Enrichment (ADDITIVE - Safe)

**Goal**: Fill the missing persona enrichment capability

### Tasks

#### 1.1 Create Persona Enrichment Schemas
- **File**: `app/core/schemas_persona_enrich.py`
- **Create**:
  - `EnrichPersonasRequest` (project_id, persona_ids?, include_research?, top_k_context?)
  - `EnrichPersonasResponse` (run_id, job_id, personas_processed, personas_updated, summary)
  - `EnrichPersonaOutput` (persona_id, enhanced fields, evidence)

#### 1.2 Create Persona Enrichment Input Builder
- **File**: `app/core/persona_enrich_inputs.py`
- **Functions**:
  - `get_persona_enrich_context()` - Gather all context including state_snapshot
  - `build_persona_enrich_prompt()` - Construct LLM prompt
  - `retrieve_supporting_chunks()` - Vector search for persona-relevant context
- **Include**: State snapshot, features (for workflow context), business drivers

#### 1.3 Update Persona Enrichment Chain
- **File**: `app/chains/enrich_personas_v2.py` (exists, needs update)
- **Changes**:
  - Accept context from input builder
  - Include state_snapshot in prompt
  - Match pattern of enrich_features.py

#### 1.4 Create Persona Enrichment Graph
- **File**: `app/graphs/enrich_personas_graph.py`
- **Create**:
  - `EnrichPersonasState` dataclass
  - Nodes: load_context, process_persona (loop), persist_results
  - `run_enrich_personas_agent()` entry point
- **Pattern**: Follow enrich_features_graph.py exactly

#### 1.5 Create Persona Enrichment API Endpoint
- **File**: `app/api/enrich_personas.py`
- **Endpoint**: `POST /agents/enrich-personas`
- **Features**:
  - Job lifecycle (create, start, complete, fail)
  - Error handling and logging
  - Background task support

#### 1.6 Register Endpoint and Wire Frontend
- **Files**:
  - `app/api/__init__.py` - Register router
  - `apps/workbench/lib/api.ts` - Add `enrichPersonas()` function
  - `apps/workbench/lib/assistant/commands.ts` - Wire `/enrich-personas` command

#### 1.7 Test Persona Enrichment
- Verify endpoint works
- Check enrichment output quality
- Confirm job tracking works

---

## Phase 2: PRD Report Generator (ADDITIVE - Safe)

**Goal**: Create replacement before removing anything

### Tasks

#### 2.1 Design PRD Report Schema
- **File**: `app/core/schemas_prd_report.py`
- **Create**:
  - `PRDReportSection` - Section with title, content, sources
  - `PRDReport` - Full report structure
  - `GeneratePRDReportRequest` (project_id, format?, include_evidence?)
  - `GeneratePRDReportResponse` (report, generated_at)

#### 2.2 Create PRD Report Compiler
- **File**: `app/core/prd_report_compiler.py`
- **Functions**:
  - `compile_prd_report()` - Main compiler
  - `_build_executive_summary()` - From strategic foundation
  - `_build_problem_section()` - From pain points
  - `_build_solution_section()` - From features
  - `_build_users_section()` - From personas
  - `_build_journey_section()` - From VP steps
  - `_build_success_metrics()` - From KPIs
- **Output**: Structured PRD that can be rendered as markdown/HTML/PDF

#### 2.3 Create PRD Report API Endpoint
- **File**: `app/api/prd_report.py`
- **Endpoints**:
  - `POST /reports/prd` - Generate PRD report
  - `GET /reports/prd/preview` - Quick preview (cached)
- **Features**:
  - Multiple format support (markdown, JSON, HTML)
  - Optional evidence/attribution inclusion
  - Caching for performance

#### 2.4 Test PRD Report Generator
- Compare output to existing PRD sections
- Verify all information is captured
- Check formatting and structure

---

## Phase 3: PRD Audit & Migration (ANALYSIS - Safe)

**Goal**: Ensure no data loss before removal

### Tasks

#### 3.1 Audit Existing PRD Data
- **Script**: `scripts/audit_prd_data.py`
- **Checks**:
  - Which projects have PRD sections?
  - Do any PRD sections have unique content not in features/personas/VP?
  - What fields are populated?
  - Is there enrichment data that needs preserving?

#### 3.2 Create PRD Migration (If Needed)
- **File**: `migrations/XXXX_migrate_prd_to_entities.sql`
- **Actions**:
  - Extract any unique PRD content
  - Map to appropriate entities (features, personas, notes)
  - Preserve attribution/evidence

#### 3.3 Document PRD File Inventory
- **List all 85+ files** that reference PRD
- **Categorize**:
  - Core PRD files (delete entirely)
  - Files with PRD references (edit to remove references)
  - Shared utilities (may need PRD type removed from enums)

---

## Phase 4: Remove PRD Backend (DESTRUCTIVE - Careful)

**Goal**: Systematically remove PRD infrastructure

### Tasks

#### 4.1 Remove PRD Enrichment Pipeline
- **Delete Files**:
  - `app/chains/enrich_prd.py`
  - `app/core/prd_enrich_inputs.py`
  - `app/graphs/enrich_prd_graph.py`
  - `app/core/schemas_prd_enrich.py`

#### 4.2 Remove PRD API Endpoints
- **Delete Files**:
  - `app/api/enrich_prd.py`
  - `app/api/prd_summary.py`
- **Edit Files**:
  - `app/api/state.py` - Remove PRD endpoints (`/state/prd`, `/state/prd/{id}/status`)
  - `app/api/__init__.py` - Remove PRD router registrations

#### 4.3 Remove PRD Database Layer
- **Delete Files**:
  - `app/db/prd.py`
- **Edit Files**:
  - Any file importing from `app.db.prd`

#### 4.4 Remove PRD from State Building
- **Edit Files**:
  - `app/chains/build_state.py` - Remove PRD section generation
  - `app/graphs/build_state_graph.py` - Remove PRD persistence
  - `app/core/schemas_state.py` - Remove `PrdSectionOut`, PRD from responses

#### 4.5 Remove PRD from Chat/Context Systems
- **Edit Files**:
  - `app/chains/chat_context.py` - Remove PRD from context building
  - `app/chains/chat_tools.py` - Remove "prd_section" entity type
  - `app/core/state_snapshot.py` - Remove any PRD references (if any)

#### 4.6 Remove PRD from Proposal/Cascade Systems
- **Edit Files**:
  - `app/chains/proposal_generator.py` - Remove PRD entity type
  - `app/chains/cascade_handler.py` - Remove PRD handling
  - `app/chains/confirmation_resolver.py` - Remove PRD updates
  - `app/chains/auto_apply_engine.py` - Remove PRD mapping

#### 4.7 Remove PRD Schemas and Types
- **Delete Files**:
  - `app/core/schemas_prd_enrich.py` (if not already)
- **Edit Files**:
  - `app/core/schemas_evidence.py` - Remove PRD_SECTION from entity types
  - `app/core/schemas_confirmations.py` - Remove PRD confirmation kind
  - `app/core/schemas_reconcile.py` - Remove PRDSectionPatch

#### 4.8 Remove PRD Summary Chain
- **Delete Files**:
  - `app/chains/generate_prd_summary.py`
  - `app/graphs/generate_prd_summary_graph.py`

---

## Phase 5: Remove PRD Frontend (DESTRUCTIVE - Careful)

### Tasks

#### 5.1 Remove PRD API Calls
- **Edit Files**:
  - `apps/workbench/lib/api.ts` - Remove PRD-related functions

#### 5.2 Remove PRD Types
- **Edit Files**:
  - `apps/workbench/types/*.ts` - Remove PRD interfaces

#### 5.3 Remove PRD UI Components (If Any)
- Search for PRD-related components
- Remove or replace with report generator UI

#### 5.4 Update Assistant Commands
- **Edit Files**:
  - `apps/workbench/lib/assistant/commands.ts` - Remove PRD commands
  - Replace with `/generate-prd-report` command

---

## Phase 6: Database Cleanup (DESTRUCTIVE - Careful)

### Tasks

#### 6.1 Create Migration to Drop PRD Table
- **File**: `migrations/XXXX_drop_prd_sections.sql`
- **Actions**:
  ```sql
  -- Backup first (optional, for safety)
  CREATE TABLE prd_sections_backup AS SELECT * FROM prd_sections;

  -- Drop the table
  DROP TABLE IF EXISTS prd_sections;

  -- Clean up any foreign key references
  -- Clean up confirmation_items where entity_type = 'prd_section'
  DELETE FROM confirmation_items WHERE entity_type = 'prd_section';
  ```

#### 6.2 Clean Up Related Tables
- Remove PRD-related entries from:
  - `confirmation_items` (entity_type = 'prd_section')
  - `revisions` (entity_type = 'prd_section')
  - `batch_proposals` (proposal_type containing 'prd')
  - Any other tables with entity_type references

---

## Phase 7: Verification & Cleanup (SAFE)

### Tasks

#### 7.1 Run Full Test Suite
- `uv run pytest tests/ -v`
- Fix any failures

#### 7.2 Verify Enrichment Pipelines
- Test feature enrichment
- Test persona enrichment (new)
- Test VP enrichment
- Test business driver enrichment

#### 7.3 Verify PRD Report Generation
- Generate PRD report
- Compare to old PRD sections (if backed up)
- Verify completeness

#### 7.4 Dead Code Cleanup
- Run linter: `uv run ruff check . --fix`
- Remove unused imports
- Remove empty files

#### 7.5 Update Documentation
- Update CLAUDE.md with new architecture
- Remove PRD references from docs
- Document new PRD report endpoint

---

## Risk Mitigation

### Before Starting
- [ ] Create database backup
- [ ] Create git branch for this work
- [ ] Document current PRD section counts per project

### During Removal
- [ ] Remove in small commits
- [ ] Test after each phase
- [ ] Keep backup of deleted files until verified

### Rollback Plan
- Git revert to pre-removal commit
- Restore database from backup
- Re-deploy previous version

---

## Success Criteria

1. **Persona enrichment works** - `/agents/enrich-personas` endpoint functional
2. **PRD report generates** - `/reports/prd` produces complete document
3. **No PRD table** - `prd_sections` table dropped
4. **No PRD code** - All 85+ files cleaned up
5. **All tests pass** - No regressions
6. **Enrichment faster** - One less entity type to process
7. **Cleaner codebase** - ~15,000+ lines removed

---

## Estimated Effort

| Phase | Tasks | Risk | Effort |
|-------|-------|------|--------|
| Phase 1: Persona Enrichment | 7 | Low | Medium |
| Phase 2: PRD Report Generator | 4 | Low | Medium |
| Phase 3: PRD Audit | 3 | Low | Small |
| Phase 4: Remove PRD Backend | 8 | Medium | Large |
| Phase 5: Remove PRD Frontend | 4 | Medium | Medium |
| Phase 6: Database Cleanup | 2 | High | Small |
| Phase 7: Verification | 5 | Low | Medium |

**Total**: 33 tasks across 7 phases

---

## Order of Operations

```
Phase 1 (Persona) ──→ Phase 2 (Report Gen) ──→ Phase 3 (Audit)
                                                    │
                                                    ▼
Phase 7 (Verify) ←── Phase 6 (DB) ←── Phase 5 (FE) ←── Phase 4 (BE)
```

**Key Rule**: Complete Phase 2 (Report Generator) BEFORE Phase 4 (Remove PRD Backend)
