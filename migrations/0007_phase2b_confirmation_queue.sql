-- migrations/0007_phase2b_confirmation_queue.sql
-- Phase 2B: Confirmation queue, project state checkpoints, and state revisions

-- =========================
-- confirmation_items: "Needs confirmation" queue for Next Steps tab
-- =========================
create table if not exists public.confirmation_items (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,

  kind text not null,         -- "prd" | "vp" | "feature" | "insight" | "gate"
  target_table text null,     -- e.g. "prd_sections" | "vp_steps" | "features" | "insights"
  target_id uuid null,        -- id in target table if applicable
  key text not null,          -- stable key e.g. "prd:constraints:ai_boundary"
  title text not null,
  why text not null,
  ask text not null,

  status text not null default 'open',   -- "open" | "queued" | "resolved" | "dismissed"
  suggested_method text not null default 'email', -- "email" | "meeting"
  priority text not null default 'medium', -- "low" | "medium" | "high"

  evidence jsonb not null default '[]'::jsonb,         -- list[EvidenceRef]
  created_from jsonb not null default '{}'::jsonb,     -- {run_id, job_id, source_signal_ids, extracted_facts_ids, insight_ids}

  resolution_evidence jsonb null,        -- {type:"email|call|doc", ref:"...", note:"..."}
  resolved_at timestamptz null,
  updated_at timestamptz not null default now(),
  created_at timestamptz not null default now(),

  unique(project_id, key)
);

-- Indexes for common query patterns
create index if not exists idx_confirmation_items_project_status 
  on public.confirmation_items(project_id, status);
create index if not exists idx_confirmation_items_project_created 
  on public.confirmation_items(project_id, created_at desc);
create index if not exists idx_confirmation_items_target 
  on public.confirmation_items(target_table, target_id);

-- Trigger for updated_at
drop trigger if exists trg_confirmation_items_updated_at on public.confirmation_items;
create trigger trg_confirmation_items_updated_at
  before update on public.confirmation_items
  for each row
  execute function public.update_updated_at_column();

-- Comments
comment on table public.confirmation_items is 
  'Confirmation queue for items that need client validation';
comment on column public.confirmation_items.kind is 
  'Type of confirmation: prd, vp, feature, insight, gate';
comment on column public.confirmation_items.key is 
  'Stable unique key for idempotent upserts (e.g., "prd:constraints:ai_boundary")';
comment on column public.confirmation_items.status is 
  'Status: open (new), queued (batched for outreach), resolved (confirmed), dismissed (rejected)';
comment on column public.confirmation_items.suggested_method is 
  'Suggested outreach method: email or meeting';
comment on column public.confirmation_items.priority is 
  'Priority: low, medium, high';
comment on column public.confirmation_items.evidence is 
  'Evidence references: [{chunk_id, excerpt, rationale}, ...]';
comment on column public.confirmation_items.created_from is 
  'Source tracking: {run_id, job_id, source_signal_ids, extracted_facts_ids, insight_ids}';
comment on column public.confirmation_items.resolution_evidence is 
  'How it was resolved: {type, ref, note}';

-- =========================
-- project_state: Checkpoints for loop prevention and idempotency
-- =========================
create table if not exists public.project_state (
  project_id uuid primary key,
  last_reconciled_at timestamptz null,
  last_extracted_facts_id uuid null,
  last_insight_id uuid null,
  last_signal_id uuid null,
  updated_at timestamptz not null default now()
);

-- Trigger for updated_at
drop trigger if exists trg_project_state_updated_at on public.project_state;
create trigger trg_project_state_updated_at
  before update on public.project_state
  for each row
  execute function public.update_updated_at_column();

-- Comments
comment on table public.project_state is 
  'Project-level checkpoints for reconciliation idempotency';
comment on column public.project_state.last_reconciled_at is 
  'Timestamp of last successful reconciliation run';
comment on column public.project_state.last_extracted_facts_id is 
  'Last processed extracted_facts id to prevent reprocessing';
comment on column public.project_state.last_insight_id is 
  'Last processed insight id to prevent reprocessing';
comment on column public.project_state.last_signal_id is 
  'Last processed signal id to prevent reprocessing';

-- =========================
-- state_revisions: Audit trail of reconciliation diffs
-- =========================
create table if not exists public.state_revisions (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  run_id uuid not null,
  job_id uuid null references public.jobs(id) on delete set null,
  input_summary jsonb not null default '{}'::jsonb,
  diff jsonb not null,
  created_at timestamptz not null default now()
);

-- Indexes for common query patterns
create index if not exists idx_state_revisions_project_created 
  on public.state_revisions(project_id, created_at desc);
create index if not exists idx_state_revisions_run_id 
  on public.state_revisions(run_id);

-- Comments
comment on table public.state_revisions is 
  'Audit trail of state reconciliation changes';
comment on column public.state_revisions.input_summary is 
  'Summary of inputs that triggered reconciliation: {facts_count, insights_count, signals_count}';
comment on column public.state_revisions.diff is 
  'Full ReconcileOutput from LLM for debugging and audit';

