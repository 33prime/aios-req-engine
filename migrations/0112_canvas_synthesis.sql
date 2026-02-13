-- Canvas synthesis table for storing AI-generated value paths
CREATE TABLE canvas_synthesis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  synthesis_type TEXT NOT NULL DEFAULT 'value_path',

  -- The synthesized value path (JSONB)
  value_path JSONB NOT NULL DEFAULT '[]',
  -- Metadata about the synthesis
  synthesis_rationale TEXT,
  excluded_flows TEXT[] DEFAULT '{}',
  source_workflow_ids UUID[] DEFAULT '{}',
  source_persona_ids UUID[] DEFAULT '{}',

  -- Tracking
  generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  generated_by TEXT DEFAULT 'di_agent',
  is_stale BOOLEAN NOT NULL DEFAULT FALSE,
  stale_reason TEXT,
  version INTEGER NOT NULL DEFAULT 1,

  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (project_id, synthesis_type)
);

-- RLS: match existing pattern
ALTER TABLE canvas_synthesis ENABLE ROW LEVEL SECURITY;
CREATE POLICY "canvas_synthesis_authenticated" ON canvas_synthesis
  FOR ALL TO authenticated USING (true) WITH CHECK (true);
CREATE POLICY "canvas_synthesis_service" ON canvas_synthesis
  FOR ALL TO service_role USING (true) WITH CHECK (true);
