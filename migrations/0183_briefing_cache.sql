-- Migration 0183: Briefing cache table
-- Pre-rendered project briefings from pulse data, served to chat/dashboard/meeting prep

CREATE TABLE IF NOT EXISTS project_briefings (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    progress text NOT NULL DEFAULT '',
    confirm_candidates jsonb NOT NULL DEFAULT '[]',
    priority_actions jsonb NOT NULL DEFAULT '[]',
    risk_alerts jsonb NOT NULL DEFAULT '[]',
    orphan_alerts jsonb NOT NULL DEFAULT '[]',
    review_flags jsonb NOT NULL DEFAULT '[]',
    pulse_snapshot_id uuid,
    generated_at timestamptz NOT NULL DEFAULT now(),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_project_briefings_project ON project_briefings(project_id);
CREATE INDEX idx_project_briefings_generated ON project_briefings(project_id, generated_at DESC);
