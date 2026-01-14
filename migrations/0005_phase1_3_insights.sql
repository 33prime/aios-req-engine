-- migrations/0005_phase1_3_insights.sql
-- Phase 1.3: Insights table for red-team findings

-- =========================
-- insights: red-team findings with status tracking
-- =========================
create table if not exists public.insights (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  run_id uuid not null,
  job_id uuid null references public.jobs(id) on delete set null,

  status text not null default 'open',
  severity text not null,
  category text not null,
  title text not null,
  finding text not null,
  why text not null,

  suggested_action text not null,
  targets jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  source jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Indexes for common query patterns
create index if not exists idx_insights_project_created 
  on public.insights(project_id, created_at desc);
create index if not exists idx_insights_project_status 
  on public.insights(project_id, status);
create index if not exists idx_insights_run_id 
  on public.insights(run_id);

-- Trigger for updated_at (reuses function from 0004)
drop trigger if exists trg_insights_updated_at on public.insights;
create trigger trg_insights_updated_at
  before update on public.insights
  for each row
  execute function public.update_updated_at_column();

-- Comments
comment on table public.insights is 
  'Red-team findings with status tracking (open|queued|applied|dismissed)';
comment on column public.insights.status is 
  'Status: open (new), queued (pending action), applied (implemented), dismissed (rejected)';
comment on column public.insights.severity is 
  'Severity: minor, important, critical';
comment on column public.insights.category is 
  'Category: logic, ux, security, data, reporting, scope, ops';
comment on column public.insights.suggested_action is 
  'Action type: apply_internally or needs_confirmation';
comment on column public.insights.targets is 
  'Target entities: [{kind, id, label}, ...]';
comment on column public.insights.evidence is 
  'Evidence refs: [{chunk_id, excerpt, rationale}, ...] (min 1)';
comment on column public.insights.source is 
  'Source metadata: {agent, model, prompt_version, schema_version}';




