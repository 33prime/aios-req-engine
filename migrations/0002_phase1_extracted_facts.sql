-- migrations/0002_phase1_extracted_facts.sql
-- Phase 1: Extracted facts table for storing LLM-extracted facts with provenance

-- =========================
-- extracted_facts: stores structured facts extracted from signals
-- =========================
create table if not exists public.extracted_facts (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  signal_id uuid not null references public.signals(id) on delete cascade,
  run_id uuid not null,
  job_id uuid null references public.jobs(id) on delete set null,
  model text not null,
  prompt_version text not null,
  schema_version text not null,
  facts jsonb not null,
  summary text null,
  created_at timestamptz not null default now()
);

-- Indexes for common query patterns
create index if not exists idx_extracted_facts_project_id on public.extracted_facts(project_id);
create index if not exists idx_extracted_facts_signal_id on public.extracted_facts(signal_id);
create index if not exists idx_extracted_facts_created_at on public.extracted_facts(created_at desc);

-- Add helpful comments
comment on table public.extracted_facts is 'Structured facts extracted from signals by LLM agents (Phase 1+)';
comment on column public.extracted_facts.facts is 'Full ExtractFactsOutput as JSONB (summary, facts, open_questions, contradictions)';
comment on column public.extracted_facts.summary is 'Redundant copy of summary from facts for easy querying';

