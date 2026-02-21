-- Auto-confirm project setting + solution flow cascade support
-- When enabled, high/very_high confidence extractions are auto-confirmed as confirmed_consultant

ALTER TABLE projects
  ADD COLUMN IF NOT EXISTS auto_confirm_extractions BOOLEAN NOT NULL DEFAULT false;

COMMENT ON COLUMN projects.auto_confirm_extractions IS
  'When true, V2 pipeline auto-confirms entities with high or very_high confidence';

-- Solution flow step: flag when linked entities are updated
ALTER TABLE solution_flow_steps
  ADD COLUMN IF NOT EXISTS has_pending_updates BOOLEAN NOT NULL DEFAULT false;
