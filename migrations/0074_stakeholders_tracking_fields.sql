-- Migration: Stakeholders Tracking Fields
-- Description: Add version tracking, enrichment status, and signal attribution to stakeholders
-- Date: 2026-01-25
-- Part of: Strategic Foundation Entity Enhancement (Phase 1, Task #5)

-- =========================
-- Add signal attribution
-- =========================

-- Array of source signals (stakeholders didn't have source_signal_id originally)
ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}'::uuid[];

-- =========================
-- Add version tracking
-- =========================

ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS created_by TEXT DEFAULT 'system'
    CHECK (created_by IN ('system', 'consultant', 'client', 'di_agent'));

-- =========================
-- Add enrichment tracking
-- =========================

ALTER TABLE stakeholders
ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'none'
    CHECK (enrichment_status IN ('none', 'pending', 'enriched', 'failed')),
ADD COLUMN IF NOT EXISTS enrichment_attempted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS enrichment_error TEXT;

-- =========================
-- Indexes for common queries
-- =========================

-- Query by enrichment status to find entities needing enrichment
CREATE INDEX IF NOT EXISTS idx_stakeholders_enrichment_status
    ON stakeholders(project_id, enrichment_status);

-- Query by version for change tracking
CREATE INDEX IF NOT EXISTS idx_stakeholders_version
    ON stakeholders(project_id, version DESC);

-- Query by created_by for attribution
CREATE INDEX IF NOT EXISTS idx_stakeholders_created_by
    ON stakeholders(project_id, created_by);

-- GIN index for evidence JSONB queries (already exists evidence column)
CREATE INDEX IF NOT EXISTS idx_stakeholders_evidence
    ON stakeholders USING gin(evidence);

-- =========================
-- Comments
-- =========================

COMMENT ON COLUMN stakeholders.source_signal_ids IS 'Array of signal IDs that contributed to this stakeholder record';
COMMENT ON COLUMN stakeholders.version IS 'Version number, incremented on each update for change tracking';
COMMENT ON COLUMN stakeholders.created_by IS 'Who created this entity: system (auto-extract), consultant, client, di_agent';
COMMENT ON COLUMN stakeholders.enrichment_status IS 'Enrichment state: none (not enriched), pending (queued), enriched (complete), failed (error)';
COMMENT ON COLUMN stakeholders.enrichment_attempted_at IS 'Timestamp of last enrichment attempt';
COMMENT ON COLUMN stakeholders.enrichment_error IS 'Error message if enrichment failed';

-- =========================
-- Data migration for existing records
-- =========================

-- Set version = 1 for all existing records (already default, but explicit)
-- Set created_by = 'system' for all existing records (already default, but explicit)

-- Note: stakeholders table already has evidence column from 0033_strategic_context.sql
