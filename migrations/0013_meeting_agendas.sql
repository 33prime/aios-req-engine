-- Migration: Meeting Agendas
-- Description: Create table to store generated meeting agendas from confirmations
-- Date: 2025-12-23

CREATE TABLE IF NOT EXISTS meeting_agendas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  title TEXT NOT NULL,
  summary TEXT NOT NULL,
  suggested_duration_minutes INT NOT NULL,
  agenda_items JSONB DEFAULT '[]'::jsonb,
  confirmation_ids UUID[] NOT NULL,
  status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'scheduled')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for project-level queries
CREATE INDEX idx_meeting_agendas_project ON meeting_agendas(project_id, created_at DESC);

-- Index for status filtering
CREATE INDEX idx_meeting_agendas_status ON meeting_agendas(project_id, status);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_meeting_agendas_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER meeting_agendas_updated_at
  BEFORE UPDATE ON meeting_agendas
  FOR EACH ROW
  EXECUTE FUNCTION update_meeting_agendas_updated_at();

-- Comments
COMMENT ON TABLE meeting_agendas IS 'AI-generated meeting agendas created from selected confirmation items';
COMMENT ON COLUMN meeting_agendas.title IS 'Meeting title (e.g., "MVP Clarification Meeting")';
COMMENT ON COLUMN meeting_agendas.summary IS 'Brief summary of meeting purpose';
COMMENT ON COLUMN meeting_agendas.suggested_duration_minutes IS 'Recommended meeting duration based on agenda complexity';
COMMENT ON COLUMN meeting_agendas.agenda_items IS 'JSONB array of agenda items with topic, duration, confirmations, discussion_notes';
COMMENT ON COLUMN meeting_agendas.confirmation_ids IS 'Array of confirmation UUIDs included in this agenda';
COMMENT ON COLUMN meeting_agendas.status IS 'Agenda status: draft, approved, or scheduled';
