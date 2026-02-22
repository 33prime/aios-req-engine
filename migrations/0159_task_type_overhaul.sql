-- Task System Overhaul: migrate from system-generated types to consulting workflow types
-- New types: signal_review, action_item, meeting_prep, reminder, review_request, book_meeting, deliverable, custom

-- 1. Drop old CHECK constraint
ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_type_check;

-- 2. Migrate existing data
UPDATE tasks SET task_type = 'signal_review' WHERE task_type = 'proposal';
UPDATE tasks SET task_type = 'custom' WHERE task_type IN ('manual', 'research', 'collaboration');
UPDATE tasks SET task_type = 'custom',
  status = CASE WHEN status IN ('pending', 'in_progress') THEN 'dismissed' ELSE status END
  WHERE task_type IN ('gap', 'enrichment', 'validation');

-- 3. New columns
ALTER TABLE tasks
  ADD COLUMN IF NOT EXISTS review_status TEXT,
  ADD COLUMN IF NOT EXISTS remind_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS meeting_type TEXT,
  ADD COLUMN IF NOT EXISTS meeting_date TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS signal_id UUID REFERENCES signals(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS patches_snapshot JSONB,
  ADD COLUMN IF NOT EXISTS action_verb TEXT;

-- 4. New CHECK constraints
ALTER TABLE tasks ADD CONSTRAINT tasks_type_check CHECK (task_type IN (
  'signal_review','action_item','meeting_prep','reminder',
  'review_request','book_meeting','deliverable','custom'
));
ALTER TABLE tasks ADD CONSTRAINT tasks_review_status_check CHECK (
  review_status IS NULL OR review_status IN ('pending_review','in_review','approved','changes_requested')
);
ALTER TABLE tasks ADD CONSTRAINT tasks_meeting_type_check CHECK (
  meeting_type IS NULL OR meeting_type IN (
    'discovery','event_modeling','proposal','prototype_review','kickoff',
    'stakeholder_interview','technical_deep_dive','internal_strategy',
    'introduction','monthly_check_in','hand_off'
  )
);
ALTER TABLE tasks ADD CONSTRAINT tasks_action_verb_check CHECK (
  action_verb IS NULL OR action_verb IN ('send','email','schedule','prepare','review','follow_up','share','create')
);

-- 5. Indexes
CREATE INDEX IF NOT EXISTS idx_tasks_remind_at ON tasks(remind_at) WHERE remind_at IS NOT NULL AND status = 'pending';
CREATE INDEX IF NOT EXISTS idx_tasks_signal_id ON tasks(signal_id) WHERE signal_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_review_status ON tasks(review_status) WHERE review_status IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_meeting_date ON tasks(meeting_date) WHERE meeting_date IS NOT NULL;

-- 6. Extend activity log actions
ALTER TABLE task_activity_log DROP CONSTRAINT IF EXISTS task_activity_action_check;
ALTER TABLE task_activity_log ADD CONSTRAINT task_activity_action_check CHECK (action IN (
  'created','started','completed','dismissed','reopened','updated',
  'priority_changed','assigned','commented','due_date_changed',
  'review_status_changed','reminder_sent'
));
