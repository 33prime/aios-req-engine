-- 0146_solution_flow_escalation.sql
-- Extend pending_items CHECK constraints for solution flow escalation

-- Add 'open_question', 'competitor', 'design_preference', 'stakeholder' to item_type
ALTER TABLE pending_items DROP CONSTRAINT IF EXISTS pending_items_item_type_check;
ALTER TABLE pending_items ADD CONSTRAINT pending_items_item_type_check
  CHECK (item_type IN (
    'feature', 'persona', 'vp_step', 'question', 'document',
    'kpi', 'goal', 'pain_point', 'requirement', 'competitor',
    'design_preference', 'stakeholder', 'open_question'
  ));

-- Add 'solution_flow' to source
ALTER TABLE pending_items DROP CONSTRAINT IF EXISTS pending_items_source_check;
ALTER TABLE pending_items ADD CONSTRAINT pending_items_source_check
  CHECK (source IN ('phase_workflow', 'needs_review', 'ai_generated', 'manual', 'solution_flow'));
