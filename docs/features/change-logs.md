# Change Logs and Enrichment Revisions

## Overview

The enrichment revision system tracks the evolution of PRD sections, VP steps, and features as they are enriched over time. This provides transparency into how AI-generated content changes and what new information influenced each enrichment.

## How It Works

### Revision Tracking

Every time an entity (PRD section, VP step, or feature) is enriched:

1. **Count New Signals**: The system counts how many new signals have been added since the last enrichment
2. **Create Revision Record**: A new revision record is created in the `enrichment_revisions` table
3. **Snapshot Data**: The enrichment data is stored as a snapshot for historical reference
4. **Context Summary**: A human-readable summary is generated (e.g., "Based on 5 new signals")

### Revision Types

- **created**: Initial creation of the entity
- **enriched**: Entity was enriched with new information
- **updated**: Manual update by user

### Database Schema

```sql
CREATE TABLE enrichment_revisions (
  id UUID PRIMARY KEY,
  project_id UUID NOT NULL,
  entity_type TEXT NOT NULL, -- 'prd_section' | 'vp_step' | 'feature'
  entity_id UUID NOT NULL,
  entity_label TEXT NOT NULL,
  revision_type TEXT NOT NULL,
  trigger_event TEXT,
  snapshot JSONB DEFAULT '{}'::jsonb,
  new_signals_count INT DEFAULT 0,
  new_facts_count INT DEFAULT 0,
  context_summary TEXT,
  run_id UUID,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## UI Components

### Change Log Timeline

The `ChangeLogTimeline` component displays a vertical timeline of revisions with:

- Revision badges showing the type (created, enriched, updated)
- Context summary ("Based on 5 new signals since last enrichment")
- Relative timestamps ("2 hours ago", "yesterday")
- Expandable details showing what changed

**Location**: Displayed below enrichment content in PRD, VP, and Feature detail views

### Enrichment Context Badge

The `EnrichmentContext` component shows a compact badge with:

- Icon indicator
- "Based on X new signals since [date]"
- Displayed inline with enrichment content

## API Endpoints

### List Entity Revisions

```
GET /v1/state/{entity_type}/{entity_id}/revisions
```

**Parameters**:
- `entity_type`: One of `prd_section`, `vp_step`, `feature`
- `entity_id`: UUID of the entity
- `limit`: Maximum number of revisions to return (default: 50, max: 100)

**Response**:
```json
{
  "revisions": [
    {
      "id": "uuid",
      "entity_type": "prd_section",
      "entity_id": "uuid",
      "entity_label": "personas",
      "revision_type": "enriched",
      "new_signals_count": 5,
      "context_summary": "Based on 5 new signals",
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

## Configuration

Control revision tracking with the `ENABLE_ENRICHMENT_REVISIONS` setting:

```python
# In .env
ENABLE_ENRICHMENT_REVISIONS=true  # Default: true
```

## Error Handling

Revision tracking is non-blocking. If revision creation fails, the enrichment process continues successfully and a warning is logged.

## Performance Considerations

- Revisions are limited to the last 50 by default to prevent excessive data transfer
- Indexed by `(entity_type, entity_id, created_at DESC)` for fast queries
- Consider archiving revisions older than 90 days for long-running projects

## Future Enhancements

- Diff view showing exact changes between revisions
- Rollback capability to restore previous versions
- Revision annotations and comments
- Export revision history to PDF/Markdown
