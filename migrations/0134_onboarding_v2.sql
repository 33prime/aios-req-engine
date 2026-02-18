-- Migration 0134: Onboarding V2 — notifications table + project launch status
-- Supports: in-app notifications, project building state

-- =============================================================================
-- 1. Notifications table
-- =============================================================================

CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  type TEXT NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  entity_type TEXT,
  entity_id UUID,
  read BOOLEAN DEFAULT false,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Fast lookup for user's unread notifications
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread
  ON notifications(user_id, read, created_at DESC);

-- RLS policies
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

-- Users can read their own notifications
CREATE POLICY notifications_select ON notifications
  FOR SELECT TO authenticated
  USING (user_id = auth.uid());

-- Users can update their own notifications (mark read)
CREATE POLICY notifications_update ON notifications
  FOR UPDATE TO authenticated
  USING (user_id = auth.uid());

-- Backend inserts on behalf of users (service_role)
CREATE POLICY notifications_service_insert ON notifications
  FOR INSERT TO service_role
  WITH CHECK (true);

CREATE POLICY notifications_service_select ON notifications
  FOR SELECT TO service_role
  USING (true);

CREATE POLICY notifications_service_update ON notifications
  FOR UPDATE TO service_role
  USING (true);

-- =============================================================================
-- 2. Projects — launch status columns
-- =============================================================================

ALTER TABLE projects ADD COLUMN IF NOT EXISTS launch_status TEXT
  CHECK (launch_status IN ('building', 'ready', 'failed'));

ALTER TABLE projects ADD COLUMN IF NOT EXISTS active_launch_id UUID;
