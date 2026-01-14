-- Migration: 0051_client_portal_info_requests.sql
-- Description: Info requests for pre-call questions and post-call action items
-- Date: 2026-01-12

-- Unified info requests (pre-call questions + post-call action items)
CREATE TABLE IF NOT EXISTS info_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- Metadata
  phase TEXT NOT NULL CHECK (phase IN ('pre_call', 'post_call')),
  created_by TEXT NOT NULL CHECK (created_by IN ('ai', 'consultant')),
  display_order INT NOT NULL DEFAULT 0,

  -- Content
  title TEXT NOT NULL,
  description TEXT,
  context_from_call TEXT,  -- "You mentioned Jennifer spends 15 hrs..."

  -- Type configuration
  request_type TEXT NOT NULL CHECK (request_type IN ('question', 'document', 'tribal_knowledge')),
  input_type TEXT NOT NULL CHECK (input_type IN ('text', 'file', 'multi_text', 'text_and_file')),
  priority TEXT DEFAULT 'medium' CHECK (priority IN ('high', 'medium', 'low', 'none')),

  -- Assignment
  best_answered_by TEXT,  -- "You" or "Jennifer (Dev Director)"
  can_delegate BOOLEAN DEFAULT FALSE,

  -- Response tracking
  status TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'complete', 'skipped')),
  answer_data JSONB,  -- Flexible storage for any answer type
  completed_at TIMESTAMPTZ,
  completed_by UUID REFERENCES users(id),

  -- Context auto-population mapping
  auto_populates_to TEXT[],  -- ['problem', 'users', 'metrics']

  -- Helper content for client
  why_asking TEXT,
  example_answer TEXT,
  pro_tip TEXT,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for info_requests
CREATE INDEX IF NOT EXISTS idx_info_requests_project ON info_requests(project_id);
CREATE INDEX IF NOT EXISTS idx_info_requests_phase ON info_requests(project_id, phase);
CREATE INDEX IF NOT EXISTS idx_info_requests_status ON info_requests(project_id, status);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_info_requests_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER info_requests_updated_at
  BEFORE UPDATE ON info_requests
  FOR EACH ROW
  EXECUTE FUNCTION update_info_requests_updated_at();
