# Signal Processing Flow Diagrams

## Current Flow (AS-IS) - Has Redundancy

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER UPLOADS SIGNAL                           │
│              (Transcript, Document, Note, Email)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   POST /v1/ingest        │
              │   (phase0.py)            │
              └──────────┬───────────────┘
                         │
                         ├─ Store raw signal
                         ├─ Chunk into smaller pieces
                         ├─ Generate embeddings
                         └─ Store chunks in DB
                         │
                         ▼
              ┌──────────────────────────┐
              │ _auto_trigger_processing │
              │ (JUST FIXED!)            │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   process_signal()       │
              │   (signal_pipeline.py)   │
              └──────────┬───────────────┘
                         │
                ┌────────┴────────┐
                │                 │
         LIGHTWEIGHT          HEAVYWEIGHT
         (notes, quick)      (transcripts, docs)
                │                 │
                ▼                 ▼
    ┌───────────────────┐  ┌────────────────────┐
    │ build_state_graph │  │ bulk_signal_graph  │
    └────────┬──────────┘  └─────────┬──────────┘
             │                        │
             ▼                        ▼
    ┌─────────────────┐     ┌──────────────────┐
    │ extract_facts   │     │ extract_facts    │
    │ from chunks     │     │ (parallel)       │
    └────────┬────────┘     └─────────┬────────┘
             │                         │
             ▼                         ▼
    ┌────────────────────┐   ┌─────────────────┐
    │ CREATE/UPDATE:     │   │ CREATE PROPOSAL │
    │ - Features         │   │ with:           │
    │ - Personas         │   │ - Features      │
    │ - VP Steps         │   │ - Personas      │
    │ - PRD Sections     │   │ - VP Steps      │
    │                    │   │ - PRD           │
    │ (Auto-applied)     │   │ (Needs review)  │
    └────────────────────┘   └─────────────────┘


┌──────────────────────────────────────────────────────────────────┐
│              SEPARATE STRATEGIC FOUNDATION PATH                   │
│                    (REDUNDANT - TO MERGE)                         │
└────────────────────────────┬─────────────────────────────────────┘
                             │
                             ▼
            ┌────────────────────────────────┐
            │ POST /v1/agents/strategic-     │
            │      foundation                │
            │ (MANUAL TRIGGER ONLY)          │
            └────────────┬───────────────────┘
                         │
                         ▼
            ┌────────────────────────────────┐
            │ run_strategic_foundation()     │
            │ (run_strategic_foundation.py)  │
            └────────────┬───────────────────┘
                         │
                         ├─ Enrich company info
                         ├─ Link stakeholders
                         └─ Extract strategic entities
                         │
                         ▼
            ┌────────────────────────────────┐
            │ extract_strategic_entities     │
            │ _from_signals()                │
            │ (SEPARATE extraction logic!)   │
            └────────────┬───────────────────┘
                         │
                         ▼
            ┌────────────────────────────────┐
            │ CREATE/UPDATE:                 │
            │ - Business Drivers             │
            │   (KPIs, Pains, Goals)         │
            │ - Competitors                  │
            │ - Stakeholders                 │
            │ - Risks                        │
            └────────────────────────────────┘
```

## Proposed Unified Flow (TO-BE) - Clean & Efficient

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER UPLOADS SIGNAL                           │
│              (Transcript, Document, Note, Email)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │   POST /v1/ingest        │
              │   (phase0.py)            │
              └──────────┬───────────────┘
                         │
                         ├─ Store raw signal
                         ├─ Chunk into smaller pieces
                         ├─ Generate embeddings
                         └─ Store chunks in DB
                         │
                         ▼
              ┌──────────────────────────┐
              │ _auto_trigger_processing │
              └──────────┬───────────────┘
                         │
                         ▼
              ┌──────────────────────────┐
              │   process_signal()       │
              │   (signal_pipeline.py)   │
              └──────────┬───────────────┘
                         │
                ┌────────┴────────┐
                │                 │
         LIGHTWEIGHT          HEAVYWEIGHT
         (notes, quick)      (transcripts, docs)
                │                 │
                ▼                 ▼
    ┌───────────────────┐  ┌────────────────────┐
    │ build_state_graph │  │ bulk_signal_graph  │
    └────────┬──────────┘  └─────────┬──────────┘
             │                        │
             ▼                        ▼
    ┌──────────────────────────────────────────┐
    │   extract_facts (UNIFIED - ONE CALL)     │
    │   Extracts ALL entity types:             │
    │   ✓ Features                             │
    │   ✓ Personas                             │
    │   ✓ VP Steps                             │
    │   ✓ PRD Sections                         │
    │   ✓ Business Drivers (KPIs/Pains/Goals)  │
    │   ✓ Competitors                          │
    │   ✓ Stakeholders                         │
    │   ✓ Risks                                │
    └────────┬─────────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────────────┐
    │   Smart Upsert for Each Entity Type      │
    │   (Similarity matching + merge logic)    │
    │                                           │
    │   For each extracted entity:             │
    │   1. Check if similar entity exists      │
    │   2. If exists + confirmed → Merge       │
    │   3. If exists + AI-generated → Update   │
    │   4. If new → Create                     │
    └────────┬─────────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────────────┐
    │      ALL ENTITIES UPDATED IN ONE PASS    │
    │                                           │
    │   Result counts:                         │
    │   - features_created/updated             │
    │   - personas_created/updated             │
    │   - business_drivers_created/merged      │
    │   - competitors_created/merged           │
    │   - stakeholders_created/merged          │
    │   - risks_created/merged                 │
    └────────┬─────────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────────────┐
    │   Trigger Background DI Agent (NEW)      │
    │   - Analyze for gaps                     │
    │   - Check for contradictions             │
    │   - Suggest improvements                 │
    │   - Auto-enrich key entities             │
    └──────────────────────────────────────────┘
```

## DI Agent Flow (Current vs Proposed)

### Current (On-Demand Only):
```
User clicks "Run DI Agent"
  ↓
POST /v1/di-agent/run
  ↓
DI Agent analyzes project
  ↓
Uses tools:
  - extract_business_drivers (REDUNDANT with signal processing!)
  - enrich_competitor
  - run_research
  - etc.
  ↓
Returns recommendations
  ↓
User must manually act on them
```

### Proposed (Background + Proactive):
```
Signal Processing Completes
  ↓
Trigger Background DI Agent
  ↓
Analyze:
  ├─ Features: Are they well-defined?
  ├─ Personas: Are pain points clear?
  ├─ Business Drivers: Are KPIs measurable?
  ├─ Competitors: Do we understand differentiation?
  ├─ Risks: Are mitigations defined?
  └─ Gates: What's blocking readiness?
  ↓
Auto-enrich entities needing detail
  ├─ enrich_kpi() for undefined KPIs
  ├─ enrich_competitor() for competitors without differentiators
  └─ enrich_stakeholder() for key decision makers
  ↓
Generate recommendations
  ├─ "Missing: Clear value prop for Finance persona"
  ├─ "Gap: No KPIs defined for customer retention"
  └─ "Risk: Critical stakeholder not engaged"
  ↓
Store recommendations in activity feed
  ↓
Notify user in UI (toast/badge)
```

## Entity Similarity Matching Flow

```
New Entity Extracted
  ↓
Generate matching key
  ├─ Features: normalized title
  ├─ Personas: normalized name
  ├─ Business Drivers: normalized description
  ├─ Competitors: normalized name
  └─ Stakeholders: normalized name
  ↓
Search existing entities
  ↓
Run 6-strategy cascade:
  1. Exact match
  2. Normalized match
  3. Token set match
  4. Partial match
  5. Key terms match
  6. Semantic similarity (embedding)
  ↓
Found match?
  ├─ YES → Check confirmation_status
  │         ├─ confirmed_client/consultant
  │         │   → MERGE evidence only
  │         ├─ ai_generated
  │         │   → UPDATE all fields
  │         └─ needs_confirmation
  │             → UPDATE all fields
  │
  └─ NO → CREATE new entity
```

## Research Agent Flow (External Knowledge)

```
DI Agent detects knowledge gap
  ↓
"We don't know competitor pricing"
  ↓
Call research_agent with query
  ↓
research_agent_graph runs
  ├─ Query Perplexity API
  ├─ Get structured results
  └─ Store as research signal
  ↓
New research signal triggers processing
  ↓
extract_facts extracts:
  ├─ Competitor pricing model
  ├─ Market positioning
  └─ Feature comparisons
  ↓
Smart upsert merges into existing competitors
  ↓
DI Agent re-analyzes
  ↓
Gap filled ✓
```

## Strategic Foundation vs Main Entities

**Main Entities (Core Product Definition):**
- Features - What to build
- Personas - Who it's for
- VP Steps - How to demo it
- PRD Sections - Detailed specs

**Strategic Foundation (Business Context):**
- Business Drivers - Why build it (KPIs/Pains/Goals)
- Competitors - Who we're competing with
- Stakeholders - Who decides and influences
- Risks - What could go wrong

**Both extracted together in unified flow!**

```
extract_facts() extracts EVERYTHING:
  ├─ facts[] - Features, Personas, VP, PRD
  └─ strategic_entities
      ├─ business_drivers[]
      ├─ competitors[]
      ├─ stakeholders[]
      └─ risks[]

All processed in one pass
All use smart_upsert
All have source attribution
All tracked with evidence
```
