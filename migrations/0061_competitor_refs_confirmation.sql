-- Migration: Competitor References Confirmation Status
-- Description: Add field-level confirmation tracking to competitor_references
-- Date: 2025-01-14

-- =========================
-- Add confirmation fields to competitor_references
-- =========================

ALTER TABLE competitor_references
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
    CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client'));

ALTER TABLE competitor_references
ADD COLUMN IF NOT EXISTS confirmed_fields JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS confirmed_by UUID,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

-- Index for filtering by confirmation status
CREATE INDEX IF NOT EXISTS idx_competitor_refs_confirmation
    ON competitor_references(project_id, confirmation_status);

-- =========================
-- Comments
-- =========================

COMMENT ON COLUMN competitor_references.confirmation_status IS 'Entity-level confirmation: ai_generated, confirmed_consultant, needs_client, confirmed_client';
COMMENT ON COLUMN competitor_references.confirmed_fields IS 'Field-level confirmation tracking: {"name": "confirmed_consultant", "strengths": "ai_generated"}';
COMMENT ON COLUMN competitor_references.confirmed_by IS 'User ID who confirmed this entity';
COMMENT ON COLUMN competitor_references.confirmed_at IS 'Timestamp of last confirmation';
