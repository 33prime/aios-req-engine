-- Migration: Business Drivers Confirmation Status
-- Description: Add field-level confirmation tracking to business_drivers
-- Date: 2025-01-14

-- =========================
-- Add confirmation fields to business_drivers
-- =========================

ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
    CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client'));

ALTER TABLE business_drivers
ADD COLUMN IF NOT EXISTS confirmed_fields JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS confirmed_by UUID,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

-- Index for filtering by confirmation status
CREATE INDEX IF NOT EXISTS idx_business_drivers_confirmation
    ON business_drivers(project_id, confirmation_status);

-- =========================
-- Comments
-- =========================

COMMENT ON COLUMN business_drivers.confirmation_status IS 'Entity-level confirmation: ai_generated, confirmed_consultant, needs_client, confirmed_client';
COMMENT ON COLUMN business_drivers.confirmed_fields IS 'Field-level confirmation tracking: {"description": "confirmed_consultant", "measurement": "ai_generated"}';
COMMENT ON COLUMN business_drivers.confirmed_by IS 'User ID who confirmed this entity';
COMMENT ON COLUMN business_drivers.confirmed_at IS 'Timestamp of last confirmation';
