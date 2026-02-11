-- Migration 0110: Add missing stale_since column to vp_steps
--
-- Migration 0032 added is_stale and stale_reason to vp_steps but omitted stale_since.
-- Migration 0034 added all three columns to features, personas, and strategic_context.
-- This brings vp_steps into alignment so cascading intelligence queries work uniformly.

ALTER TABLE vp_steps
  ADD COLUMN IF NOT EXISTS stale_since TIMESTAMPTZ;
