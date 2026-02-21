-- Convergence tracking for prototype review sessions
-- Stores computed convergence metrics per session for fast querying

ALTER TABLE prototype_sessions
  ADD COLUMN IF NOT EXISTS convergence_snapshot JSONB DEFAULT NULL;

-- Comment explaining structure
COMMENT ON COLUMN prototype_sessions.convergence_snapshot IS
  'Computed convergence metrics: {alignment_rate, trend, feedback_resolution_rate, question_coverage, per_feature: [{feature_id, consultant_verdict, client_verdict, aligned, delta}]}';
