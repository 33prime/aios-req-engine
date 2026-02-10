-- Migration: 0104_workflow_current_future_state.sql
-- Description: Add workflows table + current/future state columns on vp_steps
-- Date: 2026-02-10
--
-- Adds a "workflows" wrapper table that groups vp_steps into named workflows
-- with current vs future state pairing, time/pain/benefit fields for ROI,
-- and side-by-side comparison support.

-- ============================================================================
-- Part 1: Create workflows table
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  owner TEXT,                              -- persona name or team
  state_type TEXT NOT NULL DEFAULT 'future',
  paired_workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL,
  -- ROI fields
  frequency_per_week NUMERIC DEFAULT 0,
  hourly_rate NUMERIC DEFAULT 0,
  -- Metadata
  source TEXT DEFAULT 'manual',
  confirmation_status TEXT DEFAULT 'ai_generated',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Constraints
ALTER TABLE workflows ADD CONSTRAINT workflows_state_type_check
  CHECK (state_type IN ('current', 'future'));

ALTER TABLE workflows ADD CONSTRAINT workflows_source_check
  CHECK (source IN ('manual', 'signal_extracted', 'ai_generated'));

ALTER TABLE workflows ADD CONSTRAINT workflows_confirmation_status_check
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'confirmed_client', 'needs_client'));

-- Indexes
CREATE INDEX IF NOT EXISTS idx_workflows_project ON workflows(project_id);
CREATE INDEX IF NOT EXISTS idx_workflows_paired ON workflows(paired_workflow_id) WHERE paired_workflow_id IS NOT NULL;

-- ============================================================================
-- Part 2: Extend vp_steps with workflow FK + current/future state columns
-- ============================================================================

ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS workflow_id UUID REFERENCES workflows(id) ON DELETE SET NULL;
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS time_minutes NUMERIC;
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS pain_description TEXT;
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS benefit_description TEXT;
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS automation_level TEXT DEFAULT 'manual';
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS operation_type TEXT;

-- Constraints on new columns
ALTER TABLE vp_steps ADD CONSTRAINT vp_steps_automation_level_check
  CHECK (automation_level IN ('manual', 'semi_automated', 'fully_automated'));

ALTER TABLE vp_steps ADD CONSTRAINT vp_steps_operation_type_check
  CHECK (operation_type IS NULL OR operation_type IN ('create', 'read', 'update', 'delete', 'validate', 'notify', 'transfer'));

CREATE INDEX IF NOT EXISTS idx_vp_steps_workflow ON vp_steps(workflow_id) WHERE workflow_id IS NOT NULL;

-- ============================================================================
-- Part 3: Handle unique constraint for multi-workflow step indexes
-- ============================================================================

-- Drop old unique constraint that blocks multiple workflows at same step_index
ALTER TABLE vp_steps DROP CONSTRAINT IF EXISTS vp_steps_project_id_step_index_key;

-- Steps without a workflow keep the old uniqueness
CREATE UNIQUE INDEX IF NOT EXISTS uq_vp_steps_legacy
  ON vp_steps(project_id, step_index) WHERE workflow_id IS NULL;

-- Steps with a workflow are unique per workflow
CREATE UNIQUE INDEX IF NOT EXISTS uq_vp_steps_workflow
  ON vp_steps(workflow_id, step_index) WHERE workflow_id IS NOT NULL;

-- ============================================================================
-- Part 4: RLS + triggers
-- ============================================================================

ALTER TABLE workflows ENABLE ROW LEVEL SECURITY;

DROP TRIGGER IF EXISTS trg_workflows_updated_at ON workflows;
CREATE TRIGGER trg_workflows_updated_at
  BEFORE UPDATE ON workflows
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
