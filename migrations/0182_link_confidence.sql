-- Migration 0182: Add confidence, source, and dispute columns to entity_dependencies
-- Enables semantic link extraction with confidence scoring and link dispute mechanism

ALTER TABLE entity_dependencies
  ADD COLUMN confidence float NOT NULL DEFAULT 0.5,
  ADD COLUMN source text NOT NULL DEFAULT 'co_occurrence',
  ADD COLUMN disputed boolean NOT NULL DEFAULT false,
  ADD COLUMN disputed_at timestamptz;

COMMENT ON COLUMN entity_dependencies.source IS 'co_occurrence | semantic_extraction | consultant | rebuild';
COMMENT ON COLUMN entity_dependencies.confidence IS '0.5=co_occurrence, 0.7=semantic, 1.0=consultant';
