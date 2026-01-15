-- Add cached_readiness_data column to store full readiness breakdown
-- This allows instant display of dimensions, recommendations, and stats

ALTER TABLE projects
ADD COLUMN IF NOT EXISTS cached_readiness_data JSONB DEFAULT NULL;

COMMENT ON COLUMN projects.cached_readiness_data IS 'Full cached readiness data (dimensions, caps, recommendations, stats) for instant frontend display';
