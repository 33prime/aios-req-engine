-- Extend entity_dependencies for link intelligence.
-- Drops restrictive CHECK constraints to support all entity types.
-- Adds enrichment, embedding reference, supersession, and update tracking.

-- ══════════════════════════════════════════════════════════
-- Drop restrictive CHECK constraints
-- These only allowed 5 source types and 5 target types.
-- New entity types (business_driver, workflow, data_entity,
-- constraint, competitor, outcome, outcome_capability) need
-- to participate in the graph.
-- ══════════════════════════════════════════════════════════

ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_source_entity_type_check;
ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_target_entity_type_check;
ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_dependency_type_check;

-- ══════════════════════════════════════════════════════════
-- Add link intelligence columns
-- ══════════════════════════════════════════════════════════

-- Enrichment data (mechanism, hypothetical questions, failure mode)
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS enrichment JSONB DEFAULT '{}';

-- Enrichment status for async processing
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending'
    CHECK (enrichment_status IN ('pending', 'enriched', 'skipped'));

-- Supersession: when a new link replaces a conflicting one
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS superseded_by UUID
    REFERENCES entity_dependencies(id) ON DELETE SET NULL;
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS supersession_reason TEXT;

-- Update tracking: how many times this link has been reinforced
ALTER TABLE entity_dependencies ADD COLUMN IF NOT EXISTS update_count INTEGER DEFAULT 1;

-- ══════════════════════════════════════════════════════════
-- Indexes for new columns
-- ══════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_entity_deps_superseded ON entity_dependencies(superseded_by)
    WHERE superseded_by IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_entity_deps_enrichment_status ON entity_dependencies(enrichment_status)
    WHERE enrichment_status = 'pending';
