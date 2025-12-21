-- migrations/0006_phase2a_canonical_state.sql
-- Phase 2A: Canonical PRD sections, Value Path steps, and Features tables

-- =========================
-- prd_sections: PRD tab sections (personas, key_features, happy_path, constraints, etc.)
-- =========================
create table if not exists public.prd_sections (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  slug text not null,
  label text not null,
  required boolean not null default false,
  status text not null default 'draft',
  fields jsonb not null default '{}'::jsonb,
  client_needs jsonb not null default '[]'::jsonb,
  sources jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(project_id, slug)
);

-- Indexes for common query patterns
create index if not exists idx_prd_sections_project_slug 
  on public.prd_sections(project_id, slug);
create index if not exists idx_prd_sections_project_updated 
  on public.prd_sections(project_id, updated_at desc);

-- Trigger for updated_at
drop trigger if exists trg_prd_sections_updated_at on public.prd_sections;
create trigger trg_prd_sections_updated_at
  before update on public.prd_sections
  for each row
  execute function public.update_updated_at_column();

-- Comments
comment on table public.prd_sections is 
  'PRD tab sections with structured fields and evidence tracking';
comment on column public.prd_sections.slug is 
  'Section identifier (e.g., personas, key_features, happy_path, constraints)';
comment on column public.prd_sections.status is 
  'Status: draft, confirmed_consultant, needs_confirmation, confirmed_client';
comment on column public.prd_sections.fields is 
  'Section-specific fields (textarea content, structured data)';
comment on column public.prd_sections.client_needs is 
  'List of client needs: [{key, title, why, ask}]';
comment on column public.prd_sections.evidence is 
  'Evidence references: [{chunk_id, excerpt, rationale}]';

-- =========================
-- vp_steps: Value Path workflow steps
-- =========================
create table if not exists public.vp_steps (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  step_index int not null,
  label text not null,
  status text not null default 'draft',
  description text not null default '',
  user_benefit_pain text not null default '',
  ui_overview text not null default '',
  value_created text not null default '',
  kpi_impact text not null default '',
  needed jsonb not null default '[]'::jsonb,
  sources jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(project_id, step_index)
);

-- Indexes for common query patterns
create index if not exists idx_vp_steps_project_index 
  on public.vp_steps(project_id, step_index);
create index if not exists idx_vp_steps_project_updated 
  on public.vp_steps(project_id, updated_at desc);

-- Trigger for updated_at
drop trigger if exists trg_vp_steps_updated_at on public.vp_steps;
create trigger trg_vp_steps_updated_at
  before update on public.vp_steps
  for each row
  execute function public.update_updated_at_column();

-- Comments
comment on table public.vp_steps is 
  'Value Path workflow steps with user benefits and KPI tracking';
comment on column public.vp_steps.step_index is 
  'Step number in the workflow (1..N)';
comment on column public.vp_steps.status is 
  'Status: draft, confirmed_consultant, needs_confirmation, confirmed_client';
comment on column public.vp_steps.needed is 
  'List of needed items: [{key, title, why, ask}]';
comment on column public.vp_steps.evidence is 
  'Evidence references: [{chunk_id, excerpt, rationale}]';

-- =========================
-- features: Key Features list
-- =========================
create table if not exists public.features (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  name text not null,
  category text not null default 'General',
  is_mvp boolean not null default true,
  confidence text not null default 'medium',
  status text not null default 'draft',
  evidence jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Indexes for common query patterns
create index if not exists idx_features_project_created 
  on public.features(project_id, created_at desc);
create index if not exists idx_features_project_status 
  on public.features(project_id, status);

-- Trigger for updated_at
drop trigger if exists trg_features_updated_at on public.features;
create trigger trg_features_updated_at
  before update on public.features
  for each row
  execute function public.update_updated_at_column();

-- Comments
comment on table public.features is 
  'Key Features list with MVP flags and confidence levels';
comment on column public.features.confidence is 
  'Confidence level: low, medium, high';
comment on column public.features.status is 
  'Status: draft, confirmed_consultant, needs_confirmation, confirmed_client';
comment on column public.features.evidence is 
  'Evidence references: [{chunk_id, excerpt, rationale}]';

