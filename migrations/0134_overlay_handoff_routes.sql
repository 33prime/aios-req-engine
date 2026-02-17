-- Add handoff_routes to prototype_feature_overlays
-- Stores page routes from HANDOFF.md for each feature overlay
ALTER TABLE prototype_feature_overlays
  ADD COLUMN IF NOT EXISTS handoff_routes TEXT[];
