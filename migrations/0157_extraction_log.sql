-- Add extraction_log JSONB column to signals for full extraction audit trails
ALTER TABLE signals ADD COLUMN extraction_log JSONB DEFAULT '{}';
COMMENT ON COLUMN signals.extraction_log IS 'Full extraction audit trail: per-chunk patches, dedup decisions, scoring results';
