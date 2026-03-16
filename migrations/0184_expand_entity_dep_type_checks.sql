-- Expand entity_dependencies check constraints to include all entity and dependency types
-- Previously missing: workflow, business_driver, constraint, competitor (entity types)
--                     co_occurrence, addresses (dependency types)

ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_source_entity_type_check;
ALTER TABLE entity_dependencies ADD CONSTRAINT entity_dependencies_source_entity_type_check
  CHECK (source_entity_type IN (
    'persona', 'feature', 'vp_step', 'strategic_context', 'stakeholder',
    'data_entity', 'business_driver', 'unlock', 'workflow', 'constraint', 'competitor'
  ));

ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_target_entity_type_check;
ALTER TABLE entity_dependencies ADD CONSTRAINT entity_dependencies_target_entity_type_check
  CHECK (target_entity_type IN (
    'persona', 'feature', 'vp_step', 'signal', 'research_chunk',
    'data_entity', 'business_driver', 'unlock', 'workflow', 'constraint', 'competitor'
  ));

ALTER TABLE entity_dependencies DROP CONSTRAINT IF EXISTS entity_dependencies_dependency_type_check;
ALTER TABLE entity_dependencies ADD CONSTRAINT entity_dependencies_dependency_type_check
  CHECK (dependency_type IN (
    'uses', 'targets', 'derived_from', 'informed_by', 'actor_of',
    'spawns', 'enables', 'constrains', 'co_occurrence', 'addresses'
  ));
