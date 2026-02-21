-- Migration 0152: Extend enrichment_revisions entity_type for solution_flow_step
-- Enables change tracking (Q&A resolutions, field updates, escalations) on solution flow steps.

ALTER TABLE enrichment_revisions
  DROP CONSTRAINT IF EXISTS enrichment_revisions_entity_type_check;

ALTER TABLE enrichment_revisions
  ADD CONSTRAINT enrichment_revisions_entity_type_check
  CHECK (entity_type IN (
    'prd_section','vp_step','feature','persona',
    'business_driver','competitor_reference','stakeholder','risk','strategic_context',
    'vision','constraint','data_entity',
    'solution_flow_step'
  ));
