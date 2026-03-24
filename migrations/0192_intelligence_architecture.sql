-- Intelligence Architecture: 4-quadrant classification of product intelligence
-- Stores knowledge systems, scoring models, decision logic, AI capabilities per project

CREATE TABLE IF NOT EXISTS intelligence_architecture (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  quadrants JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(project_id)
);

-- RLS
ALTER TABLE intelligence_architecture ENABLE ROW LEVEL SECURITY;
CREATE POLICY "intelligence_architecture_all" ON intelligence_architecture
  FOR ALL USING (true) WITH CHECK (true);
