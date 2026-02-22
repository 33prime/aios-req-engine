-- 0160_pending_items_expand_types.sql
-- Extend pending_items CHECK constraints for new entity types (workflow, data_entity,
-- constraint, solution_flow_step) and 'chat' source for chat-tool-created items.

ALTER TABLE pending_items DROP CONSTRAINT IF EXISTS pending_items_item_type_check;
ALTER TABLE pending_items ADD CONSTRAINT pending_items_item_type_check
  CHECK (item_type IN (
    'feature', 'persona', 'vp_step', 'question', 'document',
    'kpi', 'goal', 'pain_point', 'requirement', 'competitor',
    'design_preference', 'stakeholder', 'open_question',
    'workflow', 'data_entity', 'constraint', 'solution_flow_step'
  ));

ALTER TABLE pending_items DROP CONSTRAINT IF EXISTS pending_items_source_check;
ALTER TABLE pending_items ADD CONSTRAINT pending_items_source_check
  CHECK (source IN ('phase_workflow', 'needs_review', 'ai_generated', 'manual', 'solution_flow', 'chat'));
