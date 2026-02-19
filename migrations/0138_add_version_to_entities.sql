-- Add version column to entity tables that don't have it yet.
-- Tracks how many times an entity has been modified by the signal pipeline.

ALTER TABLE features ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE personas ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
ALTER TABLE constraints ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;
