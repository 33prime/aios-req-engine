-- Add new stage values to projects table
-- Extends existing stage column to support full lifecycle

-- Drop existing constraint if any
ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_stage_check;

-- Add new constraint with all 6 stages
ALTER TABLE projects ADD CONSTRAINT projects_stage_check
  CHECK (stage IN ('discovery', 'validation', 'prototype', 'proposal', 'build', 'live'));

-- Update comment
COMMENT ON COLUMN projects.stage IS 'Project lifecycle stage: discovery, validation, prototype, proposal, build, live';

-- Note: prototype_refinement is deprecated, map to validation in app code
