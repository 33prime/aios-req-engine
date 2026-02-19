-- Add source_signal_ids UUID[] to entity tables missing it
-- Enables V2 patch_applicator to link entities back to source signals

ALTER TABLE features ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}';
ALTER TABLE personas ADD COLUMN IF NOT EXISTS evidence JSONB DEFAULT '[]';
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}';
ALTER TABLE constraints ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}';
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS source_signal_ids UUID[] DEFAULT '{}';
