-- Migration: Features Lifecycle
-- Description: Add lifecycle tracking columns to features table
-- Date: 2025-12-23

-- Add lifecycle columns
ALTER TABLE features
ADD COLUMN IF NOT EXISTS lifecycle_stage TEXT DEFAULT 'discovered' CHECK (lifecycle_stage IN ('discovered', 'refined', 'confirmed')),
ADD COLUMN IF NOT EXISTS confirmed_evidence JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS confirmation_date TIMESTAMPTZ;

-- Index for lifecycle stage filtering
CREATE INDEX idx_features_lifecycle_stage ON features(project_id, lifecycle_stage);

-- Index for confirmed features
CREATE INDEX idx_features_confirmed ON features(project_id, confirmation_date DESC) WHERE lifecycle_stage = 'confirmed';

-- Comments
COMMENT ON COLUMN features.lifecycle_stage IS 'Feature lifecycle stage: discovered (from reconciliation), refined (after enrichment), confirmed (client approved)';
COMMENT ON COLUMN features.confirmed_evidence IS 'JSONB array of evidence when feature is confirmed by client';
COMMENT ON COLUMN features.confirmation_date IS 'Timestamp when feature was confirmed by client';

-- Lifecycle flow:
-- 1. discovered: Created by reconciliation agent from research
-- 2. refined: Enhanced by enrichment agent with details
-- 3. confirmed: Approved by client/consultant with evidence
