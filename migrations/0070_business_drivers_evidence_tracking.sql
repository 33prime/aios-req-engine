-- Migration: Business Drivers Evidence and Tracking Fields
-- Description: Add evidence attribution, version tracking, and enrichment status to business_drivers
-- Date: 2026-01-25
-- Part of: Strategic Foundation Entity Enhancement (Phase 1, Task #1)

-- =========================
-- Add evidence attribution fields
-- =========================

-- Evidence array: links to signal chunks with attribution
ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS evidence JSONB DEFAULT '[]'::jsonb;

-- Multiple source signals (replaces single source_signal_id for new records)
-- Keep source_signal_id for backwards compatibility
ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}'::uuid[];

-- =========================
-- Add version tracking
-- =========================

ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS created_by TEXT DEFAULT 'system'
    CHECK (created_by IN ('system', 'consultant', 'client', 'di_agent'));

-- =========================
-- Add enrichment tracking
-- =========================

ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'none'
    CHECK (enrichment_status IN ('none', 'pending', 'enriched', 'failed')),
ADD COLUMN IF NOT EXISTS enrichment_attempted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS enrichment_error TEXT;

-- =========================
-- Indexes for common queries
-- =========================

-- Query by enrichment status to find entities needing enrichment
CREATE INDEX IF NOT EXISTS idx_business_drivers_enrichment_status
    ON business_drivers(project_id, enrichment_status);

-- Query by version for change tracking
CREATE INDEX IF NOT EXISTS idx_business_drivers_version
    ON business_drivers(project_id, version DESC);

-- Query by created_by for attribution
CREATE INDEX IF NOT EXISTS idx_business_drivers_created_by
    ON business_drivers(project_id, created_by);

-- GIN index for evidence JSONB queries (finding entities linked to specific signals)
CREATE INDEX IF NOT EXISTS idx_business_drivers_evidence
    ON business_drivers USING gin(evidence);

-- =========================
-- Comments
-- =========================

COMMENT ON COLUMN business_drivers.evidence IS 'Array of evidence objects: [{"signal_id": "...", "chunk_id": "...", "text": "...", "confidence": 0.95}]';
COMMENT ON COLUMN business_drivers.source_signal_ids IS 'Array of signal IDs that contributed to this driver (replaces source_signal_id for multi-signal attribution)';
COMMENT ON COLUMN business_drivers.version IS 'Version number, incremented on each update for change tracking';
COMMENT ON COLUMN business_drivers.created_by IS 'Who created this entity: system (auto-extract), consultant, client, di_agent';
COMMENT ON COLUMN business_drivers.enrichment_status IS 'Enrichment state: none (not enriched), pending (queued), enriched (complete), failed (error)';
COMMENT ON COLUMN business_drivers.enrichment_attempted_at IS 'Timestamp of last enrichment attempt';
COMMENT ON COLUMN business_drivers.enrichment_error IS 'Error message if enrichment failed';

-- =========================
-- Data migration for existing records
-- =========================

-- Backfill source_signal_ids from source_signal_id for existing records
UPDATE business_drivers
SET source_signal_ids = ARRAY[source_signal_id]
WHERE source_signal_id IS NOT NULL
  AND source_signal_ids = '{}'::uuid[];

-- Set version = 1 for all existing records (already default, but explicit)
-- Set created_by = 'system' for all existing records (already default, but explicit)

-- =========================
-- Validation
-- =========================

-- Ensure evidence is always a valid JSON array
-- (Constraint enforced at application layer for performance)
