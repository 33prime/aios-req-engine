-- Create clients table: unified client organization entity across projects
-- RLS enabled + policies from the start (lesson from 0113 incident)

CREATE TABLE IF NOT EXISTS clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Core
    name TEXT NOT NULL,
    website TEXT,
    industry TEXT,
    stage TEXT,  -- startup, growth, enterprise, government, non-profit
    size TEXT,   -- 1-10, 11-50, 51-200, 201-1000, 1001-5000, 5000+
    description TEXT,
    logo_url TEXT,

    -- Enrichment fields (populated by AI)
    revenue_range TEXT,
    employee_count INTEGER,
    founding_year INTEGER,
    headquarters TEXT,
    tech_stack JSONB DEFAULT '[]'::jsonb,
    growth_signals JSONB DEFAULT '[]'::jsonb,
    competitors JSONB DEFAULT '[]'::jsonb,
    innovation_score REAL,

    -- AI analysis fields
    company_summary TEXT,
    market_position TEXT,
    technology_maturity TEXT CHECK (technology_maturity IN ('legacy', 'transitioning', 'modern', 'cutting_edge')),
    digital_readiness TEXT CHECK (digital_readiness IN ('low', 'medium', 'high', 'advanced')),

    -- Knowledge base (Phase 2 — defaults to empty)
    business_processes JSONB DEFAULT '[]'::jsonb,
    sops JSONB DEFAULT '[]'::jsonb,
    tribal_knowledge JSONB DEFAULT '[]'::jsonb,

    -- Enrichment tracking
    enrichment_status TEXT NOT NULL DEFAULT 'pending' CHECK (enrichment_status IN ('pending', 'in_progress', 'completed', 'failed')),
    enriched_at TIMESTAMPTZ,
    enrichment_source TEXT,

    -- Ownership
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-update updated_at
CREATE TRIGGER set_clients_updated_at
    BEFORE UPDATE ON clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add client_id FK to projects
ALTER TABLE projects
    ADD COLUMN IF NOT EXISTS client_id UUID REFERENCES clients(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects(client_id);

-- Indexes on clients
CREATE INDEX IF NOT EXISTS idx_clients_name ON clients(name);
CREATE INDEX IF NOT EXISTS idx_clients_organization_id ON clients(organization_id);
CREATE INDEX IF NOT EXISTS idx_clients_industry ON clients(industry);
CREATE INDEX IF NOT EXISTS idx_clients_enrichment_status ON clients(enrichment_status);
CREATE INDEX IF NOT EXISTS idx_clients_name_gin ON clients USING gin(to_tsvector('english', name));

-- Enable RLS
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;

-- Permissive policies for authenticated users
CREATE POLICY "clients_select" ON clients
    FOR SELECT TO authenticated USING (true);

CREATE POLICY "clients_insert" ON clients
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY "clients_update" ON clients
    FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY "clients_delete" ON clients
    FOR DELETE TO authenticated USING (true);

-- Service role full access
CREATE POLICY "clients_service" ON clients
    FOR ALL TO service_role USING (true) WITH CHECK (true);
