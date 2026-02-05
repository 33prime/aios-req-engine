-- Migration 0098: BRD Canvas Support
-- Adds vision column to projects and priority_group (MoSCoW) to features

-- Add vision to projects
ALTER TABLE projects ADD COLUMN IF NOT EXISTS vision TEXT;

-- Add MoSCoW priority grouping to features
ALTER TABLE features ADD COLUMN IF NOT EXISTS priority_group TEXT
  CHECK (priority_group IN ('must_have', 'should_have', 'could_have', 'out_of_scope'));

-- Backfill: is_mvp=true → must_have, else → should_have
UPDATE features SET priority_group = CASE
  WHEN is_mvp = true THEN 'must_have' ELSE 'should_have'
END WHERE priority_group IS NULL;

-- Index for efficient grouping queries
CREATE INDEX IF NOT EXISTS idx_features_priority_group ON features(project_id, priority_group);
