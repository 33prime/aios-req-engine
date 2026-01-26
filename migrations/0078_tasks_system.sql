-- Migration: Tasks System
-- Description: Adds tasks table for unified work management and task_activity_log for audit trail

-- ============================================================================
-- TASKS TABLE
-- ============================================================================
-- Central work management layer for pushing projects toward gate completion.
-- Tasks can come from: DI Agent (gaps), Signal Processing (proposals),
-- Manual creation (user/AI assistant), Enrichment triggers, Validation needs.

CREATE TABLE IF NOT EXISTS tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- Content
  title TEXT NOT NULL,
  description TEXT,

  -- Type & Classification
  task_type TEXT NOT NULL DEFAULT 'manual',
    -- Values: 'proposal' | 'gap' | 'manual' | 'enrichment' | 'validation' | 'research' | 'collaboration'

  -- Anchoring (what this task relates to)
  anchored_entity_type TEXT,
    -- Values: 'business_driver' | 'feature' | 'persona' | 'vp_step' | 'stakeholder' | 'competitor_ref' | 'gate' | NULL (project-level)
  anchored_entity_id UUID,
  gate_stage TEXT,
    -- Which gate this helps satisfy (for priority calculation)
    -- Values: 'core_pain' | 'primary_persona' | 'wow_moment' | 'design_preferences' | 'business_case' | 'budget_constraints' | 'full_requirements' | 'confirmed_scope'

  -- Priority
  priority_score NUMERIC DEFAULT 50,
    -- Calculated: entity_value × gate_modifier × client_boost

  -- Status & Lifecycle
  status TEXT NOT NULL DEFAULT 'pending',
    -- Values: 'pending' | 'in_progress' | 'completed' | 'dismissed'

  -- Client Relevance (for Collaboration tab filtering)
  requires_client_input BOOLEAN DEFAULT false,

  -- Source Tracking
  source_type TEXT NOT NULL DEFAULT 'manual',
    -- Values: 'di_agent' | 'signal_processing' | 'manual' | 'enrichment_trigger' | 'ai_assistant'
  source_id UUID,
    -- Reference to proposal_id, signal_id, di_agent_log_id, etc.
  source_context JSONB DEFAULT '{}',
    -- Additional context from source (e.g., proposal details, gap analysis)

  -- Resolution
  completed_at TIMESTAMPTZ,
  completed_by UUID REFERENCES users(id),
  completion_method TEXT,
    -- Values: 'chat_approval' | 'task_board' | 'auto' | 'dismissed'
  completion_notes TEXT,

  -- If this creates a collaboration item
  info_request_id UUID REFERENCES info_requests(id),

  -- Metadata
  metadata JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Add comments for documentation
COMMENT ON TABLE tasks IS 'Unified work management for pushing projects toward gate completion';
COMMENT ON COLUMN tasks.task_type IS 'proposal | gap | manual | enrichment | validation | research | collaboration';
COMMENT ON COLUMN tasks.anchored_entity_type IS 'Entity type this task relates to: business_driver, feature, persona, vp_step, stakeholder, competitor_ref, gate, or NULL for project-level';
COMMENT ON COLUMN tasks.gate_stage IS 'Which gate this task helps satisfy, used for priority calculation';
COMMENT ON COLUMN tasks.priority_score IS 'Calculated priority: entity_value × gate_modifier × client_boost';
COMMENT ON COLUMN tasks.requires_client_input IS 'If true, task appears in Collaboration tab';
COMMENT ON COLUMN tasks.source_type IS 'Where this task originated: di_agent, signal_processing, manual, enrichment_trigger, ai_assistant';

-- Indexes for common query patterns
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX idx_tasks_project_type ON tasks(project_id, task_type);
CREATE INDEX idx_tasks_anchored ON tasks(anchored_entity_type, anchored_entity_id) WHERE anchored_entity_id IS NOT NULL;
CREATE INDEX idx_tasks_requires_client ON tasks(project_id) WHERE requires_client_input = true AND status = 'pending';
CREATE INDEX idx_tasks_priority ON tasks(project_id, priority_score DESC) WHERE status = 'pending';
CREATE INDEX idx_tasks_source ON tasks(source_type, source_id) WHERE source_id IS NOT NULL;

-- Updated_at trigger
CREATE TRIGGER tasks_updated_at
  BEFORE UPDATE ON tasks
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- TASK ACTIVITY LOG TABLE
-- ============================================================================
-- Audit trail for task lifecycle events.

CREATE TABLE IF NOT EXISTS task_activity_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- Activity details
  action TEXT NOT NULL,
    -- Values: 'created' | 'started' | 'completed' | 'dismissed' | 'reopened' | 'updated' | 'priority_changed'
  actor_type TEXT NOT NULL,
    -- Values: 'user' | 'system' | 'ai_assistant'
  actor_id UUID,
    -- user_id if actor_type = 'user'

  -- State snapshot
  previous_status TEXT,
  new_status TEXT,
  previous_priority NUMERIC,
  new_priority NUMERIC,

  -- Additional details
  details JSONB DEFAULT '{}',

  created_at TIMESTAMPTZ DEFAULT now()
);

-- Add comments
COMMENT ON TABLE task_activity_log IS 'Audit trail for task lifecycle events';
COMMENT ON COLUMN task_activity_log.action IS 'created | started | completed | dismissed | reopened | updated | priority_changed';
COMMENT ON COLUMN task_activity_log.actor_type IS 'user | system | ai_assistant';

-- Indexes
CREATE INDEX idx_task_activity_project ON task_activity_log(project_id, created_at DESC);
CREATE INDEX idx_task_activity_task ON task_activity_log(task_id, created_at DESC);
CREATE INDEX idx_task_activity_actor ON task_activity_log(actor_type, actor_id) WHERE actor_id IS NOT NULL;


-- ============================================================================
-- CONSTRAINTS
-- ============================================================================

-- Ensure valid task_type
ALTER TABLE tasks ADD CONSTRAINT tasks_type_check
  CHECK (task_type IN ('proposal', 'gap', 'manual', 'enrichment', 'validation', 'research', 'collaboration'));

-- Ensure valid status
ALTER TABLE tasks ADD CONSTRAINT tasks_status_check
  CHECK (status IN ('pending', 'in_progress', 'completed', 'dismissed'));

-- Ensure valid source_type
ALTER TABLE tasks ADD CONSTRAINT tasks_source_type_check
  CHECK (source_type IN ('di_agent', 'signal_processing', 'manual', 'enrichment_trigger', 'ai_assistant'));

-- Ensure valid completion_method when completed
ALTER TABLE tasks ADD CONSTRAINT tasks_completion_method_check
  CHECK (
    (status NOT IN ('completed', 'dismissed'))
    OR
    (completion_method IN ('chat_approval', 'task_board', 'auto', 'dismissed'))
  );

-- Ensure valid gate_stage if provided
ALTER TABLE tasks ADD CONSTRAINT tasks_gate_stage_check
  CHECK (
    gate_stage IS NULL
    OR
    gate_stage IN ('core_pain', 'primary_persona', 'wow_moment', 'design_preferences', 'business_case', 'budget_constraints', 'full_requirements', 'confirmed_scope')
  );

-- Ensure valid anchored_entity_type if provided
ALTER TABLE tasks ADD CONSTRAINT tasks_anchored_entity_type_check
  CHECK (
    anchored_entity_type IS NULL
    OR
    anchored_entity_type IN ('business_driver', 'feature', 'persona', 'vp_step', 'stakeholder', 'competitor_ref', 'gate', 'risk')
  );

-- Ensure valid activity action
ALTER TABLE task_activity_log ADD CONSTRAINT task_activity_action_check
  CHECK (action IN ('created', 'started', 'completed', 'dismissed', 'reopened', 'updated', 'priority_changed'));

-- Ensure valid actor_type
ALTER TABLE task_activity_log ADD CONSTRAINT task_activity_actor_type_check
  CHECK (actor_type IN ('user', 'system', 'ai_assistant'));


-- ============================================================================
-- RLS POLICIES (if RLS is enabled)
-- ============================================================================

-- Enable RLS
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_activity_log ENABLE ROW LEVEL SECURITY;

-- Tasks: Users can see tasks for projects they have access to
CREATE POLICY tasks_select_policy ON tasks
  FOR SELECT
  USING (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid()
    )
    OR
    get_my_platform_role() IN ('super_admin', 'solution_architect')
  );

-- Tasks: Consultants can insert/update/delete tasks for their projects
CREATE POLICY tasks_insert_policy ON tasks
  FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid() AND role = 'consultant'
    )
    OR
    get_my_platform_role() IN ('super_admin', 'solution_architect')
  );

CREATE POLICY tasks_update_policy ON tasks
  FOR UPDATE
  USING (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid() AND role = 'consultant'
    )
    OR
    get_my_platform_role() IN ('super_admin', 'solution_architect')
  );

CREATE POLICY tasks_delete_policy ON tasks
  FOR DELETE
  USING (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid() AND role = 'consultant'
    )
    OR
    get_my_platform_role() IN ('super_admin', 'solution_architect')
  );

-- Task activity log: Same access as tasks
CREATE POLICY task_activity_select_policy ON task_activity_log
  FOR SELECT
  USING (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid()
    )
    OR
    get_my_platform_role() IN ('super_admin', 'solution_architect')
  );

CREATE POLICY task_activity_insert_policy ON task_activity_log
  FOR INSERT
  WITH CHECK (
    project_id IN (
      SELECT project_id FROM project_members WHERE user_id = auth.uid() AND role = 'consultant'
    )
    OR
    get_my_platform_role() IN ('super_admin', 'solution_architect')
  );
