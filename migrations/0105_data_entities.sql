-- Migration 0105: Data Entities + Workflow Step Junction
-- Adds data_entities table for tracking domain data objects,
-- and data_entity_workflow_steps junction for CRUD mapping.

-- ============================================================================
-- 1. data_entities table
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.data_entities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT DEFAULT '',
  entity_category TEXT DEFAULT 'domain',
  fields JSONB DEFAULT '[]'::jsonb,
  source TEXT DEFAULT 'ai_generated',
  confirmation_status TEXT DEFAULT 'ai_generated',
  evidence JSONB DEFAULT '[]'::jsonb,
  version INT DEFAULT 1,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE data_entities ADD CONSTRAINT data_entities_category_check
  CHECK (entity_category IN ('domain', 'reference', 'transactional', 'system'));

ALTER TABLE data_entities ADD CONSTRAINT data_entities_confirmation_status_check
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'confirmed_client', 'needs_client'));

CREATE INDEX idx_data_entities_project ON data_entities(project_id);

-- ============================================================================
-- 2. data_entity_workflow_steps junction table
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.data_entity_workflow_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  data_entity_id UUID NOT NULL REFERENCES data_entities(id) ON DELETE CASCADE,
  vp_step_id UUID NOT NULL REFERENCES vp_steps(id) ON DELETE CASCADE,
  operation_type TEXT NOT NULL CHECK (operation_type IN ('create', 'read', 'update', 'delete', 'validate', 'notify', 'transfer')),
  description TEXT DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(data_entity_id, vp_step_id, operation_type)
);

CREATE INDEX idx_dews_data_entity ON data_entity_workflow_steps(data_entity_id);
CREATE INDEX idx_dews_vp_step ON data_entity_workflow_steps(vp_step_id);

-- ============================================================================
-- 3. RLS + triggers
-- ============================================================================

ALTER TABLE data_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE data_entity_workflow_steps ENABLE ROW LEVEL SECURITY;

CREATE TRIGGER trg_data_entities_updated_at
  BEFORE UPDATE ON data_entities
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 4. Extend signal_impact entity_type check to include data_entity
-- ============================================================================

ALTER TABLE signal_impact DROP CONSTRAINT IF EXISTS signal_impact_entity_type_check;
ALTER TABLE signal_impact ADD CONSTRAINT signal_impact_entity_type_check
  CHECK (entity_type IN ('prd_section', 'vp_step', 'feature', 'insight', 'persona', 'data_entity'));
