-- Migration: 0118_data_entities_rls_policies.sql
-- Fix: data_entities and data_entity_workflow_steps have RLS enabled but ZERO policies.
-- This causes silently empty results in production (same bug as workflows in 0113).

-- ============================================================
-- data_entities: allow authenticated users full access
-- ============================================================

CREATE POLICY "data_entities_select" ON data_entities
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "data_entities_insert" ON data_entities
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "data_entities_update" ON data_entities
  FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "data_entities_delete" ON data_entities
  FOR DELETE TO authenticated USING (true);

CREATE POLICY "data_entities_service" ON data_entities
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- ============================================================
-- data_entity_workflow_steps: allow authenticated users full access
-- ============================================================

CREATE POLICY "dews_select" ON data_entity_workflow_steps
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "dews_insert" ON data_entity_workflow_steps
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "dews_update" ON data_entity_workflow_steps
  FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "dews_delete" ON data_entity_workflow_steps
  FOR DELETE TO authenticated USING (true);

CREATE POLICY "dews_service" ON data_entity_workflow_steps
  FOR ALL TO service_role USING (true) WITH CHECK (true);
