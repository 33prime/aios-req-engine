-- Migration: Universal Confirmation Status Model
-- Description: Add confirmation tracking to all entities (features, vp_steps, prd_sections)
-- Date: 2025-12-25
-- Phase: 0 - Foundation

-- =========================
-- Add confirmation columns to features
-- =========================
ALTER TABLE features
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
ADD COLUMN IF NOT EXISTS confirmed_by UUID,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

-- Index for filtering by confirmation status
CREATE INDEX IF NOT EXISTS idx_features_confirmation_status
  ON features(project_id, confirmation_status);

-- Index for confirmed features
CREATE INDEX IF NOT EXISTS idx_features_confirmed_by
  ON features(confirmed_by, confirmed_at DESC) WHERE confirmed_by IS NOT NULL;

-- Comments
COMMENT ON COLUMN features.confirmation_status IS
  'Confirmation workflow status: ai_generated (default) → confirmed_consultant → needs_client → confirmed_client';
COMMENT ON COLUMN features.confirmed_by IS
  'User UUID who confirmed this feature';
COMMENT ON COLUMN features.confirmed_at IS
  'Timestamp when confirmation status was last updated';

-- =========================
-- Add confirmation columns to vp_steps
-- =========================
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
ADD COLUMN IF NOT EXISTS confirmed_by UUID,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

-- Add sort_order for flexible VP step ordering (allows inserts between steps)
ALTER TABLE vp_steps
ADD COLUMN IF NOT EXISTS sort_order NUMERIC;

-- Backfill sort_order based on step_index (10, 20, 30, ...)
UPDATE vp_steps SET sort_order = step_index * 10 WHERE sort_order IS NULL;

-- Make sort_order NOT NULL after backfill
ALTER TABLE vp_steps
ALTER COLUMN sort_order SET NOT NULL;

-- Index for filtering by confirmation status
CREATE INDEX IF NOT EXISTS idx_vp_steps_confirmation_status
  ON vp_steps(project_id, confirmation_status);

-- Index for confirmed VP steps
CREATE INDEX IF NOT EXISTS idx_vp_steps_confirmed_by
  ON vp_steps(confirmed_by, confirmed_at DESC) WHERE confirmed_by IS NOT NULL;

-- Index for sort_order (used for ordering steps)
CREATE INDEX IF NOT EXISTS idx_vp_steps_sort_order
  ON vp_steps(project_id, sort_order);

-- Comments
COMMENT ON COLUMN vp_steps.confirmation_status IS
  'Confirmation workflow status: ai_generated → confirmed_consultant → needs_client → confirmed_client';
COMMENT ON COLUMN vp_steps.confirmed_by IS
  'User UUID who confirmed this VP step';
COMMENT ON COLUMN vp_steps.confirmed_at IS
  'Timestamp when confirmation status was last updated';
COMMENT ON COLUMN vp_steps.sort_order IS
  'Numeric sort order (e.g., 10, 20, 30) allowing inserts between steps (e.g., 25)';

-- =========================
-- Add confirmation columns to prd_sections
-- =========================
ALTER TABLE prd_sections
ADD COLUMN IF NOT EXISTS confirmation_status TEXT DEFAULT 'ai_generated'
  CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
ADD COLUMN IF NOT EXISTS confirmed_by UUID,
ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

-- Index for filtering by confirmation status
CREATE INDEX IF NOT EXISTS idx_prd_sections_confirmation_status
  ON prd_sections(project_id, confirmation_status);

-- Index for confirmed sections
CREATE INDEX IF NOT EXISTS idx_prd_sections_confirmed_by
  ON prd_sections(confirmed_by, confirmed_at DESC) WHERE confirmed_by IS NOT NULL;

-- Comments
COMMENT ON COLUMN prd_sections.confirmation_status IS
  'Confirmation workflow status: ai_generated → confirmed_consultant → needs_client → confirmed_client';
COMMENT ON COLUMN prd_sections.confirmed_by IS
  'User UUID who confirmed this PRD section';
COMMENT ON COLUMN prd_sections.confirmed_at IS
  'Timestamp when confirmation status was last updated';

-- =========================
-- Note on relationship with existing lifecycle_stage
-- =========================
-- Features table has both lifecycle_stage and confirmation_status:
--   lifecycle_stage: tracks enrichment progression (discovered → refined → confirmed)
--   confirmation_status: tracks approval workflow (ai_generated → confirmed_consultant → needs_client → confirmed_client)
-- These are complementary concepts:
--   - A feature can be "refined" (lifecycle) but still "ai_generated" (confirmation)
--   - A feature can be "confirmed" (lifecycle) and "confirmed_client" (confirmation)
