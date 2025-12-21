-- migrations/0004_phase1_3_project_gates.sql
-- Phase 1.3: Baseline gate for controlling research ingestion and red-team

-- =========================
-- Generic updated_at trigger function (reusable)
-- =========================
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- =========================
-- project_gates: baseline gate configuration per project
-- =========================
create table if not exists public.project_gates (
  project_id uuid primary key,
  baseline_ready boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Index for listing by recently updated
create index if not exists idx_project_gates_updated_at
  on public.project_gates(updated_at desc);

-- Trigger for updated_at
drop trigger if exists trg_project_gates_updated_at on public.project_gates;
create trigger trg_project_gates_updated_at
  before update on public.project_gates
  for each row
  execute function public.update_updated_at_column();

-- Comments
comment on table public.project_gates is
  'Baseline gate configuration per project for controlling research access';
comment on column public.project_gates.baseline_ready is
  'Whether research features are enabled for this project';

