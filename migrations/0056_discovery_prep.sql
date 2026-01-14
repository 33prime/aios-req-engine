-- Discovery Prep Bundles
-- Stores AI-generated pre-call preparation content (questions, documents, agenda)
-- One bundle per project, regenerated as needed

CREATE TABLE IF NOT EXISTS discovery_prep_bundles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Agenda
    agenda_summary TEXT,
    agenda_bullets JSONB DEFAULT '[]'::jsonb,

    -- Generated content (JSONB for flexibility)
    -- Questions: [{id, question, best_answered_by, why_important, confirmed, client_answer, answered_at}]
    questions JSONB DEFAULT '[]'::jsonb,
    -- Documents: [{id, document_name, priority, why_important, confirmed, uploaded_file_id, uploaded_at}]
    documents JSONB DEFAULT '[]'::jsonb,

    -- Status tracking
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'confirmed', 'sent')),
    sent_to_portal_at TIMESTAMPTZ,

    -- Timestamps
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- One bundle per project
    UNIQUE(project_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_discovery_prep_project ON discovery_prep_bundles(project_id);
CREATE INDEX IF NOT EXISTS idx_discovery_prep_status ON discovery_prep_bundles(status);

-- Updated at trigger
CREATE OR REPLACE FUNCTION update_discovery_prep_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_discovery_prep_updated_at ON discovery_prep_bundles;
CREATE TRIGGER trigger_discovery_prep_updated_at
    BEFORE UPDATE ON discovery_prep_bundles
    FOR EACH ROW
    EXECUTE FUNCTION update_discovery_prep_updated_at();

-- Add portal_response to signal source types if signals table exists
-- This allows tracking client answers as authoritative signals
DO $$
BEGIN
    -- Check if the constraint exists and update it
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'signals_source_type_check'
        AND table_name = 'signals'
    ) THEN
        ALTER TABLE signals DROP CONSTRAINT IF EXISTS signals_source_type_check;
        ALTER TABLE signals ADD CONSTRAINT signals_source_type_check
            CHECK (source_type IN (
                'prd', 'transcript', 'email', 'research', 'document',
                'note', 'chat', 'unknown', 'portal_response'
            ));
    END IF;
END $$;
