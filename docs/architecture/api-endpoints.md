# API Endpoints Reference

**Last Updated:** 2026-01-30

This document provides an overview of all FastAPI endpoints in the AIOS Req Engine. For detailed request/response schemas, see the OpenAPI spec at `/docs` when running the server.

## Endpoint Categories

### Projects (`/v1/projects`)
Core project lifecycle management.

- `GET /projects` - List all projects with filtering
- `POST /projects` - Create new project (with optional auto-ingestion)
- `GET /projects/{project_id}` - Get project details
- `PATCH /projects/{project_id}` - Update project metadata
- `DELETE /projects/{project_id}` - Archive project

**Project State & Readiness:**
- `GET /projects/{project_id}/baseline` - Get baseline status
- `PATCH /projects/{project_id}/baseline` - Update baseline config
- `POST /projects/{project_id}/readiness/refresh` - Refresh readiness score
- `POST /projects/readiness/refresh-all` - Bulk refresh all projects

**Project Memory:**
- `GET /projects/{project_id}/memory` - Get project memory
- `POST /projects/{project_id}/memory/{memory_type}` - Add decision/learning/question
- `POST /projects/{project_id}/memory/synthesize` - Regenerate memory with LLM
- `GET /projects/{project_id}/memory/content` - Get full memory document
- `POST /projects/{project_id}/memory/compact` - Compress memory (auto at 2000 tokens)
- `GET /projects/{project_id}/memory/unified` - Get unified memory (cached)
- `POST /projects/{project_id}/memory/unified/refresh` - Force re-synthesis
- `GET /projects/{project_id}/memory/visualize` - Get graph visualization data
- `GET /projects/{project_id}/memory/belief-history` - Get belief change history

**Research & Evidence:**
- `GET /projects/{project_id}/research/chunks` - Get recent research chunks
- `GET /projects/{project_id}/research/evidence-stats` - Get evidence statistics
- `GET /projects/{project_id}/research/gaps` - Get entities lacking evidence
- `GET /projects/{project_id}/research/sources` - Get all signal sources

### DI Agent (`/v1/di-agent`)
Design Intelligence Agent for foundation building.

**Agent Invocation:**
- `POST /projects/{project_id}/di-agent/invoke` - Invoke DI Agent
- `GET /projects/{project_id}/di-agent/logs` - Get agent reasoning logs
- `POST /projects/{project_id}/di-cache/invalidate` - Invalidate cache

**Foundation Management:**
- `GET /projects/{project_id}/foundation` - Get complete foundation
- `POST /projects/{project_id}/foundation/extract-core-pain` - Extract core pain
- `POST /projects/{project_id}/foundation/extract-primary-persona` - Extract primary persona
- `POST /projects/{project_id}/foundation/identify-wow-moment` - Identify wow moment
- `POST /projects/{project_id}/foundation/extract-business-case` - Extract business case
- `POST /projects/{project_id}/foundation/extract-budget-constraints` - Extract constraints

**Gap Analysis:**
- `GET /projects/{project_id}/gaps/analyze` - Analyze all gaps
- `GET /projects/{project_id}/gaps/requirements` - Analyze requirements gaps
- `POST /projects/{project_id}/gaps/suggest-fixes` - Generate fix suggestions

### Signals (`/v1/signals`)
Signal and chunk management.

- `GET /signals/{signal_id}` - Get signal details
- `GET /signals/{signal_id}/chunks` - Get signal chunks
- `GET /signals/{signal_id}/impact` - Get signal impact
- `GET /projects/{project_id}/signals` - List project signals
- `GET /projects/{project_id}/sources/usage` - Get source usage stats

### Document Processing (`/v1/documents`)
Document upload and processing.

- `POST /projects/{project_id}/documents/upload` - Upload document
- `GET /projects/{project_id}/documents` - List project documents
- `GET /projects/{project_id}/documents/{doc_id}` - Get document details
- `DELETE /projects/{project_id}/documents/{doc_id}` - Delete document
- `POST /projects/{project_id}/documents/{doc_id}/process` - Reprocess document
- `POST /projects/{project_id}/documents/{doc_id}/withdraw` - Withdraw document

### Chat (`/v1/chat`)
AI assistant chat interface.

- `POST /projects/{project_id}/chat` - Send chat message (streaming)
- `GET /projects/{project_id}/chat/history` - Get chat history
- `DELETE /projects/{project_id}/chat/history` - Clear chat history

### Analytics (`/v1/analytics`)
Project analytics and metrics.

- `GET /projects/{project_id}/analytics/overview` - Get analytics dashboard
- `GET /projects/{project_id}/analytics/timeline` - Get activity timeline
- `GET /projects/{project_id}/analytics/signal-types` - Signal type distribution
- `GET /projects/{project_id}/analytics/entity-coverage` - Entity coverage metrics

### Research (`/v1/research`)
Research agent and pipeline.

- `POST /projects/{project_id}/research/run` - Run research query
- `GET /projects/{project_id}/research/jobs` - List research jobs
- `GET /projects/{project_id}/research/jobs/{job_id}` - Get job status
- `POST /projects/{project_id}/research/ingest` - Ingest research results

### Entities
Strategic foundation entities.

**Personas** (`/v1/personas`)
- `GET /projects/{project_id}/personas` - List personas
- `POST /projects/{project_id}/personas` - Create persona
- `PATCH /projects/{project_id}/personas/{persona_id}` - Update persona
- `DELETE /projects/{project_id}/personas/{persona_id}` - Delete persona
- `POST /projects/{project_id}/personas/enrich` - Enrich all personas

**Features** (`/v1/features`)
- `GET /projects/{project_id}/features` - List features
- `POST /projects/{project_id}/features` - Create feature
- `PATCH /projects/{project_id}/features/{feature_id}` - Update feature
- `DELETE /projects/{project_id}/features/{feature_id}` - Delete feature
- `POST /projects/{project_id}/features/enrich` - Enrich all features

**Value Proposition** (`/v1/vp`)
- `GET /projects/{project_id}/vp` - Get value proposition
- `POST /projects/{project_id}/vp/generate` - Generate VP
- `PATCH /projects/{project_id}/vp/steps/{step_id}` - Update VP step

**Business Drivers** (`/v1/business-drivers`)
- `GET /projects/{project_id}/business-drivers` - List business drivers
- `POST /projects/{project_id}/business-drivers` - Create business driver
- `PATCH /projects/{project_id}/business-drivers/{id}` - Update business driver
- `DELETE /projects/{project_id}/business-drivers/{id}` - Delete business driver

**Stakeholders** (`/v1/stakeholders`)
- `GET /projects/{project_id}/stakeholders` - List stakeholders
- `POST /projects/{project_id}/stakeholders` - Create stakeholder
- `PATCH /projects/{project_id}/stakeholders/{id}` - Update stakeholder
- `DELETE /projects/{project_id}/stakeholders/{id}` - Delete stakeholder

**Risks** (`/v1/risks`)
- `GET /projects/{project_id}/risks` - List risks
- `POST /projects/{project_id}/risks` - Create risk
- `PATCH /projects/{project_id}/risks/{id}` - Update risk
- `DELETE /projects/{project_id}/risks/{id}` - Delete risk

### Workflows
Pre-built workflow templates.

**Creative Briefs** (`/v1/creative-briefs`)
- `POST /projects/{project_id}/creative-briefs/generate` - Generate creative brief
- `GET /projects/{project_id}/creative-briefs` - List briefs

**Proposals** (`/v1/proposals`)
- `POST /projects/{project_id}/proposals/generate` - Generate proposal
- `GET /projects/{project_id}/proposals` - List proposals

**Meetings** (`/v1/meetings`)
- `POST /projects/{project_id}/meetings/agendas/generate` - Generate meeting agenda
- `GET /projects/{project_id}/meetings` - List meetings

**Discovery Prep** (`/v1/discovery-prep`)
- `POST /projects/{project_id}/discovery-prep/questions` - Generate discovery questions
- `POST /projects/{project_id}/discovery-prep/agenda` - Generate discovery agenda
- `POST /projects/{project_id}/discovery-prep/briefing` - Generate prep briefing

### Client Portal (`/v1/client-portal`)
Client-facing endpoints.

- `GET /client-portal/projects/{project_id}` - Get client view
- `POST /client-portal/projects/{project_id}/feedback` - Submit feedback
- `GET /client-portal/projects/{project_id}/deliverables` - List deliverables

### Organizations (`/v1/organizations`)
Multi-tenancy and team management.

- `GET /organizations` - List user's organizations
- `POST /organizations` - Create organization
- `GET /organizations/{org_id}` - Get organization details
- `GET /organizations/{org_id}/members` - List members
- `POST /organizations/{org_id}/invite` - Invite member
- `DELETE /organizations/{org_id}/members/{user_id}` - Remove member

### Tasks (`/v1/tasks`)
Task management and tracking.

- `GET /projects/{project_id}/tasks` - List project tasks
- `POST /projects/{project_id}/tasks` - Create task
- `PATCH /projects/{project_id}/tasks/{task_id}` - Update task
- `DELETE /projects/{project_id}/tasks/{task_id}` - Delete task
- `POST /projects/{project_id}/tasks/{task_id}/complete` - Mark complete

### Jobs (`/v1/jobs`)
Background job monitoring.

- `GET /jobs/{job_id}` - Get job status
- `GET /projects/{project_id}/jobs` - List project jobs
- `POST /jobs/{job_id}/cancel` - Cancel running job

### State Management (`/v1/state`)
Project state snapshots.

- `GET /projects/{project_id}/state` - Get current state snapshot
- `POST /projects/{project_id}/state/rebuild` - Rebuild state snapshot
- `GET /projects/{project_id}/state/history` - Get state change history

### Admin (`/v1/admin`)
Administrative operations.

- `POST /admin/sync-profiles` - Sync user profiles from Supabase Auth
- `GET /admin/stats` - Get system-wide statistics
- `POST /admin/cleanup-orphans` - Clean orphaned data

## Authentication

All endpoints (except `/health`) require authentication via Supabase JWT token in the `Authorization` header:

```
Authorization: Bearer <supabase_jwt_token>
```

The `user_id` is extracted from the JWT and used for permission checks.

## Common Query Parameters

- `limit` (default: 50, max: 100) - Maximum results to return
- `offset` (default: 0) - Pagination offset
- `search` - Text search query
- `status` - Filter by status (active, archived, completed, all)

## Response Formats

### Success Response
```json
{
  "data": {...},
  "message": "Success"
}
```

### Error Response
```json
{
  "detail": "Error message",
  "status_code": 404
}
```

### Streaming Response (Chat)
```
data: {"type": "text", "content": "Hello"}
data: {"type": "done"}
```

## Rate Limiting

- LLM operations: Rate limited by API provider
- Database operations: Connection pool limited
- No explicit rate limits on endpoints (trust-based)

## Versioning

API is versioned via path prefix: `/v1/...`

Future versions will be introduced as `/v2/...` with backward compatibility maintained for v1.

---

**Note:** This document is auto-generated and may not reflect all endpoints. For the most up-to-date reference, visit `/docs` on the running API server for interactive OpenAPI documentation.
