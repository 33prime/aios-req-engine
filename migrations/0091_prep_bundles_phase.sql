-- Migration: Add phase column to discovery_prep_bundles
-- This enables stage-aware prep generation for different collaboration phases

-- Add phase column to discovery_prep_bundles
ALTER TABLE discovery_prep_bundles
ADD COLUMN IF NOT EXISTS phase VARCHAR(50) DEFAULT 'pre_discovery';

-- Add touchpoint link (optional - links bundle to a specific touchpoint)
ALTER TABLE discovery_prep_bundles
ADD COLUMN IF NOT EXISTS touchpoint_id UUID REFERENCES collaboration_touchpoints(id) ON DELETE SET NULL;

-- Create index for efficient lookup by phase
CREATE INDEX IF NOT EXISTS idx_prep_bundles_phase ON discovery_prep_bundles(project_id, phase);

-- Create index for touchpoint link
CREATE INDEX IF NOT EXISTS idx_prep_bundles_touchpoint ON discovery_prep_bundles(touchpoint_id);

-- Add comment for documentation
COMMENT ON COLUMN discovery_prep_bundles.phase IS 'Collaboration phase this prep bundle was generated for (pre_discovery, validation, prototype, etc.)';
COMMENT ON COLUMN discovery_prep_bundles.touchpoint_id IS 'Optional link to a specific collaboration touchpoint';
