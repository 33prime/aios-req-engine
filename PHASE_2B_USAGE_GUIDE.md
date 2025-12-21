# Phase 2B Usage Guide

## Quick Start

Phase 2B adds three main capabilities:
1. **State Reconciliation**: Automatically update canonical state (PRD/VP/Features) from new signals
2. **Confirmation Queue**: Track items that need client validation
3. **Outreach Drafts**: Generate batched email or meeting messages

## API Endpoints

### 1. Reconcile State

**Endpoint:** `POST /v1/state/reconcile`

**When to use:** After ingesting new signals or extracting facts

**Request:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000",
  "include_research": true,
  "top_k_context": 24
}
```

**Parameters:**
- `project_id` (required): Project UUID
- `include_research` (optional, default: true): Include RAG context chunks
- `top_k_context` (optional, default: 24): Number of context chunks to retrieve

**Response:**
```json
{
  "run_id": "...",
  "job_id": "...",
  "changed_counts": {
    "prd_sections_updated": 2,
    "vp_steps_updated": 1,
    "features_updated": 3,
    "confirmations_created": 2
  },
  "confirmations_open_count": 2,
  "summary": "Reconciled 2 PRD sections, 1 VP step, 3 features"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/v1/state/reconcile \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000",
    "include_research": true,
    "top_k_context": 24
  }'
```

### 2. List Confirmations

**Endpoint:** `GET /v1/confirmations`

**When to use:** To display the "Next Steps" tab or confirmation queue

**Query Parameters:**
- `project_id` (required): Project UUID
- `status` (optional): Filter by status (open, queued, resolved, dismissed)

**Response:**
```json
{
  "confirmations": [
    {
      "id": "...",
      "project_id": "...",
      "kind": "prd",
      "key": "prd:constraints:ai_boundary",
      "title": "AI boundary clarification",
      "why": "Need to understand scope",
      "ask": "What AI features are in scope?",
      "status": "open",
      "suggested_method": "meeting",
      "priority": "high",
      "evidence": [...],
      "created_from": {...},
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl "http://localhost:8000/v1/confirmations?project_id=550e8400-e29b-41d4-a716-446655440000&status=open"
```

### 3. Get Single Confirmation

**Endpoint:** `GET /v1/confirmations/{confirmation_id}`

**When to use:** To display details of a specific confirmation item

**Example:**
```bash
curl http://localhost:8000/v1/confirmations/550e8400-e29b-41d4-a716-446655440001
```

### 4. Update Confirmation Status

**Endpoint:** `PATCH /v1/confirmations/{confirmation_id}/status`

**When to use:** When client confirms or dismisses an item

**Request:**
```json
{
  "status": "resolved",
  "resolution_evidence": {
    "type": "email",
    "ref": "Email from client on 2024-01-01",
    "note": "Client confirmed via email"
  }
}
```

**Status Values:**
- `open`: New, not yet addressed
- `queued`: Batched for outreach
- `resolved`: Client confirmed
- `dismissed`: Not needed

**Resolution Evidence Types:**
- `email`: Email confirmation
- `call`: Phone call
- `doc`: Document reference
- `meeting`: Meeting confirmation

**Example:**
```bash
curl -X PATCH http://localhost:8000/v1/confirmations/550e8400-e29b-41d4-a716-446655440001/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_evidence": {
      "type": "email",
      "ref": "Email from client on 2024-01-01",
      "note": "Client confirmed via email"
    }
  }'
```

### 5. Generate Outreach Draft

**Endpoint:** `POST /v1/outreach/draft`

**When to use:** To generate a batched email or meeting message for open confirmations

**Request:**
```json
{
  "project_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "recommended_method": "email",
  "reason": "Items can be addressed asynchronously",
  "goal": "Confirm 2 requirement(s) with client to ensure alignment",
  "needs": [
    {
      "key": "prd:constraints:1",
      "title": "Clarify constraint",
      "ask": "What is the constraint?",
      "priority": "low"
    }
  ],
  "subject": "Quick clarifications needed (2 items)",
  "message": "Hi [Client Name],\n\nAs we continue refining the requirements, I have a few quick clarifications that would help us move forward:\n\n1. Clarify constraint\n   What is the constraint?\n\nCould you provide your input on these points? Feel free to reply inline or let me know if you'd prefer to discuss synchronously.\n\nThanks,\n[Your Name]"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/v1/outreach/draft \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

## Typical Workflow

### 1. Initial Setup
```bash
# 1. Create project
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project"}'

# 2. Ingest client signals
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "...",
    "signal_type": "email",
    "source": "client@example.com",
    "text": "We need a user authentication system..."
  }'

# 3. Extract facts
curl -X POST http://localhost:8000/agents/extract-facts \
  -H "Content-Type: application/json" \
  -d '{"signal_id": "..."}'
```

### 2. Reconcile State
```bash
# After extracting facts, reconcile canonical state
curl -X POST http://localhost:8000/v1/state/reconcile \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "...",
    "include_research": true,
    "top_k_context": 24
  }'
```

### 3. Review Confirmations
```bash
# List open confirmations
curl "http://localhost:8000/v1/confirmations?project_id=...&status=open"
```

### 4. Generate Outreach
```bash
# Generate email or meeting draft
curl -X POST http://localhost:8000/v1/outreach/draft \
  -H "Content-Type: application/json" \
  -d '{"project_id": "..."}'
```

### 5. Mark Resolved
```bash
# After client confirms, mark as resolved
curl -X PATCH http://localhost:8000/v1/confirmations/{id}/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "resolved",
    "resolution_evidence": {
      "type": "email",
      "ref": "Email from client on 2024-01-01",
      "note": "Client confirmed via email"
    }
  }'
```

## Idempotency

Reconciliation is idempotent:
- First call: Processes new facts/insights, creates confirmations
- Second call (no new inputs): Returns "No new inputs to reconcile"
- Third call (after new signal): Only processes new inputs since last checkpoint

**Checkpoint tracking:**
- `last_reconciled_at`: Timestamp of last reconciliation
- `last_extracted_facts_id`: Last processed fact extraction
- `last_insight_id`: Last processed insight
- `last_signal_id`: Last processed signal

## Outreach Decision Logic

**Meeting recommended if:**
- ≥3 open confirmation items, OR
- Any item has `priority: "high"`, OR
- Keywords detected: threshold, alignment, decision rights, strategy, budget, timeline, scope change

**Email recommended otherwise**

## Best Practices

### 1. Reconcile Regularly
Run reconciliation after:
- Ingesting new signals
- Extracting facts
- Running red-team analysis
- Adding research documents

### 2. Batch Confirmations
- Let confirmations accumulate (2-5 items)
- Generate single outreach message
- Avoid bombarding client with individual questions

### 3. Track Resolution Evidence
Always include resolution evidence when marking resolved:
```json
{
  "status": "resolved",
  "resolution_evidence": {
    "type": "email",
    "ref": "Email from Jane Doe on 2024-01-15",
    "note": "Confirmed Python 3.10+ is acceptable"
  }
}
```

### 4. Use Status Transitions
- `open` → `queued`: When batching for outreach
- `queued` → `resolved`: After client confirms
- `open/queued` → `dismissed`: If no longer needed

### 5. Monitor Confirmation Queue
- Check open count regularly
- Generate outreach when ≥3 items or weekly
- Don't let confirmations go stale

## Error Handling

### Reconciliation Errors
```json
{
  "detail": "State reconciliation failed: Model output could not be validated to schema"
}
```
**Solution:** Check logs for LLM output validation errors. May need to adjust prompt or retry.

### No Confirmations Found
```json
{
  "detail": "No open confirmation items found for this project"
}
```
**Solution:** This is expected if all items are resolved or dismissed. Run reconciliation to create new ones.

### Confirmation Not Found
```json
{
  "detail": "Confirmation item {id} not found"
}
```
**Solution:** Verify the confirmation ID is correct and belongs to the project.

## Database Schema

### Confirmation Item Fields
- `id`: UUID (primary key)
- `project_id`: UUID (foreign key)
- `kind`: prd | vp | feature | insight | gate
- `target_table`: Optional reference table
- `target_id`: Optional reference ID
- `key`: Stable unique key (e.g., "prd:constraints:ai_boundary")
- `title`: Short title
- `why`: Why this needs confirmation
- `ask`: What we're asking
- `status`: open | queued | resolved | dismissed
- `suggested_method`: email | meeting
- `priority`: low | medium | high
- `evidence`: JSONB array of EvidenceRef
- `created_from`: JSONB with run_id, job_id, source_signal_ids
- `resolution_evidence`: JSONB (optional)
- `resolved_at`: Timestamp (optional)
- `created_at`: Timestamp
- `updated_at`: Timestamp

### Project State Fields
- `project_id`: UUID (primary key)
- `last_reconciled_at`: Timestamp
- `last_extracted_facts_id`: UUID
- `last_insight_id`: UUID
- `last_signal_id`: UUID
- `updated_at`: Timestamp

## Testing

Run Phase 2B tests:
```bash
pytest tests/test_project_state_checkpoint_mock.py \
       tests/test_confirmations_db_mock.py \
       tests/test_reconcile_parsing.py \
       tests/test_reconcile_prompt_inputs_mock.py \
       tests/test_reconcile_agent_mock.py \
       tests/test_outreach_draft_logic.py -v
```

All tests are mocked (no real DB or LLM calls).

## Troubleshooting

### Reconciliation not creating confirmations
- Check if new facts/insights exist since last checkpoint
- Verify LLM output includes `confirmation_items` array
- Check logs for validation errors

### Outreach draft always recommends meeting
- Check confirmation priorities (high priority → meeting)
- Check confirmation titles/why for strategic keywords
- Reduce number of open confirmations if batching too many

### Confirmations not showing in UI
- Verify project_id is correct
- Check status filter (default to "open")
- Ensure reconciliation completed successfully

## Support

For issues or questions:
1. Check logs: `tail -f logs/app.log`
2. Review state revisions: Query `state_revisions` table
3. Check project state: Query `project_state` table
4. Verify confirmation items: Query `confirmation_items` table

