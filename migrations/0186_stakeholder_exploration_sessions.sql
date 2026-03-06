-- Add stakeholder sharing support to prototype sessions.
-- A stakeholder session links back to the parent client session,
-- tracks who invited them, and optionally provides a focus question.

ALTER TABLE prototype_sessions
  ADD COLUMN IF NOT EXISTS parent_session_id UUID REFERENCES prototype_sessions(id),
  ADD COLUMN IF NOT EXISTS invited_by_user_id UUID REFERENCES users(id),
  ADD COLUMN IF NOT EXISTS focus_context TEXT;

CREATE INDEX IF NOT EXISTS idx_proto_sessions_parent
  ON prototype_sessions(parent_session_id)
  WHERE parent_session_id IS NOT NULL;
