# Confirmation Workflow Evolution

## Current State

Every AI-extracted entity goes through confirmation:
```
ai_generated → confirmed_consultant → needs_client → confirmed_client
```

UI shows status via badges:
- Gray: AI Draft
- Teal: Confirmed (consultant)
- Green: Client Confirmed
- Yellow: Needs Review

Actions available:
- Single confirm: Click on entity
- Batch confirm: "Confirm All" per section
- Needs review: Flag for client

## Original Assumptions

1. Consultants need to validate ALL AI outputs before sharing
2. Two-stage confirmation (consultant → client) provides quality gates
3. Evidence visibility gives confidence to confirm
4. Confirmation status should be visible everywhere

## Evolution Timeline

### 2026-02-06 - Added Batch Confirmation for BRD Canvas

**Trigger**: BRD Canvas has many items per section; one-by-one is tedious

**Before**:
- Single entity confirmation only
- Click entity → confirm button

**After**:
- `POST /confirmations/batch` endpoint
- "Confirm All" button on each BRD section header
- Optimistic UI update (instant feedback)

**Learning**: TBD

**Evidence**: Commit cafb36b

**Assumptions to Validate**:
- [ ] Consultants use batch confirm frequently
- [ ] Batch confirm doesn't lead to rubber-stamping
- [ ] Section-level granularity is right (not too broad, not too narrow)

### 2026-01-XX - Confirmation Queue System

**Trigger**: Need structured way to track what needs validation

**Before**: Implicit status on entities

**After**:
- `confirmation_items` table
- Confirmation queue modal in Collaboration Panel
- Each item has: kind, title, why, ask, suggested_method
- Filter by status: open, queued, resolved, dismissed

**Learning**:
- Queue provides clear "what's next" guidance
- "Why" and "Ask" fields help consultants explain to clients

### 2026-01-XX - Evidence Attribution

**Trigger**: Consultants asked "where did this come from?"

**Before**: Features had no source tracing

**After**:
- `evidence` JSONB array on all entities
- Each evidence item: `{chunk_id, excerpt, source_type, rationale}`
- `EvidenceBlock` component shows citations
- Field-level attribution via `field_attributions` table

**Learning**:
- Evidence visibility dramatically increases confidence
- Consultants show evidence to clients to build trust

---

## Open Questions

1. Is two-stage (consultant → client) the right flow?
2. Should some entities auto-confirm based on evidence quality?
3. Is "Needs Review" used or do consultants just skip?
4. Do batch confirms lead to lower quality reviews?

## Related Features

- CF-001 to CF-004 (Confirmation)
- EV-001 to EV-006 (Evidence)
- BRD-011 (Confirm All)
