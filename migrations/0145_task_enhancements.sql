-- 0145_task_enhancements.sql
-- Add assignment, due dates, human priority to tasks; create task_comments table

-- New columns on tasks
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS due_date TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'none';

ALTER TABLE tasks ADD CONSTRAINT tasks_priority_check
  CHECK (priority IN ('none', 'low', 'medium', 'high'));

CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to, status) WHERE assigned_to IS NOT NULL;
CREATE INDEX idx_tasks_created_by ON tasks(created_by) WHERE created_by IS NOT NULL;
CREATE INDEX idx_tasks_due_date ON tasks(due_date) WHERE due_date IS NOT NULL AND status NOT IN ('completed', 'dismissed');

-- Task comments
CREATE TABLE task_comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  author_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_task_comments_task ON task_comments(task_id, created_at);
ALTER TABLE task_comments ENABLE ROW LEVEL SECURITY;

-- Extend activity action enum to include new actions
ALTER TABLE task_activity_log DROP CONSTRAINT IF EXISTS task_activity_action_check;
ALTER TABLE task_activity_log ADD CONSTRAINT task_activity_action_check
  CHECK (action IN ('created','started','completed','dismissed','reopened','updated','priority_changed','assigned','commented','due_date_changed'));
