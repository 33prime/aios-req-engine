-- Migration 0121: Data entity intelligence columns
-- Part of Living BRD Panels feature

ALTER TABLE data_entities
  ADD COLUMN IF NOT EXISTS enrichment_data JSONB,
  ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'pending'
    CHECK (enrichment_status IN ('pending', 'enriched', 'failed')),
  ADD COLUMN IF NOT EXISTS enrichment_attempted_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS pii_flags JSONB DEFAULT '[]'::jsonb,
  ADD COLUMN IF NOT EXISTS relationships JSONB DEFAULT '[]'::jsonb;
