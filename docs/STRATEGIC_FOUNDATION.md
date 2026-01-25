# Strategic Foundation System

**Version:** 1.0
**Last Updated:** 2026-01-25

## Overview

The Strategic Foundation is a comprehensive system for extracting, enriching, and tracking strategic context from client signals. It provides a structured layer of business intelligence that informs readiness gates, agent decision-making, and project planning.

**Core Principle:** Everything traces back to signals. Every strategic entity, every field, every insight can be attributed to its source with evidence and confidence scores.

## Entity Types

### 1. Business Drivers

Business drivers represent the measurable objectives and challenges that justify the project.

**Three subtypes:**

| Type | Purpose | Example |
|------|---------|---------|
| **KPI** | Measurable success metrics | "Reduce support tickets by 40%" |
| **Pain** | Current problems/inefficiencies | "Manual onboarding takes 10 hours/customer" |
| **Goal** | Desired future state | "Launch self-service portal by Q2" |

**Base fields:**
- `driver_type`: 'kpi', 'pain', or 'goal'
- `description`: Natural language description
- `measurement`: Quantifiable metric (for KPIs) or impact (for pains)
- `timeframe`: Target completion date/period
- `priority`: 1-5 (5 = highest)
- `stakeholder_id`: Link to stakeholder who owns this driver

**Enrichment fields:**
- `baseline_value`: Current state measurement
- `current_state`: Qualitative description of current situation
- `target_state`: Desired future state
- `success_criteria`: How to measure success
- `stakeholder_importance`: Why this matters to stakeholders
- `business_impact`: ROI, cost savings, revenue impact
- `affected_users`: Who is impacted by this pain/goal
- `severity`: For pains - low/medium/high/critical

**Gate impact:**
- KPIs with `baseline_value` and `business_impact` → **business_case** gate
- Pains with `severity` and `affected_users` → **core_pain** gate
- Goals with `success_criteria` → **wow_moment** gate

### 2. Competitor References

Competitor references track competitive landscape and design inspiration.

**Types:**
- `competitor`: Direct market competitor
- `design_inspiration`: Product referenced for design patterns
- `feature_inspiration`: Product referenced for specific features

**Base fields:**
- `name`: Competitor/product name
- `reference_type`: competitor/design_inspiration/feature_inspiration
- `category`: Market category
- `website`: URL
- `strengths`: List of competitive advantages
- `weaknesses`: List of competitive gaps
- `features_to_study`: Specific features to analyze
- `research_notes`: Additional context

**Enrichment fields:**
- `market_position`: Market share, positioning
- `pricing_model`: Pricing strategy and tiers
- `key_differentiator`: What makes them unique
- `target_customers`: Their ideal customer profile
- `core_features`: Main feature set

**Gate impact:**
- Competitors with `key_differentiator` → **wow_moment** gate (differentiation strategy)
- Competitors with `market_position` → **business_case** gate (competitive context)

### 3. Stakeholders

Stakeholders represent the people involved in or affected by the project.

**Types:**
- `champion`: Strong advocate for the project
- `sponsor`: Executive sponsor with budget authority
- `user`: End user of the solution
- `blocker`: Potential resistance or obstacles
- `influencer`: Opinion leader without direct authority

**Base fields:**
- `name`: Full name
- `role`: Job title
- `organization`: Company/department
- `stakeholder_type`: champion/sponsor/user/blocker/influencer
- `influence_level`: high/medium/low
- `is_economic_buyer`: Boolean - has budget authority
- `priorities`: List of their key priorities
- `concerns`: List of their concerns/objections

**Enrichment fields:**
- `engagement_level`: highly_engaged/moderately_engaged/neutral/disengaged/unknown
- `decision_authority`: Scope of decision-making power
- `engagement_strategy`: How to keep them engaged
- `risk_if_disengaged`: Impact if they lose interest
- `win_conditions`: What they need to see to support project
- `key_concerns`: Specific concerns to address

**Gate impact:**
- Economic buyers with `decision_authority` → **primary_persona** gate
- Champions with `engagement_level` = highly_engaged → **business_case** gate
- Users with `win_conditions` → **core_pain** gate

### 4. Risks

Risks represent threats to project success.

**Types:**
- `technical`: Technology/implementation risks
- `resource`: Team/budget/time constraints
- `stakeholder`: People/political risks
- `market`: External market factors
- `compliance`: Regulatory/legal risks

**Base fields:**
- `title`: Short risk description
- `risk_type`: technical/resource/stakeholder/market/compliance
- `severity`: low/medium/high/critical
- `description`: Detailed risk description
- `likelihood`: low/medium/high

**Enrichment fields:**
- `impact_on_timeline`: How it affects schedule
- `impact_on_budget`: Financial impact
- `impact_on_scope`: What features are at risk
- `affected_stakeholders`: Who is impacted
- `probability`: Quantified likelihood
- `mitigation_strategy`: How to prevent/reduce risk
- `contingency_plan`: What to do if it happens
- `owner`: Who owns risk mitigation

**Gate impact:**
- Critical risks with `mitigation_strategy` → **business_case** gate (risk awareness)
- High-severity risks → Analytics recommendations

## Universal Entity Fields

All strategic entities share these tracking fields:

**Source Attribution:**
- `source_signal_ids`: Array of signal UUIDs that contributed to this entity
- `evidence`: Array of evidence objects with chunk_id, quote, confidence

**Confirmation Status:**
- `confirmed_client`: Client explicitly confirmed this
- `confirmed_consultant`: Consultant validated this
- `ai_generated`: AI extracted/inferred this
- `needs_confirmation`: Requires validation

**Enrichment Status:**
- `none`: Not enriched yet
- `enriched`: Successfully enriched with LLM
- `failed`: Enrichment failed

**Version Control:**
- `version`: Integer version number
- `created_at`: Initial creation timestamp
- `updated_at`: Last modification timestamp
- `created_by`: User/system that created entity

## Workflows

### Extraction Workflow

```
Signal Ingestion
    ↓
Heavyweight Classification
    ↓
Strategic Foundation Extraction
    ↓
Similarity Matching (6-strategy cascade)
    ↓
Smart Upsert
    ↓
Entity Created/Updated
```

**1. Signal Ingestion**

Signals (transcripts, emails, notes, research) are chunked and stored with authority metadata:
- `client`: Direct from client (highest authority)
- `consultant`: From consultant notes
- `ai`: AI-generated insights
- `research`: From research sources

**2. Extraction Chains**

Each entity type has a dedicated extraction chain:
- `extract_business_drivers_from_signals(project_id, signal_ids)`
- `extract_competitors_from_signals(project_id, signal_ids)`
- `extract_stakeholders_from_signals(project_id, signal_ids)`
- `extract_risks_from_signals(project_id, signal_ids)`

These use LLM with PydanticOutputParser to extract structured entities with evidence.

**3. Similarity Matching**

Uses 6-strategy cascade to find duplicates:
1. Exact match
2. Normalized match (lowercase, stripped)
3. Token set match (order-independent)
4. Partial match
5. Key terms match
6. Semantic similarity (embeddings)

**4. Smart Upsert**

Handles duplicate resolution based on confirmation status:

```python
if existing.confirmation_status in ["confirmed_client", "confirmed_consultant"]:
    # MERGE: Preserve confirmed entity, add new evidence
    merged_evidence = existing.evidence + new.evidence
    merged_source_ids = existing.source_signal_ids + new.source_signal_ids
    return update(existing, evidence=merged_evidence, source_signal_ids=merged_source_ids)

elif existing.confirmation_status == "ai_generated":
    # UPDATE: Replace AI-generated with new extraction
    return update(existing, **new_fields)

else:
    # CREATE: No match, create new entity
    return create(new_entity)
```

### Enrichment Workflow

```
Entity Extraction
    ↓
Enrich Entity (LLM Call)
    ↓
Validate Enrichment
    ↓
Update Entity + Create Revision
    ↓
Recompute Gate Impact
```

**Enrichment Chains:**
- `enrich_business_driver(project_id, driver_id)` - Adds baseline, impact, success criteria
- `enrich_competitor(project_id, competitor_id)` - Adds market position, pricing, differentiators
- `enrich_stakeholder(project_id, stakeholder_id)` - Adds engagement level, decision authority, win conditions
- `enrich_risk(project_id, risk_id)` - Adds mitigation strategies, contingency plans

**Enrichment triggers:**
1. Manual enrichment via API
2. DI Agent tool calls (`enrich_business_driver`, etc.)
3. Batch enrichment jobs

**Revision Tracking:**

Every enrichment creates a revision entry in `enrichment_revisions`:
```python
{
    "entity_type": "business_driver",
    "entity_id": uuid,
    "revision_type": "enrichment",
    "changes": {
        "baseline_value": {"old": null, "new": "500 tickets/week"},
        "business_impact": {"old": null, "new": "$120K savings"}
    },
    "enrichment_model": "gpt-4o",
    "created_at": timestamp
}
```

### Gate Impact Analysis

Strategic entities directly influence readiness gate confidence.

**Impact Calculation:**

```python
def compute_entity_contribution_to_gate(entity, gate_name):
    """
    Returns contribution score (0.0 - 1.0) based on:
    - How many relevant fields are enriched
    - Quality of enrichment (length, specificity)
    - Entity confirmation status
    """
    if entity.enrichment_status != "enriched":
        return 0.0

    # Get relevant fields for this gate
    relevant_fields = FIELD_TO_GATE_MAP[entity_type][gate_name]

    # Count enriched fields
    enriched_count = sum(1 for f in relevant_fields if entity[f] is not None)

    # Compute base contribution
    base_score = enriched_count / len(relevant_fields)

    # Boost for confirmed entities
    if entity.confirmation_status in ["confirmed_client", "confirmed_consultant"]:
        base_score *= 1.2

    return min(base_score, 1.0)
```

**Field-to-Gate Mapping:**

| Entity Type | Enriched Field | Impacted Gate |
|-------------|----------------|---------------|
| Business Driver (KPI) | baseline_value | business_case |
| Business Driver (KPI) | business_impact | business_case |
| Business Driver (Pain) | severity | core_pain |
| Business Driver (Pain) | affected_users | core_pain |
| Business Driver (Goal) | success_criteria | wow_moment |
| Competitor | market_position | wow_moment, business_case |
| Competitor | key_differentiator | wow_moment |
| Stakeholder (Economic Buyer) | decision_authority | primary_persona |
| Stakeholder | win_conditions | core_pain |
| Risk (Critical) | mitigation_strategy | business_case |

**Using Gate Impact:**

```python
from app.core.readiness.gate_impact import get_entity_gate_impact_summary

impact = get_entity_gate_impact_summary(project_id)

# Per-gate breakdown
for gate in impact["gates"]:
    print(f"{gate['gate_name']}: {gate['contributing_entities']} entities")
    print(f"  Enrichment: {gate['enrichment_coverage']}%")
    print(f"  Boost: +{gate['confidence_boost']}%")
    print(f"  Recommendations: {gate['recommendations']}")

# Overall summary
print(f"Total entities: {impact['overall']['total_strategic_entities']}")
print(f"Avg enrichment: {impact['overall']['average_enrichment_coverage']}%")
print(f"Total boost: +{impact['overall']['total_confidence_boost']}%")
```

## DI Agent Integration

The DI Agent has 6 strategic foundation tools available:

### Extraction Tools

**1. extract_business_drivers**
```python
{
    "name": "extract_business_drivers",
    "description": "Extract KPIs, pains, and goals from signals",
    "parameters": {
        "signal_ids": ["uuid1", "uuid2"]
    }
}
```

**2. extract_competitors**
```python
{
    "name": "extract_competitors",
    "description": "Extract competitor references from signals",
    "parameters": {
        "signal_ids": ["uuid1", "uuid2"]
    }
}
```

**3. extract_stakeholders**
```python
{
    "name": "extract_stakeholders",
    "description": "Extract stakeholder information from signals",
    "parameters": {
        "signal_ids": ["uuid1", "uuid2"]
    }
}
```

**4. extract_risks**
```python
{
    "name": "extract_risks",
    "description": "Extract project risks from signals",
    "parameters": {
        "signal_ids": ["uuid1", "uuid2"]
    }
}
```

### Enrichment Tools

**5. enrich_business_driver**
```python
{
    "name": "enrich_business_driver",
    "description": "Enrich KPI/pain/goal with baseline, impact, success criteria",
    "parameters": {
        "driver_id": "uuid"
    }
}
```

**6. enrich_competitor**
```python
{
    "name": "enrich_competitor",
    "description": "Enrich competitor with market position, pricing, differentiators",
    "parameters": {
        "competitor_id": "uuid"
    }
}
```

**DI Agent Workflow:**

```
User: "I'm looking at the transcript - what KPIs should we focus on?"

DI Agent:
1. Identifies relevant signals containing KPI mentions
2. Calls extract_business_drivers with signal IDs
3. Reviews extracted KPIs
4. Calls enrich_business_driver for top KPIs
5. Analyzes gate impact
6. Recommends prioritization based on business impact and gate contribution
```

## Analytics & Reporting

### Strategic Analytics Dashboard

Access at: `/projects/{projectId}/strategic-foundation` → Analytics tab

**Metrics Displayed:**

1. **Entity Counts**
   - Total entities across all types
   - Breakdown by type (business_drivers, kpis, pains, goals, competitors, stakeholders, risks)

2. **Enrichment Stats**
   - Enrichment rate (% enriched)
   - Average evidence per entity
   - Enriched vs. not enriched vs. failed counts

3. **Confirmation Stats**
   - Confirmed by client count
   - Confirmed by consultant count
   - AI-generated count
   - Needs confirmation count
   - Overall confirmation rate

4. **Source Coverage**
   - Entities with source attribution (%)
   - Average sources per entity
   - Top source signals by entity count

5. **Recommendations**
   - Auto-generated based on thresholds:
     - < 50% enrichment → "Enrich more entities"
     - Needs confirmation > 0 → "Review X entities with client"
     - < 80% source coverage → "Improve attribution"
     - < 3 KPIs → "Extract more KPIs"
     - 0 risks → "Run risk extraction"
     - AI-generated > confirmed → "Prioritize validation"

### API Endpoint

```
GET /v1/projects/{project_id}/strategic-analytics
```

Response:
```json
{
  "entity_counts": {
    "business_drivers": 12,
    "kpis": 5,
    "pains": 4,
    "goals": 3,
    "competitor_refs": 3,
    "stakeholders": 8,
    "risks": 2,
    "total": 25
  },
  "enrichment_stats": {
    "enriched": 15,
    "none": 8,
    "failed": 2,
    "enrichment_rate": 0.6,
    "avg_evidence_per_entity": 2.3
  },
  "confirmation_stats": {
    "confirmed_client": 10,
    "confirmed_consultant": 5,
    "ai_generated": 7,
    "needs_confirmation": 3,
    "confirmation_rate": 0.6
  },
  "source_coverage": {
    "entities_with_sources": 20,
    "total_entities": 25,
    "coverage_rate": 0.8,
    "avg_sources_per_entity": 1.6,
    "top_source_signals": [
      {"signal_id": "uuid1", "entity_count": 8},
      {"signal_id": "uuid2", "entity_count": 5}
    ]
  },
  "recommendations": [
    "Only 60% of entities are enriched. Run enrichment on key entities.",
    "3 entities need client confirmation. Review with client.",
    "Only 5 KPIs defined. Extract more from discussions."
  ]
}
```

## API Endpoints

### Business Drivers

```
GET    /v1/projects/{project_id}/business-drivers
GET    /v1/projects/{project_id}/business-drivers/by-type/{type}
POST   /v1/projects/{project_id}/business-drivers
GET    /v1/projects/{project_id}/business-drivers/{driver_id}
PATCH  /v1/projects/{project_id}/business-drivers/{driver_id}
DELETE /v1/projects/{project_id}/business-drivers/{driver_id}
```

### Competitor References

```
GET    /v1/projects/{project_id}/competitors
POST   /v1/projects/{project_id}/competitors
GET    /v1/projects/{project_id}/competitors/{competitor_id}
PATCH  /v1/projects/{project_id}/competitors/{competitor_id}
DELETE /v1/projects/{project_id}/competitors/{competitor_id}
```

### Stakeholders

```
GET    /v1/state/stakeholders?project_id={project_id}
POST   /v1/state/stakeholders
PATCH  /v1/state/stakeholders/{stakeholder_id}
DELETE /v1/state/stakeholders/{stakeholder_id}
```

### Risks

```
GET    /v1/projects/{project_id}/risks
GET    /v1/projects/{project_id}/risks/critical
POST   /v1/projects/{project_id}/risks
GET    /v1/projects/{project_id}/risks/{risk_id}
PATCH  /v1/projects/{project_id}/risks/{risk_id}
DELETE /v1/projects/{project_id}/risks/{risk_id}
```

### Analytics & Impact

```
GET    /v1/projects/{project_id}/strategic-analytics
GET    /v1/projects/{project_id}/readiness/gate-impact
```

### Change History

```
GET    /v1/state/{entity_type}/{entity_id}/revisions?limit=20
```

## Best Practices

### 1. Extraction Strategy

**Do:**
- Run extraction on heavyweight signals (transcripts, research)
- Process signals in batches for efficiency
- Review extraction results before enrichment
- Let smart upsert handle duplicates automatically

**Don't:**
- Extract from every signal (use lightweight/heavyweight classification)
- Skip similarity matching (leads to duplicates)
- Override confirmed entities without reason

### 2. Enrichment Strategy

**Prioritize enrichment for:**
1. Confirmed entities (client/consultant validated)
2. Entities linked to multiple signals (high signal)
3. Entities that impact multiple gates
4. Critical risks and high-priority KPIs

**Enrichment order:**
1. Business drivers (KPIs → pains → goals)
2. Stakeholders (economic buyers first)
3. Competitors (direct competitors before inspiration)
4. Risks (critical/high severity first)

### 3. Confirmation Workflow

**Always confirm:**
- Business drivers that impact critical gates
- Stakeholder decision authority and influence
- Risk severity and probability
- Competitive positioning claims

**Confirmation methods:**
- Client portal review
- Call follow-ups
- Async validation via email/Slack

### 4. Gate Impact Optimization

**To maximize gate confidence:**

For **business_case** gate:
- Enrich KPIs with baseline_value and business_impact
- Enrich critical risks with mitigation strategies
- Identify economic buyer stakeholders

For **core_pain** gate:
- Enrich pains with severity and affected_users
- Link stakeholders to pain points
- Quantify pain impact

For **wow_moment** gate:
- Enrich competitors with key_differentiator
- Define clear goals with success_criteria
- Identify design inspiration references

For **primary_persona** gate:
- Enrich economic buyers with decision_authority
- Document stakeholder win_conditions
- Link stakeholders to business drivers

### 5. Data Quality

**Maintain quality:**
- Always include evidence with confidence scores
- Link entities to source signals
- Track confirmation status accurately
- Create revisions for significant changes
- Review analytics recommendations weekly

**Red flags:**
- < 50% enrichment rate
- > 30% AI-generated without confirmation
- < 70% source coverage
- 0 risks identified (usually unrealistic)
- No economic buyers identified

## Integration Points

### Signal Pipeline

Strategic Foundation integrates at the **consolidate** step:

```
Signal → Classify (heavy/light) → Extract (if heavy) → Consolidate
                                           ↓
                                 Strategic Foundation Extraction
                                           ↓
                                 Smart Upsert + Evidence Tracking
```

### Readiness System

Strategic entities boost gate confidence through enrichment:

```
Compute Readiness
    ↓
For each gate:
    ↓
    Get contributing strategic entities
    ↓
    Calculate enrichment coverage
    ↓
    Apply confidence boost
    ↓
Return ReadinessScore with caps/boosts
```

### DI Agent

DI Agent uses strategic entities to inform recommendations:

```
DI Agent Gate Analysis
    ↓
Fetch strategic entities
    ↓
Assess enrichment coverage
    ↓
Identify gaps (missing KPIs, unconfirmed risks, etc.)
    ↓
Recommend extraction/enrichment actions
    ↓
Execute tools to improve gate confidence
```

## Migration & Backfilling

If adding Strategic Foundation to existing projects:

1. **Backfill extraction:**
   ```python
   from app.chains.strategic_foundation import extract_all_strategic_entities

   # Extract from all heavyweight signals
   heavy_signals = get_heavyweight_signals(project_id)
   result = extract_all_strategic_entities(project_id, heavy_signals)
   ```

2. **Prioritize enrichment:**
   ```python
   # Get unenriched entities linked to multiple signals
   drivers = business_drivers.list_business_drivers(project_id)
   high_signal = [d for d in drivers if len(d["source_signal_ids"]) >= 2]

   for driver in high_signal:
       enrich_business_driver(project_id, driver["id"])
   ```

3. **Validate with client:**
   - Export to client portal
   - Schedule review session
   - Update confirmation statuses

## Testing

See `tests/test_strategic_foundation_e2e.py` for comprehensive end-to-end test coverage including:

- Extraction → enrichment → gate impact flow
- Smart upsert with confirmation status handling
- Analytics computation across all entity types
- Change history and revision tracking
- Multi-signal evidence merging

## Troubleshooting

**Issue:** Duplicates being created despite similarity matching

**Solution:** Check similarity thresholds in `app/core/similarity.py`. May need to tune semantic similarity threshold or add custom normalization rules for domain-specific terms.

---

**Issue:** Enrichment failing with validation errors

**Solution:** Check LLM response format. Use PydanticOutputParser with explicit schema. Log raw responses for debugging.

---

**Issue:** Gate impact not reflecting enriched entities

**Solution:** Verify field-to-gate mapping in `app/core/readiness/gate_impact.py`. Ensure enriched fields match expected field names.

---

**Issue:** Analytics showing incorrect counts

**Solution:** Check filter logic in `app/api/strategic_analytics.py`. Verify entity type comparisons are case-sensitive and exact matches.

---

## Future Enhancements

- **Real-time sync:** WebSocket updates for collaborative editing (Task #38)
- **Conflict resolution:** UI for resolving concurrent edits (Task #39)
- **Automated enrichment:** Background jobs for batch enrichment
- **Trend analysis:** Historical tracking of entity changes over time
- **Client portal:** Self-service validation and feedback workflows
- **Export:** PDF/Excel exports for client presentations

---

**For questions or contributions, see:**
- [CLAUDE.md](../CLAUDE.md) - Working context and patterns
- [README.md](../README.md) - Project overview
- API docs: `http://localhost:8000/docs` (when running locally)
