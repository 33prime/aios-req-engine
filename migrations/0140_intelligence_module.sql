-- Migration: 0140_intelligence_module.sql
-- Add consultant confirmation columns to memory_nodes (orthogonal to hypothesis_status)

ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS consultant_status TEXT;
ALTER TABLE memory_nodes ADD CONSTRAINT chk_consultant_status
  CHECK (consultant_status IS NULL OR consultant_status IN ('confirmed', 'disputed'));
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS consultant_note TEXT;
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS consultant_status_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_memory_nodes_consultant_status
  ON memory_nodes(project_id, consultant_status)
  WHERE consultant_status IS NOT NULL;
