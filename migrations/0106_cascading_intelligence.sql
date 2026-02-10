-- Migration 0106: Cascading Intelligence
-- Extends data_entities with staleness tracking, and
-- extends entity_dependencies CHECK constraints to include data_entity.

-- ============================================================================
-- 1. Add staleness columns to data_entities
-- ============================================================================

ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT FALSE;
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS stale_reason TEXT;
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS stale_since TIMESTAMPTZ;

-- ============================================================================
-- 2. Extend entity_dependencies CHECK constraints to include data_entity
-- ============================================================================

ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_source_entity_type_check;
ALTER TABLE entity_dependencies ADD CONSTRAINT entity_dependencies_source_entity_type_check
  CHECK (source_entity_type IN ('persona', 'feature', 'vp_step', 'strategic_context', 'stakeholder', 'data_entity'));

ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_target_entity_type_check;
ALTER TABLE entity_dependencies ADD CONSTRAINT entity_dependencies_target_entity_type_check
  CHECK (target_entity_type IN ('persona', 'feature', 'vp_step', 'signal', 'research_chunk', 'data_entity'));
