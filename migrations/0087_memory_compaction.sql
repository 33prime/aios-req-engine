-- Migration: Memory Compaction Support
-- Description: Add is_landmark field to project_decisions for compaction preservation
-- Author: Memory compaction feature
-- Date: 2025-01-28

-- Add is_landmark column to project_decisions
ALTER TABLE project_decisions
ADD COLUMN IF NOT EXISTS is_landmark BOOLEAN DEFAULT FALSE;

-- Add index for quick landmark queries
CREATE INDEX IF NOT EXISTS idx_project_decisions_landmark
ON project_decisions(project_id, is_landmark)
WHERE is_landmark = TRUE;

-- Add compaction metadata to project_memory
ALTER TABLE project_memory
ADD COLUMN IF NOT EXISTS last_compacted_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS compaction_count INT DEFAULT 0;

COMMENT ON COLUMN project_decisions.is_landmark IS 'Landmark decisions are never compacted - preserved in full detail';
COMMENT ON COLUMN project_memory.last_compacted_at IS 'Timestamp of last memory compaction';
COMMENT ON COLUMN project_memory.compaction_count IS 'Number of times memory has been compacted';
