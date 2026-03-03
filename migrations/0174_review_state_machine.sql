-- 0174_review_state_machine.sql
-- Adds review state machine, flag_for_client verdict, and update pipeline storage

-- Review state on prototype sessions
ALTER TABLE prototype_sessions
  ADD COLUMN IF NOT EXISTS review_state TEXT DEFAULT 'not_started';

ALTER TABLE prototype_sessions
  DROP CONSTRAINT IF EXISTS prototype_sessions_review_state_check;

ALTER TABLE prototype_sessions
  ADD CONSTRAINT prototype_sessions_review_state_check
  CHECK (review_state IN ('not_started','in_progress','complete','updating','re_review','ready_for_client'));

ALTER TABLE prototype_sessions
  ADD COLUMN IF NOT EXISTS review_summary JSONB;

-- Add flag_for_client as valid verdict
ALTER TABLE prototype_epic_confirmations
  DROP CONSTRAINT IF EXISTS prototype_epic_confirmations_verdict_check;

ALTER TABLE prototype_epic_confirmations
  ADD CONSTRAINT prototype_epic_confirmations_verdict_check
  CHECK (verdict IS NULL OR verdict IN ('confirmed','refine','flag_for_client'));

-- Store build artifacts path for update pipeline
ALTER TABLE prototype_builds
  ADD COLUMN IF NOT EXISTS build_dir TEXT;

-- Store coherence plan separately for update pipeline
ALTER TABLE prototypes
  ADD COLUMN IF NOT EXISTS coherence_plan JSONB;

-- Store Netlify site_id for redeployment
ALTER TABLE prototypes
  ADD COLUMN IF NOT EXISTS netlify_site_id TEXT;
