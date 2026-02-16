-- Migration 0127: Add verdict columns to prototype_feature_overlays
-- Supports the streamlined review flow: one question per feature + quick verdict + open feedback

ALTER TABLE prototype_feature_overlays
  ADD COLUMN consultant_verdict TEXT,
  ADD COLUMN consultant_notes TEXT,
  ADD COLUMN client_verdict TEXT,
  ADD COLUMN client_notes TEXT;

ALTER TABLE prototype_feature_overlays
  ADD CONSTRAINT chk_consultant_verdict
    CHECK (consultant_verdict IS NULL OR consultant_verdict IN ('aligned', 'needs_adjustment', 'off_track'));

ALTER TABLE prototype_feature_overlays
  ADD CONSTRAINT chk_client_verdict
    CHECK (client_verdict IS NULL OR client_verdict IN ('aligned', 'needs_adjustment', 'off_track'));
