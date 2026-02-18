-- Signal Pipeline v2: processing status tracking
-- Adds columns to signals table for pipeline progress tracking and patch results.

ALTER TABLE signals ADD COLUMN IF NOT EXISTS processing_status TEXT DEFAULT 'pending'
  CHECK (processing_status IN ('pending','preprocessing','triaged','extracting','scoring','applying','complete','failed'));

ALTER TABLE signals ADD COLUMN IF NOT EXISTS triage_metadata JSONB DEFAULT '{}';

ALTER TABLE signals ADD COLUMN IF NOT EXISTS patch_summary JSONB DEFAULT '{}';

-- Index for status-based queries (dashboard, polling)
CREATE INDEX IF NOT EXISTS idx_signals_processing_status ON signals (processing_status)
  WHERE processing_status NOT IN ('complete', 'pending');
