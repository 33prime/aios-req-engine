-- ============================================================================
-- Migration 0123: Process Documents
-- Structured process documentation generated from KB items
-- ============================================================================

CREATE TABLE IF NOT EXISTS process_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    client_id UUID REFERENCES clients(id) ON DELETE SET NULL,

    -- KB provenance
    source_kb_category TEXT,
    source_kb_item_id TEXT,

    -- Core content
    title TEXT NOT NULL,
    purpose TEXT,
    trigger_event TEXT,
    frequency TEXT,

    -- Structured sections (JSONB arrays)
    steps JSONB DEFAULT '[]'::jsonb,
    roles JSONB DEFAULT '[]'::jsonb,
    data_flow JSONB DEFAULT '[]'::jsonb,
    decision_points JSONB DEFAULT '[]'::jsonb,
    exceptions JSONB DEFAULT '[]'::jsonb,
    tribal_knowledge_callouts JSONB DEFAULT '[]'::jsonb,
    evidence JSONB DEFAULT '[]'::jsonb,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'review', 'confirmed', 'archived')),
    confirmation_status TEXT DEFAULT 'ai_generated'
        CHECK (confirmation_status IN (
            'ai_generated', 'confirmed_consultant', 'confirmed_client', 'needs_client'
        )),

    -- Generation metadata
    generation_scenario TEXT
        CHECK (generation_scenario IN ('reconstruct', 'generate', 'tribal_capture')),
    generation_model TEXT,
    generation_duration_ms INTEGER,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_process_documents_project_id ON process_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_process_documents_client_id ON process_documents(client_id);
CREATE INDEX IF NOT EXISTS idx_process_documents_status ON process_documents(status);
CREATE INDEX IF NOT EXISTS idx_process_documents_source_kb_item ON process_documents(source_kb_item_id);

-- updated_at trigger
CREATE OR REPLACE TRIGGER set_process_documents_updated_at
    BEFORE UPDATE ON process_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- RLS Policies
-- ============================================================================

ALTER TABLE process_documents ENABLE ROW LEVEL SECURITY;

-- Authenticated users can read all
CREATE POLICY "process_documents_select_authenticated"
    ON process_documents FOR SELECT
    TO authenticated
    USING (true);

-- Authenticated users can insert
CREATE POLICY "process_documents_insert_authenticated"
    ON process_documents FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Authenticated users can update
CREATE POLICY "process_documents_update_authenticated"
    ON process_documents FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

-- Authenticated users can delete
CREATE POLICY "process_documents_delete_authenticated"
    ON process_documents FOR DELETE
    TO authenticated
    USING (true);

-- Service role full access
CREATE POLICY "process_documents_service_role"
    ON process_documents FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
