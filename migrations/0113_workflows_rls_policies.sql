-- workflows table had RLS enabled but NO policies — all queries returned empty
-- Add policies matching the pattern used by features, personas, vp_steps

CREATE POLICY "workflows_select" ON workflows
  FOR SELECT TO authenticated USING (true);

CREATE POLICY "workflows_insert" ON workflows
  FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "workflows_update" ON workflows
  FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "workflows_delete" ON workflows
  FOR DELETE TO authenticated USING (true);

CREATE POLICY "workflows_service" ON workflows
  FOR ALL TO service_role USING (true) WITH CHECK (true);
