-- migrations/0008_phase2d_project_state_build.sql
-- Phase 2D: Add last_state_built_at to project_state table

-- Add column for tracking when build state was last run
alter table public.project_state
add column if not exists last_state_built_at timestamptz null;

-- Add comment
comment on column public.project_state.last_state_built_at is 'Timestamp when build state was last run to create initial canonical state';
