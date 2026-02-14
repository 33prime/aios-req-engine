-- Migration: 0115_business_driver_links.sql
-- Add explicit entity link arrays, vision alignment, relatability score,
-- and staleness tracking to business_drivers table.

-- Explicit link arrays (extracted + consolidated from signals)
ALTER TABLE business_drivers
  ADD COLUMN IF NOT EXISTS linked_persona_ids UUID[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS linked_vp_step_ids UUID[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS linked_feature_ids UUID[] DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS linked_driver_ids UUID[] DEFAULT '{}';

-- Vision alignment assessment (from enrichment)
ALTER TABLE business_drivers
  ADD COLUMN IF NOT EXISTS vision_alignment TEXT
    CHECK (vision_alignment IN ('high', 'medium', 'low', 'unrelated'));

-- Relatability score for sorting (computed on BRD load, cached here)
ALTER TABLE business_drivers
  ADD COLUMN IF NOT EXISTS relatability_score REAL DEFAULT 0.0;

-- Staleness tracking (consistent with other entity tables)
ALTER TABLE business_drivers
  ADD COLUMN IF NOT EXISTS is_stale BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS stale_reason TEXT;

-- Index for sorting by relatability within a project
CREATE INDEX IF NOT EXISTS idx_business_drivers_relatability
  ON business_drivers(project_id, relatability_score DESC);
