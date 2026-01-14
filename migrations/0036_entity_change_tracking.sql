-- Migration: Enhanced Entity Change Tracking
-- Description: Add field-level diff tracking to enrichment_revisions
-- Date: 2025-01-06

-- Add changes column for field-level diffs
ALTER TABLE enrichment_revisions
ADD COLUMN IF NOT EXISTS changes JSONB DEFAULT '{}'::jsonb;

-- Add source_signal_id to track which signal triggered the change
ALTER TABLE enrichment_revisions
ADD COLUMN IF NOT EXISTS source_signal_id UUID;

-- Add revision_number for easy ordering per entity
ALTER TABLE enrichment_revisions
ADD COLUMN IF NOT EXISTS revision_number INT DEFAULT 1;

-- Add diff_summary for human-readable change description
ALTER TABLE enrichment_revisions
ADD COLUMN IF NOT EXISTS diff_summary TEXT;

-- Add created_by to track who/what made the change
ALTER TABLE enrichment_revisions
ADD COLUMN IF NOT EXISTS created_by TEXT DEFAULT 'system';

-- Index for signal-based lookups
CREATE INDEX IF NOT EXISTS idx_enrichment_revisions_signal
ON enrichment_revisions(source_signal_id) WHERE source_signal_id IS NOT NULL;

-- Update entity_type constraint to include persona
ALTER TABLE enrichment_revisions
DROP CONSTRAINT IF EXISTS enrichment_revisions_entity_type_check;

ALTER TABLE enrichment_revisions
ADD CONSTRAINT enrichment_revisions_entity_type_check
CHECK (entity_type IN ('prd_section', 'vp_step', 'feature', 'persona'));

-- Comments
COMMENT ON COLUMN enrichment_revisions.changes IS 'Field-level diffs: {field_name: {old: value, new: value}}';
COMMENT ON COLUMN enrichment_revisions.source_signal_id IS 'Signal that triggered this change (if applicable)';
COMMENT ON COLUMN enrichment_revisions.revision_number IS 'Sequential revision number per entity';
COMMENT ON COLUMN enrichment_revisions.diff_summary IS 'Human-readable summary of what changed';
COMMENT ON COLUMN enrichment_revisions.created_by IS 'Who/what created this revision (system, user, agent name)';
