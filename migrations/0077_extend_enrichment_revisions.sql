-- Migration: Extend Enrichment Revisions for Strategic Foundation Entities
-- Description: Add business_driver, competitor_reference, stakeholder, and risk to enrichment_revisions entity_type
-- Date: 2026-01-25
-- Part of: Strategic Foundation Entity Enhancement (Phase 1, Task #8)

-- =========================
-- Update entity_type constraint to include strategic foundation entities
-- =========================

ALTER TABLE enrichment_revisions
DROP CONSTRAINT IF EXISTS enrichment_revisions_entity_type_check;

ALTER TABLE enrichment_revisions
ADD CONSTRAINT enrichment_revisions_entity_type_check
CHECK (entity_type IN (
    -- Original product entities
    'prd_section',
    'vp_step',
    'feature',
    'persona',
    -- Strategic foundation entities (new)
    'business_driver',
    'competitor_reference',
    'stakeholder',
    'risk',
    'strategic_context'
));

-- =========================
-- Comments
-- =========================

COMMENT ON CONSTRAINT enrichment_revisions_entity_type_check ON enrichment_revisions IS
    'Supported entities: prd_section, vp_step, feature, persona (product); business_driver, competitor_reference, stakeholder, risk, strategic_context (strategic foundation)';

-- =========================
-- Usage notes
-- =========================

-- Strategic foundation entities now support full change tracking via enrichment_revisions:
--
-- Example: Track business_driver changes
-- INSERT INTO enrichment_revisions (
--     project_id,
--     entity_type,
--     entity_id,
--     entity_label,
--     revision_type,
--     changes,
--     source_signal_id,
--     revision_number,
--     diff_summary,
--     created_by
-- ) VALUES (
--     'project-uuid',
--     'business_driver',
--     'driver-uuid',
--     'Reduce checkout time from 5s to 2s',
--     'enriched',
--     '{"baseline_value": {"old": null, "new": "5 seconds"}, "target_value": {"old": null, "new": "2 seconds"}}'::jsonb,
--     'signal-uuid',
--     2,
--     'Added KPI baseline and target values from client interview',
--     'di_agent'
-- );
--
-- Example: Track competitor_reference changes
-- INSERT INTO enrichment_revisions (
--     project_id,
--     entity_type,
--     entity_id,
--     entity_label,
--     revision_type,
--     changes,
--     revision_number,
--     diff_summary,
--     created_by
-- ) VALUES (
--     'project-uuid',
--     'competitor_reference',
--     'comp-uuid',
--     'Acme Corp',
--     'enriched',
--     '{"market_position": {"old": null, "new": "market_leader"}, "pricing_model": {"old": null, "new": "Freemium, $99/mo Pro"}}'::jsonb,
--     1,
--     'Added market position and pricing analysis from web research',
--     'system'
-- );
