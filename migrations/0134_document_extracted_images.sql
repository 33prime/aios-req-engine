-- Migration: 0134_document_extracted_images
-- Description: Table for persisting images extracted from documents (PDF, PPTX)

-- Create the table
CREATE TABLE IF NOT EXISTS document_extracted_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_upload_id UUID NOT NULL REFERENCES document_uploads(id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    page_number INTEGER,  -- 1-indexed slide/page number
    image_index INTEGER NOT NULL DEFAULT 0,  -- 0-based order within page
    source_context TEXT,  -- e.g. "Slide 3 > Architecture Diagram"
    vision_analysis TEXT,
    vision_model TEXT,
    vision_analyzed_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_doc_extracted_images_upload
    ON document_extracted_images(document_upload_id);
CREATE INDEX IF NOT EXISTS idx_doc_extracted_images_project
    ON document_extracted_images(project_id);

-- Updated_at trigger
CREATE TRIGGER set_updated_at_document_extracted_images
    BEFORE UPDATE ON document_extracted_images
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE document_extracted_images ENABLE ROW LEVEL SECURITY;

-- RLS policies: service_role full access
CREATE POLICY "service_role_all_document_extracted_images"
    ON document_extracted_images
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- RLS policies: authenticated users can read images for projects they have access to
CREATE POLICY "authenticated_select_document_extracted_images"
    ON document_extracted_images
    FOR SELECT
    TO authenticated
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN project_members pm ON pm.project_id = p.id
            WHERE pm.user_id = auth.uid()
        )
    );

-- RLS policies: authenticated users can insert for their projects
CREATE POLICY "authenticated_insert_document_extracted_images"
    ON document_extracted_images
    FOR INSERT
    TO authenticated
    WITH CHECK (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN project_members pm ON pm.project_id = p.id
            WHERE pm.user_id = auth.uid()
        )
    );
