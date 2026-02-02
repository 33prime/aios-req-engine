# Database Schema

**Last Updated:** 2026-01-30  
**Database:** Supabase (PostgreSQL + pgvector)

## Overview

AIOS Req Engine uses Supabase PostgreSQL with pgvector extension for semantic search. The schema follows a relational model with approximately 40 tables organized into logical domains.

## Core Tables

### Projects & Organizations

**projects**
- `id` (uuid, pk)
- `name` (text)
- `description` (text)
- `status` (text) - active, archived, completed
- `prd_mode` (text) - initial, enriched, finalized
- `stage` (text) - discovery, requirements, design, build
- `created_by` (uuid, fk → users)
- `client_name` (text)
- `portal_enabled` (boolean)
- `portal_phase` (text)
- `cached_readiness_score` (float) - 0-1 readiness percentage
- `cached_readiness_data` (jsonb) - Full readiness breakdown
- `status_narrative` (jsonb) - AI-generated project summary
- `tags` (text[])
- `created_at`, `updated_at` (timestamptz)

**organizations**
- `id` (uuid, pk)
- `name` (text)
- `slug` (text, unique)
- `settings` (jsonb)
- `created_at`, `updated_at` (timestamptz)

**organization_members**
- `id` (uuid, pk)
- `organization_id` (uuid, fk → organizations)
- `user_id` (uuid, fk → users)
- `role` (text) - owner, admin, member
- `joined_at` (timestamptz)

**project_members**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `user_id` (uuid, fk → users)
- `role` (text) - owner, editor, viewer
- `joined_at` (timestamptz)

### Strategic Foundation Entities

**personas**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `name` (text)
- `description` (text)
- `goals` (text[])
- `pain_points` (text[])
- `motivations` (text[])
- `behaviors` (text[])
- `evidence` (jsonb[]) - Array of {chunk_id, quote, source}
- `confidence_score` (float) - 0-1
- `created_at`, `updated_at` (timestamptz)

**features**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `name` (text)
- `description` (text)
- `user_story` (text)
- `acceptance_criteria` (text[])
- `priority` (text) - critical, high, medium, low
- `is_mvp` (boolean)
- `evidence` (jsonb[])
- `target_personas` (uuid[]) - Array of persona_ids
- `confidence_score` (float)
- `created_at`, `updated_at` (timestamptz)

**vp_steps**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `sequence` (int)
- `label` (text) - Step name
- `rationale` (text)
- `pain_inverted` (text)
- `value_delivered` (text)
- `evidence` (jsonb[])
- `feature_refs` (uuid[]) - Features that enable this step
- `created_at`, `updated_at` (timestamptz)

**business_drivers**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `title` (text)
- `description` (text)
- `driver_type` (text) - goal, kpi, constraint
- `target_value` (text)
- `current_value` (text)
- `measurement_method` (text)
- `priority` (text)
- `evidence` (jsonb[])
- `created_at`, `updated_at` (timestamptz)

**stakeholders**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `name` (text)
- `role` (text)
- `influence_level` (text) - low, medium, high
- `involvement_level` (text)
- `concerns` (text[])
- `goals` (text[])
- `evidence` (jsonb[])
- `created_at`, `updated_at` (timestamptz)

**risks**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `title` (text)
- `description` (text)
- `severity` (text) - low, medium, high, critical
- `likelihood` (text) - unlikely, possible, likely, certain
- `category` (text) - technical, business, organizational
- `mitigation_strategy` (text)
- `evidence` (jsonb[])
- `created_at`, `updated_at` (timestamptz)

### Signal Processing

**signals**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `signal_type` (text) - email, transcript, file, note, research
- `source` (text) - Source identifier
- `source_label` (text) - Human-readable name
- `raw_text` (text)
- `metadata` (jsonb) - Extensible metadata
- `run_id` (uuid) - LangGraph run identifier
- `created_at` (timestamptz)

**signal_chunks**
- `id` (uuid, pk)
- `signal_id` (uuid, fk → signals)
- `content` (text)
- `chunk_index` (int)
- `metadata` (jsonb) - {chunk_type, doc_type, authority, etc}
- `embedding` (vector(1536)) - Voyage AI embedding
- `created_at` (timestamptz)

**facts**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `claim` (text)
- `claim_type` (text) - user_pain, feature_request, constraint
- `authority` (text) - client, stakeholder, consultant
- `chunk_id` (uuid, fk → signal_chunks)
- `confidence` (float)
- `created_at` (timestamptz)

### Foundation & Gates

**project_foundation**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects, unique)
- `core_pain` (jsonb) - {statement, confidence, trigger, stakes}
- `primary_persona` (jsonb) - {name, role, confidence}
- `wow_moment` (jsonb) - {description, trigger_event, confidence}
- `design_preferences` (jsonb) - User preferences
- `business_case` (jsonb) - ROI, KPIs, value
- `budget_constraints` (jsonb) - Budget, timeline, constraints
- `confirmed_scope` (jsonb) - Finalized scope
- `created_at`, `updated_at` (timestamptz)

**project_gates**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects, unique)
- `baseline_ready` (boolean) - Research features enabled
- `foundation_ready` (boolean) - Core foundation complete
- `solution_ready` (boolean) - Solution defined
- `prototype_ready` (boolean) - Ready for prototype
- `build_ready` (boolean) - Ready for build
- `gate_details` (jsonb) - Detailed gate status
- `updated_at` (timestamptz)

### Memory & Intelligence

**project_memory**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects, unique)
- `content` (text) - Synthesized memory document (markdown)
- `decisions` (jsonb[]) - Key decisions
- `learnings` (jsonb[]) - Insights and learnings
- `open_questions` (jsonb[]) - Unresolved questions
- `tokens_estimate` (int)
- `last_updated_by` (text) - consultant, ai
- `last_compacted_at` (timestamptz)
- `compaction_count` (int)
- `updated_at` (timestamptz)

**memory_graph**
Knowledge graph for beliefs and facts.

- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `node_type` (text) - fact, belief, insight
- `content` (text)
- `confidence` (float)
- `source_type` (text) - signal, inference
- `evidence_refs` (uuid[]) - chunk_ids
- `metadata` (jsonb)
- `is_active` (boolean)
- `created_at`, `updated_at` (timestamptz)

**memory_edges**
Relationships between memory nodes.

- `id` (uuid, pk)
- `from_node_id` (uuid, fk → memory_graph)
- `to_node_id` (uuid, fk → memory_graph)
- `edge_type` (text) - supports, contradicts, derives_from
- `strength` (float) - 0-1
- `created_at` (timestamptz)

**memory_history**
Change tracking for beliefs.

- `id` (uuid, pk)
- `node_id` (uuid, fk → memory_graph)
- `change_type` (text) - created, updated, superseded
- `old_content` (text)
- `new_content` (text)
- `reason` (text)
- `changed_at` (timestamptz)

### AI Agents & Jobs

**agent_runs**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `agent_type` (text) - di_agent, research_agent, etc
- `input_data` (jsonb)
- `output_data` (jsonb)
- `status` (text) - running, completed, failed
- `error_message` (text)
- `started_at`, `completed_at` (timestamptz)

**di_logs**
DI Agent reasoning logs.

- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `trigger` (text)
- `trigger_context` (text)
- `observation` (text)
- `thinking` (text)
- `decision` (text)
- `action_type` (text)
- `tools_called` (jsonb[])
- `gates_affected` (text[])
- `readiness_before`, `readiness_after` (int)
- `success` (boolean)
- `error_message` (text)
- `created_at` (timestamptz)

**di_cache**
DI Agent analysis cache.

- `id` (uuid, pk)
- `project_id` (uuid, fk → projects, unique)
- `cache_data` (jsonb) - Cached analysis
- `is_stale` (boolean)
- `stale_reason` (text)
- `cached_at` (timestamptz)

**jobs**
Background job tracking.

- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `job_type` (text) - onboarding, research, enrichment
- `status` (text) - pending, running, completed, failed
- `input_json` (jsonb)
- `output_json` (jsonb)
- `error_message` (text)
- `run_id` (uuid)
- `created_at`, `started_at`, `completed_at` (timestamptz)

### Workflows & Deliverables

**creative_briefs**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `content` (jsonb) - Structured brief
- `status` (text)
- `generated_by` (text)
- `created_at`, `updated_at` (timestamptz)

**proposals**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `proposal_type` (text) - sow, rfp_response, etc
- `content` (jsonb)
- `status` (text)
- `generated_by` (text)
- `created_at`, `updated_at` (timestamptz)

**meetings**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `title` (text)
- `meeting_type` (text)
- `scheduled_at` (timestamptz)
- `attendees` (text[])
- `agenda` (jsonb)
- `notes` (text)
- `action_items` (jsonb[])
- `created_at`, `updated_at` (timestamptz)

**tasks**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `title` (text)
- `description` (text)
- `status` (text) - todo, in_progress, blocked, done
- `priority` (text)
- `assigned_to` (uuid, fk → users)
- `due_date` (date)
- `completed_at` (timestamptz)
- `created_at`, `updated_at` (timestamptz)

### Users & Auth

**users**
(Managed by Supabase Auth)
- `id` (uuid, pk)
- `email` (text, unique)
- `created_at`, `updated_at` (timestamptz)

**profiles**
- `id` (uuid, pk)
- `user_id` (uuid, fk → users, unique)
- `first_name` (text)
- `last_name` (text)
- `photo_url` (text)
- `bio` (text)
- `updated_at` (timestamptz)

### Documents

**document_uploads**
- `id` (uuid, pk)
- `project_id` (uuid, fk → projects)
- `filename` (text)
- `file_path` (text) - Supabase Storage path
- `file_size` (bigint)
- `mime_type` (text)
- `upload_status` (text) - pending, processing, completed, failed
- `processing_status` (text)
- `metadata` (jsonb)
- `uploaded_by` (uuid, fk → users)
- `created_at`, `updated_at` (timestamptz)

## Indexes

Key indexes for performance:

- `signals(project_id, created_at)` - Signal timeline queries
- `signal_chunks(signal_id)` - Chunk lookups
- `signal_chunks USING ivfflat (embedding vector_cosine_ops)` - Vector similarity
- `facts(project_id)` - Fact queries
- `personas(project_id)` - Entity queries
- `features(project_id)` - Entity queries
- `memory_graph(project_id, is_active)` - Active nodes
- `memory_edges(from_node_id)`, `memory_edges(to_node_id)` - Graph traversal

## Row Level Security (RLS)

Supabase RLS policies enforce:
- Users can only see projects they're members of
- Organization members can see organization data
- Signals/chunks/facts inherit project permissions
- Admin users have broader access

## Migrations

Migrations stored in `/migrations` directory. Applied via Supabase CLI or direct SQL.

Current migration status: ~50 migrations applied.

## Vector Embeddings

**Embedding Model:** Voyage AI (voyage-2, 1536 dimensions)

**Indexed Tables:**
- `signal_chunks.embedding` - For RAG queries

**Search Strategy:**
- Hybrid search: Vector similarity + keyword matching
- Contextual chunking for better retrieval

## Data Retention

- Soft deletes (is_deleted flag) for most entities
- Hard deletes for GDPR compliance on user request
- Signal/chunk data retained indefinitely for audit trail

---

**Schema Version:** 1.0  
**Last Migration:** 2026-01-25
