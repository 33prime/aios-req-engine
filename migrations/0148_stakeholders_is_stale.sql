-- Add is_stale tracking to stakeholders table
-- (matches pattern from features, personas, vp_steps, data_entities)
ALTER TABLE stakeholders
  ADD COLUMN IF NOT EXISTS is_stale boolean DEFAULT false,
  ADD COLUMN IF NOT EXISTS stale_reason text,
  ADD COLUMN IF NOT EXISTS stale_since timestamptz;
