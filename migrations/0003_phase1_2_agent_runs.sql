-- migrations/0003_phase1_2_agent_runs.sql
-- Phase 1.2: Agent run logging and replay support

-- =========================
-- agent_runs: audit trail for all agent executions
-- =========================
create table if not exists public.agent_runs (
  id uuid primary key default gen_random_uuid(),
  agent_name text not null,
  project_id uuid null,
  signal_id uuid null,
  run_id uuid not null,
  job_id uuid null references public.jobs(id) on delete set null,
  status text not null default 'queued',
  input jsonb not null default '{}'::jsonb,
  output jsonb not null default '{}'::jsonb,
  error text null,
  started_at timestamptz null,
  completed_at timestamptz null,
  created_at timestamptz not null default now()
);

-- Indexes for common query patterns
create index if not exists idx_agent_runs_run_id on public.agent_runs(run_id);
create index if not exists idx_agent_runs_agent_name_created 
  on public.agent_runs(agent_name, created_at desc);
create index if not exists idx_agent_runs_project_created 
  on public.agent_runs(project_id, created_at desc);
create index if not exists idx_agent_runs_signal_created 
  on public.agent_runs(signal_id, created_at desc);

-- Add helpful comments
comment on table public.agent_runs is 
  'Audit trail for all agent executions with replay capability';
comment on column public.agent_runs.agent_name is 
  'Agent identifier (e.g., extract_facts, reconcile, enrich)';
comment on column public.agent_runs.status is 
  'Execution status: queued, processing, completed, failed';
comment on column public.agent_runs.input is 
  'Safe replay input (identifiers only, no raw prompts)';
comment on column public.agent_runs.output is 
  'Execution output summary (not full results)';
comment on column public.agent_runs.error is 
  'Error message if status=failed';
comment on column public.agent_runs.started_at is 
  'Timestamp when agent execution started';
comment on column public.agent_runs.completed_at is 
  'Timestamp when agent execution completed or failed';




