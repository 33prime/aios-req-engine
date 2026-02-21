-- Migration 0150: Widen signal_impact entity_type CHECK constraint
-- Adds all V2 entity types that were missing from the original constraint,
-- which caused patch_applicator to silently fail when recording evidence
-- for stakeholders, workflows, data_entities, constraints, competitors, etc.

ALTER TABLE signal_impact DROP CONSTRAINT IF EXISTS signal_impact_entity_type_check;
ALTER TABLE signal_impact ADD CONSTRAINT signal_impact_entity_type_check
  CHECK (entity_type IN (
    'prd_section', 'vp_step', 'feature', 'insight', 'persona', 'data_entity',
    'stakeholder', 'workflow', 'business_driver', 'constraint', 'competitor', 'solution_flow_step'
  ));
