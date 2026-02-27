-- Discovery Protocol: North Star progress and mission sign-off columns on projects.
-- Probes are ephemeral (generated per briefing), not persisted.

ALTER TABLE projects ADD COLUMN IF NOT EXISTS north_star_progress JSONB DEFAULT '{}';
ALTER TABLE projects ADD COLUMN IF NOT EXISTS north_star_sign_off JSONB DEFAULT '{}';
