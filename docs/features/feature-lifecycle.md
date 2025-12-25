# Feature Lifecycle Management

## Overview

Features progress through three lifecycle stages:
1. **Discovered**: Initially identified from signals and reconciliation
2. **Refined**: Enriched with detailed information
3. **Confirmed**: Validated and approved by client

## Lifecycle Stages

### Discovered

**When**: Features are created during the reconciliation agent run.

**Characteristics**:
- Minimal information (name, slug, basic description)
- No enrichment data yet
- Automatically set during reconciliation

**UI**: Gray badge, empty progress bar

### Refined

**When**: After the feature enrichment agent processes the feature.

**Characteristics**:
- Detailed enrichment with user stories, acceptance criteria, technical notes
- Based on retrieved signals and research
- Automatically progresses from "discovered" to "refined" after enrichment

**UI**: Blue badge, progress bar 50% filled

### Confirmed

**When**: Consultant manually confirms the feature with client.

**Characteristics**:
- Client has validated the feature
- Evidence of confirmation attached (meeting notes, email, etc.)
- `confirmation_date` timestamp recorded
- Cannot be automatically set - requires manual action

**UI**: Green badge, progress bar 100% filled, confirmation evidence displayed

## Database Schema

```sql
ALTER TABLE features
ADD COLUMN lifecycle_stage TEXT DEFAULT 'discovered',
ADD COLUMN confirmed_evidence JSONB DEFAULT '[]'::jsonb,
ADD COLUMN confirmation_date TIMESTAMPTZ;

ALTER TABLE features
ADD CONSTRAINT features_lifecycle_check
  CHECK (lifecycle_stage IN ('discovered', 'refined', 'confirmed'));
```

## Automatic Progression

### Discovered → Refined

Triggered automatically in `enrich_features_graph.py` after enrichment:

```python
# After persisting enrichment
update_feature_lifecycle(
    feature_id=feature_id,
    lifecycle_stage="refined",
)
```

### Refined → Confirmed

Requires manual API call with evidence:

```python
update_feature_lifecycle(
    feature_id=feature_id,
    lifecycle_stage="confirmed",
    confirmed_evidence=[
        {
            "type": "meeting",
            "date": "2025-01-15",
            "note": "Confirmed in client sync",
            "attendees": ["client@example.com", "consultant@example.com"]
        }
    ]
)
```

## UI Component

### FeatureLifecycleView

Interactive progress bar showing three stages:

```tsx
<FeatureLifecycleView
  feature={feature}
  onUpdateLifecycle={handleUpdateLifecycle}
  readonly={false}
/>
```

**Features**:
- Visual progress bar with three segments
- Clickable stages (can only move forward, not backward)
- Evidence input modal for "confirmed" stage
- Loading states during updates
- Readonly mode for view-only contexts

**Interaction**:
1. Click "refined" stage → Progress immediately
2. Click "confirmed" stage → Opens evidence input modal
3. Submit evidence → Updates lifecycle and closes modal

### Evidence Input Modal

When confirming a feature, consultants provide:
- Evidence type (meeting, email, document, verbal)
- Date of confirmation
- Notes/context
- Attendees (for meetings)

## API Endpoints

### Update Feature Lifecycle

```
PATCH /v1/features/{feature_id}/lifecycle
```

**Request Body**:
```json
{
  "lifecycle_stage": "confirmed",
  "confirmed_evidence": [
    {
      "type": "meeting",
      "date": "2025-01-15",
      "note": "Client approved during sprint planning",
      "attendees": ["client@example.com"]
    }
  ]
}
```

**Response**:
```json
{
  "feature_id": "uuid",
  "lifecycle_stage": "confirmed",
  "message": "Feature lifecycle updated to confirmed"
}
```

### List Features by Lifecycle

```
GET /v1/projects/{project_id}/features-by-lifecycle?lifecycle_stage=confirmed
```

**Response**:
```json
{
  "features": [...],
  "total": 5
}
```

## Filtering and Reporting

### Filter Features by Stage

Use the lifecycle filter in the features view:

```tsx
const confirmedFeatures = features.filter(f => f.lifecycle_stage === 'confirmed')
const refinedFeatures = features.filter(f => f.lifecycle_stage === 'refined')
const discoveredFeatures = features.filter(f => f.lifecycle_stage === 'discovered')
```

### Progress Metrics

Track project progress:
- **Discovery Rate**: New features discovered per week
- **Refinement Rate**: Features enriched per day
- **Confirmation Rate**: % of refined features confirmed
- **Cycle Time**: Average time from discovered → confirmed

## Best Practices

### For Consultants

1. **Review Discoveries**: Regularly review newly discovered features
2. **Enrich Promptly**: Run enrichment agent to move features to refined stage
3. **Confirm with Evidence**: Always provide detailed evidence when confirming
4. **Track Confirmations**: Use confirmed features list for implementation planning

### For AI Agents

1. **Reconciliation**: Always create features in "discovered" stage
2. **Enrichment**: Automatically progress to "refined" after successful enrichment
3. **Never Auto-Confirm**: Confirmation requires human validation

## Workflow Example

### Typical Feature Journey

```
Day 1: Reconciliation Agent
├─ Create feature "User Authentication"
├─ lifecycle_stage = "discovered"
└─ Basic description from signals

Day 2: Feature Enrichment
├─ Enrich with user stories, acceptance criteria
├─ Auto-progress: lifecycle_stage = "refined"
└─ Show in consultant review queue

Day 5: Client Meeting
├─ Consultant presents feature
├─ Client approves
└─ Consultant confirms:
    ├─ lifecycle_stage = "confirmed"
    ├─ confirmation_date = "2025-01-20"
    └─ confirmed_evidence = [meeting details]

Day 6: Implementation Planning
└─ Confirmed feature moves to engineering backlog
```

## Error Handling

### Invalid Stage Transitions

Attempting to skip stages or move backward throws an error:

```python
# Invalid: discovered → confirmed (skips refined)
# Valid: discovered → refined → confirmed
```

### Missing Evidence

Attempting to confirm without evidence shows validation error:

```
"Confirmation requires evidence. Please provide meeting notes, email reference, or other documentation."
```

## Future Enhancements

- Bulk lifecycle updates
- Automatic confirmation from calendar integration
- Lifecycle stage change notifications
- Visual timeline showing stage progression
- Workflow automation (e.g., auto-enrich new discoveries)
