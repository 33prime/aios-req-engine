-- Migration 0120: Vision panel columns + constraints redesign
-- Part of Living BRD Panels feature

-- ============================================================================
-- Vision panel columns on projects
-- ============================================================================

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS vision_analysis JSONB DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS vision_updated_at TIMESTAMPTZ;

-- ============================================================================
-- Extend enrichment_revisions entity_type CHECK for vision/constraint/data_entity
-- ============================================================================

ALTER TABLE enrichment_revisions
  DROP CONSTRAINT IF EXISTS enrichment_revisions_entity_type_check;

ALTER TABLE enrichment_revisions
  ADD CONSTRAINT enrichment_revisions_entity_type_check
  CHECK (entity_type IN (
    'prd_section','vp_step','feature','persona',
    'business_driver','competitor_reference','stakeholder','risk','strategic_context',
    'vision','constraint','data_entity'
  ));

-- ============================================================================
-- Constraints redesign: remap 8 types → 6
-- ============================================================================

-- Drop old check constraint
ALTER TABLE constraints DROP CONSTRAINT IF EXISTS constraints_constraint_type_check;

-- Remap old types to new categories
UPDATE constraints SET constraint_type = 'regulatory'     WHERE constraint_type = 'compliance';
UPDATE constraints SET constraint_type = 'technical'      WHERE constraint_type = 'integration';
UPDATE constraints SET constraint_type = 'budget'         WHERE constraint_type = 'business';
UPDATE constraints SET constraint_type = 'strategic'      WHERE constraint_type IN ('risk', 'kpi');
UPDATE constraints SET constraint_type = 'organizational' WHERE constraint_type = 'assumption';

-- Add new check constraint with 6 categories
ALTER TABLE constraints ADD CONSTRAINT constraints_constraint_type_check
  CHECK (constraint_type IN ('budget', 'timeline', 'regulatory', 'organizational', 'technical', 'strategic'));

-- ============================================================================
-- Constraints new columns
-- ============================================================================

ALTER TABLE constraints
  ADD COLUMN IF NOT EXISTS source TEXT DEFAULT 'extracted'
    CHECK (source IN ('extracted', 'manual', 'ai_inferred')),
  ADD COLUMN IF NOT EXISTS confidence FLOAT,
  ADD COLUMN IF NOT EXISTS linked_data_entity_ids UUID[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS impact_description TEXT;

-- ============================================================================
-- Constraints severity: must_have/should_have/nice_to_have → critical/high/medium/low
-- ============================================================================

ALTER TABLE constraints DROP CONSTRAINT IF EXISTS constraints_severity_check;

UPDATE constraints SET severity = 'critical' WHERE severity = 'must_have';
UPDATE constraints SET severity = 'high'     WHERE severity = 'should_have';
UPDATE constraints SET severity = 'medium'   WHERE severity = 'nice_to_have';

ALTER TABLE constraints ADD CONSTRAINT constraints_severity_check
  CHECK (severity IN ('critical', 'high', 'medium', 'low'));

ALTER TABLE constraints ALTER COLUMN severity SET DEFAULT 'medium';
