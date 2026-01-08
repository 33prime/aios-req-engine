# Signal Processing Pipeline - Implementation Plan

## Overview

A sophisticated signal processing system that differentiates between lightweight signals (chat, short emails) and heavyweight signals (transcripts, documents, long emails). Heavyweight signals trigger a bulk processing pipeline that extracts entities holistically, validates against existing state, and presents consolidated updates for approval.

## Core Concepts

### Signal Power Classification

| Source Type | Default Mode | Override Condition |
|-------------|--------------|-------------------|
| Transcript | heavyweight | - |
| Document/PDF | heavyweight | - |
| Email >500 words | heavyweight | - |
| Email <500 words | lightweight | entity_count > 5 → heavyweight |
| Chat message | lightweight | - |

### Confirmation Semantics

- **Direct participant** (on email, speaker in transcript) → `confirmed` status
- **Mentioned indirectly** ("Jim said...") → `draft` status
- Client voice in transcript = auto-confirmation for entities discussed
- New data supersedes old, even if previously confirmed (with changelog)
- Edge case: highly illogical contradiction → flag as `client_correction_needed`

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    SIGNAL INGESTION                         │
│  Classify: source_type, length, entity_density → power_score│
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
         lightweight                     heavyweight
         (existing flow)                      │
                              ┌───────────────┴───────────────┐
                              │   PARALLEL EXTRACTION AGENTS  │
                              ├───────────────────────────────┤
                              │ 1. Entity Agent               │
                              │ 2. Stakeholder Agent          │
                              │ 3. Creative Brief Agent       │
                              │ 4. Fact Agent (existing)      │
                              └───────────────────────────────┘
                                            │
                              ┌─────────────┴─────────────────┐
                              │   CONSOLIDATION ENGINE        │
                              │ • Similarity matching         │
                              │ • Dedupe mentions             │
                              │ • Group related changes       │
                              └───────────────────────────────┘
                                            │
                              ┌─────────────┴─────────────────┐
                              │   RESEARCH VALIDATION         │
                              │ • Sanity check                │
                              │ • Contradiction detection     │
                              │ • Gap analysis                │
                              └───────────────────────────────┘
                                            │
                              ┌─────────────┴─────────────────┐
                              │   BULK UPDATE PROPOSAL        │
                              │ Consolidated preview + apply  │
                              └───────────────────────────────┘
```

---

## Phase 1: Stakeholder System

### 1.1 Database Schema

```sql
-- Migration: 0038_stakeholders.sql

CREATE TABLE stakeholders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Identity
    name TEXT NOT NULL,
    role TEXT,                          -- "CFO", "Product Manager", "CTO"
    email TEXT,
    phone TEXT,

    -- Expertise & Matching
    domain_expertise TEXT[] DEFAULT '{}',  -- ["finance", "security", "ux"]
    topic_mentions JSONB DEFAULT '{}',     -- {"sso": 3, "budget": 5}

    -- Status
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'confirmed')),
    source_type TEXT CHECK (source_type IN ('direct_participant', 'mentioned')),
    is_primary_contact BOOLEAN DEFAULT false,

    -- Provenance
    extracted_from_signal_id UUID REFERENCES signals(id),
    mentioned_in_signals UUID[] DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stakeholders_project ON stakeholders(project_id);
CREATE INDEX idx_stakeholders_domain ON stakeholders USING GIN(domain_expertise);

-- Ensure only one primary contact per project (or allow multiple, just track it)
-- No unique constraint - multiple primaries allowed, UI shows all
```

### 1.2 Stakeholder Extraction Agent

**File:** `app/chains/extract_stakeholders.py`

```python
SYSTEM_PROMPT = """Extract stakeholders mentioned in this content.

For each person identified, extract:
- name: Full name if available
- role: Job title or function
- domain_expertise: Areas they likely know about based on context
- source_type: 'direct_participant' if they wrote/spoke this, 'mentioned' if referenced
- email: If visible in content

Output JSON array of stakeholders.
"""
```

**Extraction Logic:**
1. Parse signal for names + roles
2. Determine if direct participant (email sender, transcript speaker) or mentioned
3. Infer domain expertise from context
4. Check similarity against existing stakeholders (avoid duplicates)
5. Return new + updated stakeholders

### 1.3 API Endpoints

```
POST   /v1/projects/{id}/stakeholders          # Create
GET    /v1/projects/{id}/stakeholders          # List
GET    /v1/projects/{id}/stakeholders/{id}     # Get
PATCH  /v1/projects/{id}/stakeholders/{id}     # Update
DELETE /v1/projects/{id}/stakeholders/{id}     # Delete
POST   /v1/projects/{id}/stakeholders/{id}/set-primary
```

### 1.4 Frontend Components

- `StakeholderCard.tsx` - Display stakeholder with role, domains
- `StakeholderList.tsx` - List view with primary contact badge
- `StakeholderModal.tsx` - Create/edit stakeholder
- Add stakeholder tab or section to project view

---

## Phase 2: Signal Power Classification

### 2.1 Signal Classifier

**File:** `app/core/signal_classifier.py`

```python
@dataclass
class SignalClassification:
    power_level: Literal["lightweight", "heavyweight"]
    power_score: float  # 0.0 - 1.0
    reason: str
    estimated_entity_count: int
    recommended_pipeline: str

def classify_signal(
    source_type: str,
    content: str,
    metadata: dict
) -> SignalClassification:
    """
    Classify signal for processing pipeline routing.

    Factors:
    - source_type weight (transcript=1.0, doc=0.9, email=0.5, chat=0.2)
    - content length (normalized)
    - entity density (quick NER scan)
    """
```

### 2.2 Entity Density Scanner

Quick pre-scan to estimate entity count without full extraction:
- Regex patterns for feature-like phrases
- Name detection for stakeholders
- Step/flow language for VP

### 2.3 Integration Point

Modify `POST /v1/projects/{id}/signals` to:
1. Classify incoming signal
2. Route to appropriate pipeline
3. Return classification in response for UI feedback

---

## Phase 3: Bulk Pipeline Orchestrator

### 3.1 Pipeline Coordinator

**File:** `app/graphs/bulk_signal_graph.py`

LangGraph workflow:
```
START
  │
  ├─→ extract_entities (parallel)
  ├─→ extract_stakeholders (parallel)
  ├─→ extract_creative_brief (parallel)
  ├─→ extract_facts (parallel, existing)
  │
  ▼
CONSOLIDATE
  │
  ├─→ match_to_existing_entities
  ├─→ dedupe_mentions
  ├─→ group_related_changes
  │
  ▼
VALIDATE
  │
  ├─→ research_sanity_check
  ├─→ detect_contradictions
  ├─→ gap_analysis
  │
  ▼
PROPOSE
  │
  └─→ generate_bulk_proposal
      (consolidated view of all changes)
```

### 3.2 Consolidation Engine

**File:** `app/chains/consolidate_extractions.py`

```python
def consolidate_extractions(
    entities: list[ExtractedEntity],
    existing_features: list[Feature],
    existing_personas: list[Persona],
    existing_vp_steps: list[VpStep],
) -> ConsolidatedChanges:
    """
    1. For each extracted entity, find best match in existing
    2. If similarity > 0.85, treat as UPDATE
    3. If similarity < 0.85, treat as CREATE
    4. Merge multiple mentions of same entity
    5. Detect field-level changes
    """
```

### 3.3 Research Validation

**File:** `app/chains/validate_bulk_changes.py`

```python
def validate_bulk_changes(
    proposed_changes: ConsolidatedChanges,
    project_state: ProjectState,
    research_chunks: list[Chunk],
) -> ValidationResult:
    """
    1. Check each proposed change against existing confirmed state
    2. Flag logical contradictions (e.g., "no mobile app" when MVP has mobile features)
    3. Identify gaps this signal fills
    4. Score confidence for each change
    """
```

### 3.4 Bulk Proposal Schema

```python
class BulkProposal(BaseModel):
    id: UUID
    project_id: UUID
    source_signal_id: UUID

    # Summary
    title: str  # "Updates from 50-min Discovery Call"
    summary: str

    # Grouped changes
    features: list[FeatureChange]      # new, updated
    personas: list[PersonaChange]
    vp_steps: list[VpStepChange]
    stakeholders: list[StakeholderChange]
    creative_brief_updates: dict

    # Metadata
    total_changes: int
    contradictions: list[Contradiction]
    confidence_score: float

    # Status
    status: Literal["pending", "applied", "rejected"]
```

---

## Phase 4: Creative Brief Intent Agent

### 4.1 Agent Design

**File:** `app/chains/extract_creative_brief.py`

Runs on every signal, looks for answers to creative brief gaps:

```python
CREATIVE_BRIEF_FIELDS = [
    "client_name",
    "industry",
    "website",
    "competitors",
    "target_users",
    "success_metrics",
    "constraints",
    "budget_timeline",
    "technical_requirements"
]

def extract_creative_brief_data(
    content: str,
    current_brief: dict,
) -> dict[str, Any]:
    """
    Extract any creative brief fields mentioned in content.
    Only return fields that are currently empty or have new info.
    """
```

### 4.2 Auto-Fill Logic

- If field is empty → fill it
- If field has value but signal has more detail → append/enrich
- Track which signal provided which field (provenance)

---

## Phase 5: "Who Would Know" Feature

### 5.1 Confirmation Enhancement

When any entity has `status = 'needs_client_confirmation'`:

```python
def suggest_stakeholder_for_confirmation(
    entity: Feature | Persona | VpStep,
    stakeholders: list[Stakeholder],
    topic_keywords: list[str],
) -> list[StakeholderSuggestion]:
    """
    Match entity topic to stakeholder expertise.

    Returns ranked list:
    1. Domain expertise match
    2. Topic mention frequency
    3. Role relevance
    """
```

### 5.2 UI Component

```typescript
// ConfirmationSuggestion.tsx
interface Props {
  entity: Entity
  gap: string  // "Unclear if SAML or OAuth required"
}

// Displays:
// 💡 Jim (IT Security) or Sarah (CTO) would likely know
//    - Jim mentioned SSO 3 times in Call #3
//    [Ask Jim] [Ask Sarah] [Mark Resolved]
```

### 5.3 Stakeholder Topic Tracking

Update `topic_mentions` whenever stakeholder discusses something:

```python
def update_stakeholder_topics(
    stakeholder_id: UUID,
    signal_content: str,
    extracted_topics: list[str],
):
    """
    Increment topic counts for stakeholder.
    e.g., {"sso": 3, "compliance": 2, "budget": 5}
    """
```

---

## Phase 6: Frontend Integration

### 6.1 Signal Upload Enhancement

When uploading transcript/document:
1. Show "Analyzing..." with progress
2. Display classification result ("Heavyweight signal detected - 12 entities found")
3. Show bulk proposal preview
4. [Apply All] [Review Each] [Cancel]

### 6.2 Bulk Proposal Review UI

```
┌────────────────────────────────────────────────────┐
│ Updates from "Discovery Call - Jan 7"              │
│ 50 minutes • 12 changes detected                   │
├────────────────────────────────────────────────────┤
│                                                    │
│ Features (4)                              [Review] │
│  ✓ Voice Dictation (new)                          │
│  ✓ SSO Integration (updated: added SAML req)      │
│  ✓ Dashboard Analytics (enriched)                 │
│  ⚠ Offline Mode (conflicts with existing)         │
│                                                    │
│ Personas (1)                              [Review] │
│  ✓ Sales Manager - enriched goals                 │
│                                                    │
│ Value Path (2)                            [Review] │
│  ✓ Step 3: Added voice input flow                 │
│  ✓ Step 5: Updated success metrics                │
│                                                    │
│ Stakeholders (3)                          [Review] │
│  + Jim Martinez (CFO) - direct participant        │
│  + Sarah Chen (CTO) - direct participant          │
│  + Mike (Dev Lead) - mentioned                    │
│                                                    │
│ Creative Brief                            [Review] │
│  + Industry: Healthcare SaaS                      │
│  + Competitor: CompetitorX                        │
│                                                    │
├────────────────────────────────────────────────────┤
│ ⚠ 1 potential conflict detected          [Review] │
├────────────────────────────────────────────────────┤
│        [Cancel]              [Apply All Changes]  │
└────────────────────────────────────────────────────┘
```

### 6.3 Stakeholder Management Tab

New tab in project view:
- List of stakeholders with roles
- Primary contact badge
- Domain expertise tags
- "Last mentioned in" signal reference
- Click to see what topics they've discussed

---

## Implementation Order

### Sprint 1: Foundation
- [ ] Migration 0038: stakeholders table
- [ ] `app/db/stakeholders.py` - CRUD operations
- [ ] `app/api/stakeholders.py` - REST endpoints
- [ ] Basic stakeholder extraction agent
- [ ] Frontend: StakeholderList, StakeholderCard

### Sprint 2: Signal Classification
- [ ] `app/core/signal_classifier.py`
- [ ] Entity density scanner
- [ ] Modify signal ingestion to classify
- [ ] Add `power_level` to signal metadata
- [ ] Frontend: Show classification on upload

### Sprint 3: Bulk Pipeline Core
- [ ] `app/graphs/bulk_signal_graph.py` - orchestrator
- [ ] `app/chains/consolidate_extractions.py`
- [ ] `app/chains/validate_bulk_changes.py`
- [ ] Bulk proposal schema + storage
- [ ] Integration with signal ingestion

### Sprint 4: Creative Brief Agent
- [ ] `app/chains/extract_creative_brief.py`
- [ ] Auto-fill logic with provenance
- [ ] UI updates to show auto-filled fields

### Sprint 5: Who Would Know
- [ ] Stakeholder-to-topic matching
- [ ] `suggest_stakeholder_for_confirmation()`
- [ ] Frontend: ConfirmationSuggestion component
- [ ] Topic mention tracking

### Sprint 6: Polish & Integration
- [ ] Bulk proposal review UI
- [ ] Conflict resolution workflow
- [ ] End-to-end testing with real transcripts
- [ ] Performance optimization

---

## Success Metrics

1. **Extraction Accuracy**: >90% of entities in transcript are captured
2. **Consolidation Quality**: <5% duplicate entities created
3. **Time Savings**: Bulk apply reduces manual work by 80%
4. **Stakeholder Utility**: "Who would know" suggestions are relevant >70% of time

---

## Design Decisions

1. **No expiration** - Bulk proposals persist until explicitly applied or rejected
2. **Partial apply** - Future consideration; v1 is all-or-nothing with ability to review/edit before apply
3. **Project-scoped stakeholders** - No cross-project sharing for now
4. **No notifications** - Future consideration; v1 shows suggestions inline only
