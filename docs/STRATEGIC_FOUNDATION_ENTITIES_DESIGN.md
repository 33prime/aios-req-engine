# Strategic Foundation Entities - First-Class Architecture Design

> **Design Date:** 2026-01-25
> **Status:** 🚧 ARCHITECTURAL DESIGN - Ready for Implementation
> **Priority:** ⚡ HIGH - Critical for gate scoring and client portal

---

## Executive Summary

Strategic Foundation entities (Business Drivers, References, Stakeholders, Constraints, Risks, Success Metrics) are currently **second-class citizens** in the system. They lack the sophisticated workflows that features and personas have:

- ❌ No smart merge with evidence preservation
- ❌ No enrichment chains
- ❌ No change tracking/versioning
- ❌ No lifecycle beyond basic confirmation
- ❌ No DI Agent tools for intelligent management
- ❌ No proposal system for updates
- ❌ Weak integration with client portal

This design elevates these entities to first-class status with the same rigor as features/personas.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [The 3 Strategic Foundation Tabs](#2-the-3-strategic-foundation-tabs)
3. [Desired Architecture](#3-desired-architecture)
4. [Entity-Specific Designs](#4-entity-specific-designs)
5. [DI Agent Integration](#5-di-agent-integration)
6. [Client Portal Integration](#6-client-portal-integration)
7. [Implementation Roadmap](#7-implementation-roadmap)

---

## 1. Current State Analysis

### 1.1 Existing Tables & Fields

| Entity | Table | Key Fields | Has Evidence | Has Confirmation | Has Enrichment |
|--------|-------|------------|--------------|------------------|----------------|
| **Business Drivers** | `business_drivers` | driver_type, description, measurement, priority | ❌ | ✅ | ❌ |
| **Competitor Refs** | `competitor_references` | reference_type, name, url, strengths, weaknesses | ❌ | ✅ | ❌ |
| **Stakeholders** | `stakeholders` | name, type, influence_level, priorities, concerns | ✅ | ✅ | ❌ |
| **Constraints** | `constraints` | constraint_type, description, severity | ❓ | ❓ | ❌ |
| **Risks** | ??? | ??? | ❌ | ❌ | ❌ |
| **Success Metrics** | ??? | ??? | ❌ | ❌ | ❌ |

### 1.2 Current Workflow Gaps

**Signal → Entity Flow:**
```
Signal Added
    ↓
run_strategic_foundation chain
    ├─ Extracts business_drivers via fact extraction
    ├─ Extracts competitor_refs via fact extraction
    └─ Creates new rows if not similar
    ↓
❌ NO evidence linking
❌ NO smart merge (just skips if similar)
❌ NO change tracking
❌ NO enrichment
```

**Client Portal Flow:**
```
Client edits Business Driver in portal
    ↓
??? How is this tracked?
??? How does consultant see the change?
??? How does DI Agent know about it?
??? How is it attributed?
```

### 1.3 Critical Issues

1. **No Evidence Attribution**
   - Business drivers extracted from signals have `source_signal_id` but no detailed `evidence[]` array
   - Can't trace WHY a driver exists or which signal chunks support it
   - Can't show client "here's where you said this"

2. **No Smart Merge**
   - Current: Find similar → skip creation
   - Needed: Find similar → merge evidence, update fields, track changes

3. **No Enrichment**
   - KPIs lack: baseline values, target values, measurement methodology
   - Competitors lack: feature comparison, pricing analysis, market positioning
   - Stakeholders lack: communication preferences, engagement history

4. **No Change Tracking**
   - Can't see: "Client updated 'Reduce data access time' from 5 seconds to 2 seconds"
   - No version history
   - No audit trail for compliance

5. **No DI Agent Tools**
   - DI Agent can't intelligently manage these entities
   - Can't extract KPI targets from signals
   - Can't enrich competitor analysis
   - Can't suggest stakeholder priorities

---

## 2. The 3 Strategic Foundation Tabs

### Tab 1: Project Context

**Displays:**
- Executive Summary (AI-generated)
- Opportunity (Problem, Business Opportunity, Why Now)
- Stakeholders (with roles and influence)
- Investment Case (Efficiency Gains, Cost Reduction, Risk Mitigation)
- Risks (with severity and mitigation)
- Success Metrics (KPIs)
- Project Constraints (Technical, Compliance)

**Data Sources:**
- `project_foundation` table → Opportunity section
- `stakeholders` table → Stakeholders section
- `business_drivers` (type=kpi) → Success Metrics section
- `risks` table → Risks section
- `constraints` table → Project Constraints section
- Investment Case → Computed from foundation + drivers?

### Tab 2: Business Drivers

**Displays 3 Columns:**
1. **KPIs** (green cards)
   - Title: "Reduce data access time"
   - Target: "[AI Suggestion] Measure the reduction in time taken to access health data"
2. **Pain Points** (red cards)
   - Title: "Difficulty accessing health data"
3. **Goals** (green cards)
   - Title: "Simplify health data access"

**Data Source:** `business_drivers` table filtered by `driver_type`

### Tab 3: References

**Displays 2 Sections:**
1. **Competitors**
   - Name, category, strengths, weaknesses
2. **Design Inspiration**
   - Reference products, design patterns

**Data Source:** `competitor_references` table filtered by `reference_type`

---

## 3. Desired Architecture

### 3.1 Universal Entity Pattern

ALL Strategic Foundation entities should follow this pattern (same as features/personas):

```typescript
interface StrategicEntity {
  // Core fields
  id: UUID
  project_id: UUID

  // Confirmation workflow
  confirmation_status: "ai_generated" | "confirmed_consultant" | "needs_client" | "confirmed_client"
  confirmed_by: UUID | null
  confirmed_at: timestamp | null

  // Evidence attribution
  evidence: Evidence[]  // Links to signal_chunks
  source_signal_ids: UUID[]  // All signals that contributed

  // Change tracking
  version: number
  created_by: "system" | "consultant" | "client" | "di_agent"
  updated_by: "system" | "consultant" | "client" | "di_agent"
  created_at: timestamp
  updated_at: timestamp

  // Enrichment
  enrichment_status: "none" | "pending" | "enriched"
  enriched_at: timestamp | null
  enrichment_confidence: number | null

  // Field-level confirmation
  confirmed_fields: Record<string, ConfirmationStatus>
}

interface Evidence {
  chunk_id: UUID
  signal_id: UUID
  quote: string
  relevance: number  // 0-1
  extracted_at: timestamp
}
```

### 3.2 Smart Merge Pattern

When a new signal creates an entity similar to an existing one:

```python
def smart_upsert_strategic_entity(
    project_id: UUID,
    entity_type: str,  # "business_driver", "competitor_ref", etc.
    new_data: dict,
    similarity_threshold: float = 0.85
):
    """
    Smart upsert with evidence merging and change tracking.
    """
    # 1. Find similar entities using multi-strategy matching
    similar = find_similar_entity(
        project_id,
        entity_type,
        new_data,
        threshold=similarity_threshold
    )

    if similar:
        # 2. Check confirmation status
        if similar["confirmation_status"] in CONFIRMED_STATUSES:
            # Entity is confirmed - MERGE evidence, don't replace
            merged_evidence = dedupe_evidence(
                similar["evidence"] + new_data["evidence"]
            )

            # 3. Track the change
            track_entity_change(
                entity_id=similar["id"],
                old_entity=similar,
                new_evidence=new_data["evidence"],
                trigger_event="signal_added",
                source_signal_id=new_data["source_signal_id"]
            )

            # 4. Update with new evidence
            update_entity(
                entity_id=similar["id"],
                evidence=merged_evidence,
                source_signal_ids=list(set(
                    similar["source_signal_ids"] + [new_data["source_signal_id"]]
                ))
            )

            return similar["id"], "merged"
        else:
            # Entity is AI-generated - update fields + merge evidence
            updated_fields = {}
            for field, new_value in new_data.items():
                if field in ["description", "measurement", "target"]:
                    if new_value != similar.get(field):
                        updated_fields[field] = new_value

            update_entity(
                entity_id=similar["id"],
                **updated_fields,
                evidence=dedupe_evidence(
                    similar["evidence"] + new_data["evidence"]
                ),
                version=similar["version"] + 1
            )

            return similar["id"], "updated"
    else:
        # No similar entity - create new
        new_entity = create_entity(project_id, entity_type, new_data)
        return new_entity["id"], "created"
```

### 3.3 Change Tracking

Extend existing `change_tracking` table to support all strategic entities:

```sql
-- Existing table schema (expand entity_type values)
CREATE TABLE change_tracking (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    entity_type TEXT NOT NULL,  -- Add: "business_driver", "competitor_ref", "stakeholder", "constraint", "risk", "success_metric"
    entity_id UUID NOT NULL,
    entity_label TEXT,
    change_type TEXT,  -- "created", "updated", "deleted", "merged", "confirmed"
    fields_changed JSONB,
    old_values JSONB,
    new_values JSONB,
    trigger_event TEXT,  -- "signal_added", "manual_edit", "di_agent", "client_portal"
    created_by TEXT,  -- "system", "consultant", "client", "di_agent"
    source_signal_id UUID,
    run_id UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Entity-Specific Designs

### 4.1 Business Drivers

#### Enhanced Schema

```sql
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS evidence JSONB DEFAULT '[]';
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}';
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS created_by TEXT DEFAULT 'system';
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS updated_by TEXT;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'none';
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS enrichment_confidence NUMERIC;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS confirmed_fields JSONB DEFAULT '{}';

-- KPI-specific enrichment fields
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS baseline_value TEXT;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS target_value TEXT;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS measurement_method TEXT;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS tracking_frequency TEXT;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS data_source TEXT;
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS responsible_team TEXT;
```

#### Enrichment Chain: `enrich_business_driver`

**For KPIs:**
```python
async def enrich_kpi(driver_id: UUID, project_id: UUID):
    """
    Enrich a KPI with structured measurement data.

    Extracts:
    - baseline_value: Current state (e.g., "5 seconds average")
    - target_value: Desired state (e.g., "2 seconds average")
    - measurement_method: How to measure (e.g., "Average query response time from logs")
    - tracking_frequency: How often to measure (e.g., "Weekly")
    - data_source: Where data comes from (e.g., "Application logs, Analytics dashboard")
    - responsible_team: Who owns this (e.g., "Data Engineering team")
    """
```

**For Pain Points:**
```python
async def enrich_pain_point(driver_id: UUID, project_id: UUID):
    """
    Enrich a pain point with impact analysis.

    Extracts:
    - impact_description: Detailed impact (e.g., "Causes 15 hours/week of wasted time")
    - affected_roles: Who feels this (e.g., ["Health Data Analyst", "Care Professional"])
    - frequency: How often it occurs (e.g., "Daily, 20+ times")
    - severity_score: 1-10 rating
    - workaround_cost: Cost of current workaround
    ```

**For Goals:**
```python
async def enrich_goal(driver_id: UUID, project_id: UUID):
    """
    Enrich a goal with success criteria.

    Extracts:
    - success_criteria: What success looks like
    - dependencies: What else needs to happen
    - timeline: When should this be achieved
    - business_value: Why this matters
    """
```

### 4.2 Competitor References

#### Enhanced Schema

```sql
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS evidence JSONB DEFAULT '[]';
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}';
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS created_by TEXT DEFAULT 'system';
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS updated_by TEXT;
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'none';
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS enrichment_confidence NUMERIC;
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS confirmed_fields JSONB DEFAULT '{}';

-- Competitive analysis enrichment fields
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS market_position TEXT;  -- "Leader", "Challenger", "Niche"
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS pricing_model TEXT;
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS pricing_range TEXT;
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS target_market TEXT;
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS tech_stack TEXT[];
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS feature_comparison JSONB;  -- {feature_name: "has" | "lacks" | "partial"}
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS design_patterns TEXT[];  -- ["Card-based UI", "Minimal navigation"]
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS last_researched_at TIMESTAMPTZ;
```

#### Enrichment Chain: `enrich_competitor_ref`

```python
async def enrich_competitor(ref_id: UUID, project_id: UUID):
    """
    Deep competitive analysis enrichment.

    Uses:
    1. Perplexity research for public data
    2. Website scraping (if URL provided)
    3. Signal analysis for client mentions

    Extracts:
    - market_position: Market position analysis
    - pricing_model: How they charge (subscription, usage-based, etc.)
    - pricing_range: Approximate pricing
    - target_market: Who they target
    - tech_stack: Technologies they use
    - feature_comparison: Feature-by-feature comparison with our project
    - design_patterns: UI/UX patterns to study
    """
```

### 4.3 Stakeholders

#### Enhanced Schema (mostly exists, add missing fields)

```sql
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS updated_by TEXT;
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'none';
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS enrichment_confidence NUMERIC;
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS confirmed_fields JSONB DEFAULT '{}';

-- Stakeholder engagement enrichment
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS communication_style TEXT;  -- "Direct", "Data-driven", "Relationship-focused"
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS decision_making_style TEXT;  -- "Analytical", "Intuitive", "Consensus-driven"
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS engagement_level TEXT;  -- "Champion", "Supporter", "Neutral", "Skeptic", "Blocker"
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS communication_frequency TEXT;  -- "Weekly", "Bi-weekly", "Monthly"
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS last_engagement_date DATE;
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS next_touchpoint_date DATE;
```

#### Enrichment Chain: `enrich_stakeholder`

```python
async def enrich_stakeholder(stakeholder_id: UUID, project_id: UUID):
    """
    Enrich stakeholder with engagement strategy.

    Analyzes signals mentioning this stakeholder to extract:
    - communication_style: How they prefer to communicate
    - decision_making_style: How they make decisions
    - engagement_level: Current engagement status
    - key_concerns: Specific concerns to address
    - influence_strategy: How to work with them effectively
    """
```

### 4.4 Risks (NEW TABLE)

```sql
CREATE TABLE IF NOT EXISTS risks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Risk details
    title TEXT NOT NULL,
    description TEXT,
    risk_type TEXT NOT NULL,  -- "technical", "business", "timeline", "resource", "market"
    category TEXT,  -- Subcategory
    severity TEXT NOT NULL DEFAULT 'medium',  -- "critical", "high", "medium", "low"
    likelihood TEXT NOT NULL DEFAULT 'medium',  -- "high", "medium", "low"
    impact_description TEXT,

    -- Mitigation
    mitigation_strategy TEXT,
    mitigation_owner TEXT,
    mitigation_status TEXT DEFAULT 'identified',  -- "identified", "in_progress", "mitigated", "accepted"
    contingency_plan TEXT,

    -- Evidence and confirmation
    evidence JSONB DEFAULT '[]',
    source_signal_ids UUID[] DEFAULT '{}',
    confirmation_status TEXT DEFAULT 'ai_generated',
    confirmed_by UUID,
    confirmed_at TIMESTAMPTZ,
    confirmed_fields JSONB DEFAULT '{}',

    -- Versioning and tracking
    version INTEGER DEFAULT 1,
    created_by TEXT DEFAULT 'system',
    updated_by TEXT,
    enrichment_status TEXT DEFAULT 'none',
    enriched_at TIMESTAMPTZ,
    enrichment_confidence NUMERIC,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_risks_project_id ON risks(project_id);
CREATE INDEX idx_risks_severity ON risks(project_id, severity);
CREATE INDEX idx_risks_risk_type ON risks(project_id, risk_type);
```

### 4.5 Success Metrics (Can use business_drivers with driver_type='kpi')

Success Metrics shown in "Project Context" tab are just **KPIs from business_drivers** with additional presentation logic.

---

## 5. DI Agent Integration

### 5.1 New DI Agent Tools

The DI Agent needs new tools to intelligently manage Strategic Foundation entities.

#### Tool: `extract_business_drivers`

```python
{
    "name": "extract_business_drivers",
    "description": "Extract and update business drivers (KPIs, pain points, goals) from signals. Uses smart merge to preserve confirmed drivers and add evidence.",
    "parameters": {
        "driver_types": ["kpi", "pain", "goal"],  # Which types to extract
        "enrich": bool,  # Whether to enrich after extraction
        "signal_ids": list[UUID] | None  # Specific signals to analyze, or all if None
    }
}
```

**Implementation:**
```python
async def _execute_extract_business_drivers(project_id: UUID, args: dict):
    """
    Extract business drivers with smart merge.

    1. Load signals (specified or all)
    2. Extract facts (pains, goals, kpis)
    3. For each extracted driver:
       - Find similar existing driver
       - If similar and confirmed → merge evidence
       - If similar and ai_generated → update + merge evidence
       - If not similar → create new
    4. Track all changes
    5. Optionally enrich new/updated drivers
    """
```

#### Tool: `enrich_business_driver`

```python
{
    "name": "enrich_business_driver",
    "description": "Deeply enrich a business driver with structured data (baselines, targets, measurement methods, impact analysis).",
    "parameters": {
        "driver_id": UUID,
        "depth": "standard" | "deep"
    }
}
```

#### Tool: `extract_competitors`

```python
{
    "name": "extract_competitors",
    "description": "Extract and update competitor references from signals. Identifies mentions of competitors, design inspiration, and feature inspiration.",
    "parameters": {
        "include_research": bool,  # Whether to use Perplexity for additional research
        "signal_ids": list[UUID] | None
    }
}
```

#### Tool: `enrich_competitor`

```python
{
    "name": "enrich_competitor",
    "description": "Deep competitive analysis including market position, pricing, features, tech stack, design patterns.",
    "parameters": {
        "ref_id": UUID,
        "include_web_scraping": bool,  # Whether to scrape their website
        "feature_comparison": bool  # Whether to compare features with our project
    }
}
```

#### Tool: `extract_stakeholders`

```python
{
    "name": "extract_stakeholders",
    "description": "Extract and update project stakeholders from signals. Identifies people, their roles, influence, priorities, and concerns.",
    "parameters": {
        "link_to_personas": bool,  # Whether to link stakeholders to personas
        "signal_ids": list[UUID] | None
    }
}
```

#### Tool: `extract_risks`

```python
{
    "name": "extract_risks",
    "description": "Extract project risks from signals. Identifies technical, business, timeline, and market risks with mitigation strategies.",
    "parameters": {
        "risk_types": ["technical", "business", "timeline", "resource", "market"],
        "signal_ids": list[UUID] | None
    }
}
```

#### Tool: `enrich_constraint`

```python
{
    "name": "enrich_constraint",
    "description": "Enrich a project constraint with detailed analysis of impact, alternatives, and dependencies.",
    "parameters": {
        "constraint_id": UUID
    }
}
```

### 5.2 DI Agent Decision Logic

Update DI Agent prompts to recognize when to use these tools:

```python
STRATEGIC_FOUNDATION_TOOLS_GUIDANCE = """
When analyzing signals, consider extracting Strategic Foundation entities:

USE extract_business_drivers WHEN:
- Signal mentions pain points, challenges, frustrations
- Signal discusses goals, objectives, desired outcomes
- Signal specifies KPIs, metrics, success criteria, targets
- Client describes "what success looks like"

USE extract_competitors WHEN:
- Signal mentions competitor names or products
- Client says "like [Product]" or "similar to [Company]"
- Signal discusses market alternatives or comparisons
- Client provides design or feature inspiration references

USE extract_stakeholders WHEN:
- Signal introduces new people with roles
- Signal describes organizational structure
- Signal mentions decision makers or influencers
- Client discusses who needs to approve/review

USE extract_risks WHEN:
- Signal expresses concerns, worries, or fears
- Signal discusses potential problems or blockers
- Signal mentions technical challenges or unknowns
- Client asks "what if" questions

ENRICHMENT PRIORITY:
1. Enrich KPIs first (needed for gate scoring)
2. Enrich competitors if researching alternatives
3. Enrich stakeholders if engagement planning needed
4. Enrich risks if mitigation planning needed
"""
```

---

## 6. Client Portal Integration

### 6.1 Portal Workflows

#### Client Adds/Edits Business Driver

```
Client Portal
    ↓
Client adds pain point: "Manual data entry is time-consuming"
    ↓
POST /api/portal/business-drivers
{
    "driver_type": "pain",
    "description": "Manual data entry is time-consuming",
    "created_by": "client",
    "confirmation_status": "confirmed_client"
}
    ↓
Create business_driver record
    ├─ created_by = "client"
    ├─ confirmation_status = "confirmed_client"
    ├─ evidence = [] (no signal chunks, added manually)
    └─ Track change: trigger_event="client_portal_add"
    ↓
Invalidate state snapshot
    ↓
Notify consultant: "Client added new pain point"
    ↓
DI Agent analyzes on next invocation
    ├─ OBSERVE: New client-confirmed pain point exists
    ├─ THINK: Should we extract more context from signals?
    └─ DECIDE: Suggest enrichment or research
```

#### Client Edits Existing Driver

```
Client edits KPI target
    ↓
PATCH /api/portal/business-drivers/{id}
{
    "target_value": "2 seconds (was 5 seconds)",
    "updated_by": "client"
}
    ↓
Update business_driver
    ├─ version += 1
    ├─ updated_by = "client"
    ├─ Track change showing old vs new value
    └─ Optionally create proposal if consultant needs to review
    ↓
Refresh readiness score (targets affect gate scoring)
    ↓
Notify consultant: "Client updated KPI target"
```

### 6.2 Bidirectional Sync

**Consultant → Client:**
```
Consultant enriches business driver in workbench
    ↓
Enrichment adds: baseline_value, measurement_method, data_source
    ↓
Changes immediately visible in client portal
    ↓
Client can review and confirm
```

**Client → Consultant:**
```
Client confirms enriched KPI in portal
    ↓
confirmation_status: "confirmed_consultant" → "confirmed_client"
    ↓
Workbench shows updated confirmation status
    ↓
Readiness gate score updated (confirmed = more points)
```

### 6.3 Conflict Resolution

**Scenario:** Client edits a driver while consultant enriches it

```
1. Client starts edit at T0
2. Consultant enriches at T1 (version 2)
3. Client submits edit at T2

OPTIONS:
A. Last-write-wins (risky - may lose data)
B. Optimistic locking (reject client edit, show conflict)
C. Field-level merge (recommended)

RECOMMENDED: Field-level merge
- Track which fields changed in each update
- Merge non-conflicting fields
- For conflicts, create proposal for review
- Show diff in UI: "You changed X, consultant changed Y"
```

---

## 7. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Database Migrations:**
- [ ] Add `evidence`, `source_signal_ids`, `version`, tracking fields to `business_drivers`
- [ ] Add enrichment fields to `business_drivers` (baseline, target, method, etc.)
- [ ] Add same fields to `competitor_references`
- [ ] Add same fields to `stakeholders`
- [ ] Create `risks` table with full schema
- [ ] Extend `change_tracking` to support all entity types

**Core Functions:**
- [ ] `smart_upsert_business_driver()` with evidence merging
- [ ] `smart_upsert_competitor_ref()` with evidence merging
- [ ] `smart_upsert_stakeholder()` with evidence merging
- [ ] `track_strategic_entity_change()` - unified change tracking
- [ ] Update `find_similar_driver()` to use multi-strategy matching
- [ ] Update `find_similar_competitor()` to use multi-strategy matching

### Phase 2: Extraction & Enrichment (Week 2-3)

**Extraction Chains:**
- [ ] Update `extract_strategic_entities_from_signals()` to use smart upsert
- [ ] Create `extract_risks_from_signals()` chain

**Enrichment Chains:**
- [ ] `enrich_kpi()` - baselines, targets, measurement
- [ ] `enrich_pain_point()` - impact analysis, affected roles
- [ ] `enrich_goal()` - success criteria, dependencies
- [ ] `enrich_competitor()` - market analysis, feature comparison
- [ ] `enrich_stakeholder()` - engagement strategy
- [ ] `enrich_risk()` - mitigation analysis
- [ ] `enrich_constraint()` - impact analysis

### Phase 3: DI Agent Integration (Week 3-4)

**DI Agent Tools:**
- [ ] `extract_business_drivers` tool
- [ ] `enrich_business_driver` tool
- [ ] `extract_competitors` tool
- [ ] `enrich_competitor` tool
- [ ] `extract_stakeholders` tool
- [ ] `extract_risks` tool
- [ ] `enrich_constraint` tool

**DI Agent Prompts:**
- [ ] Update system prompt with Strategic Foundation guidance
- [ ] Add tool descriptions and when to use them
- [ ] Add examples of good vs bad tool usage

### Phase 4: Client Portal Integration (Week 4-5)

**Portal API Endpoints:**
- [ ] `POST /api/portal/business-drivers` - Client creates driver
- [ ] `PATCH /api/portal/business-drivers/{id}` - Client updates driver
- [ ] `POST /api/portal/business-drivers/{id}/confirm` - Client confirms
- [ ] Similar endpoints for competitors, stakeholders, risks, constraints

**Portal UI Components:**
- [ ] Business Drivers tab (KPIs, Pain Points, Goals)
- [ ] References tab (Competitors, Design Inspiration)
- [ ] Stakeholders section in Project Context
- [ ] Risks section in Project Context
- [ ] Success Metrics section in Project Context

**Sync & Notifications:**
- [ ] Real-time updates when consultant changes entities
- [ ] Notifications when client changes entities
- [ ] Conflict resolution UI
- [ ] Change history viewer

### Phase 5: Analytics & Reporting (Week 5-6)

**Change Analytics:**
- [ ] Dashboard showing which entities clients engage with most
- [ ] Heat map of client-consultant collaboration
- [ ] Version history visualization

**Gate Impact Tracking:**
- [ ] Show how enriched KPIs improve gate scores
- [ ] Show how confirmed stakeholders improve confidence
- [ ] Track correlation between enrichment and project success

---

## 8. Success Metrics

### Implementation Success Criteria

1. **Data Quality**
   - [ ] 90%+ of business drivers have evidence attribution
   - [ ] 80%+ of KPIs have enriched targets and baselines
   - [ ] 70%+ of competitors have feature comparison data

2. **Client Engagement**
   - [ ] Clients add/edit 5+ strategic foundation items per project
   - [ ] 60%+ client confirmation rate on AI-suggested items
   - [ ] <10% conflict rate (client edits conflicting with consultant)

3. **DI Agent Effectiveness**
   - [ ] DI Agent correctly identifies when to extract strategic entities 90%+ of time
   - [ ] Enrichment quality score 4+/5 (human eval)
   - [ ] Smart merge reduces duplicates by 80%

4. **Gate Scoring Impact**
   - [ ] Projects with enriched KPIs score 15%+ higher on Business Case gate
   - [ ] Projects with confirmed stakeholders score 20%+ higher on Team Readiness gate

---

## 9. Technical Considerations

### 9.1 Performance

**Caching Strategy:**
- Cache enriched strategic entities (10-minute TTL)
- Invalidate on update
- Batch-load for state snapshot generation

**Parallel Processing:**
- Enrich multiple entities in parallel
- Use async/await for enrichment chains
- Queue enrichment jobs for background processing

### 9.2 Data Migration

**For existing projects:**
```python
async def migrate_existing_strategic_entities():
    """
    Backfill evidence and tracking fields for existing entities.

    1. For each business_driver with source_signal_id:
       - Find signal chunks that mention the driver
       - Create evidence array from matching chunks
    2. Set created_by = "system" for all existing
    3. Set version = 1
    4. Set enrichment_status based on field completeness
    """
```

### 9.3 Testing Strategy

**Unit Tests:**
- `test_smart_upsert_business_driver_merge_evidence()`
- `test_smart_upsert_business_driver_update_ai_generated()`
- `test_smart_upsert_business_driver_preserve_confirmed()`
- `test_enrich_kpi_extraction_quality()`

**Integration Tests:**
- `test_signal_to_business_driver_with_evidence()`
- `test_client_portal_edit_creates_change_log()`
- `test_di_agent_extracts_business_drivers()`

**E2E Tests:**
- `test_full_workflow_signal_to_enriched_driver()`
- `test_client_consultant_collaboration()`

---

## 10. Open Questions

1. **Proposal System:** Should client edits to confirmed entities require consultant approval?
   - Option A: Yes, always create proposal for confirmed items
   - Option B: No, client can directly edit (they're the source of truth)
   - **Recommendation:** Option B, but track all changes and notify consultant

2. **Bulk Operations:** How to handle bulk import of KPIs from spreadsheet?
   - Need `POST /api/business-drivers/bulk` endpoint
   - Support CSV upload with smart merge
   - Show preview before committing

3. **Enrichment Triggers:** When should auto-enrichment happen?
   - Option A: Immediately after extraction
   - Option B: On-demand when consultant requests
   - Option C: Batched nightly for efficiency
   - **Recommendation:** Option B for interactive, Option C for batch

4. **Evidence Confidence:** How to score evidence relevance?
   - Use semantic similarity between driver description and chunk content
   - Score 0-1, only include chunks >0.7 relevance
   - Show confidence in UI

---

## Conclusion

Elevating Strategic Foundation entities to first-class status will:

✅ **Improve data quality** - Evidence attribution ensures traceability
✅ **Enable intelligent updates** - Smart merge prevents duplicates while preserving human input
✅ **Empower DI Agent** - New tools allow intelligent entity management
✅ **Enhance client collaboration** - Portal integration enables true co-creation
✅ **Increase gate scores** - Enriched entities provide better readiness signals
✅ **Build audit trails** - Change tracking ensures compliance and transparency

**Priority:** This is HIGH priority work that directly impacts:
- Gate scoring accuracy
- Client portal value
- DI Agent effectiveness
- Overall system data quality

**Estimated Effort:** 5-6 weeks for full implementation across all phases.

---

**Next Steps:**
1. Review and approve this design
2. Create implementation tasks
3. Start Phase 1 (database migrations)
4. Iterate with user feedback

**Document Status:** Ready for implementation review
**Last Updated:** 2026-01-25
