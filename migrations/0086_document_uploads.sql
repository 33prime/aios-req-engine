-- Migration: Document Uploads System
-- Adds support for uploading and processing PDF, DOCX, XLSX, PPTX, and images
-- with smart chunking, classification, and hybrid search

-- ============================================================================
-- Document Uploads Table
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_uploads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- File information
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,  -- Supabase Storage path
    file_type TEXT NOT NULL CHECK (file_type IN ('pdf', 'docx', 'xlsx', 'pptx', 'image')),
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    checksum TEXT,  -- SHA256 for deduplication

    -- Classification (AI-assigned after processing)
    document_class TEXT,  -- 'prd', 'transcript', 'spec', 'email', 'presentation', 'spreadsheet', 'wireframe', 'generic'
    quality_score FLOAT CHECK (quality_score IS NULL OR (quality_score >= 0 AND quality_score <= 1)),
    relevance_score FLOAT CHECK (relevance_score IS NULL OR (relevance_score >= 0 AND relevance_score <= 1)),
    information_density FLOAT CHECK (information_density IS NULL OR (information_density >= 0 AND information_density <= 1)),

    -- Processing status
    processing_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    processing_priority INTEGER DEFAULT 50 CHECK (processing_priority >= 1 AND processing_priority <= 100),
    processing_started_at TIMESTAMPTZ,
    processing_completed_at TIMESTAMPTZ,
    processing_error TEXT,
    processing_duration_ms INTEGER,

    -- Extraction metadata (populated after processing)
    page_count INTEGER,
    word_count INTEGER,
    total_chunks INTEGER,
    content_summary TEXT,  -- AI-generated 2-3 sentence summary
    keyword_tags TEXT[],   -- Extracted keywords for hybrid search
    key_topics TEXT[],     -- Main topics identified
    extraction_method TEXT CHECK (extraction_method IS NULL OR extraction_method IN ('native', 'ocr', 'vision', 'hybrid')),

    -- Source tracking
    uploaded_by UUID REFERENCES auth.users(id),
    upload_source TEXT NOT NULL CHECK (upload_source IN ('workbench', 'client_portal', 'api')),
    authority TEXT NOT NULL DEFAULT 'consultant' CHECK (authority IN ('client', 'consultant')),

    -- Link to signal (created after successful processing)
    signal_id UUID REFERENCES signals(id),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- Indexes
-- ============================================================================

-- Primary lookup by project
CREATE INDEX idx_document_uploads_project
ON document_uploads(project_id);

-- Queue processing: pending documents ordered by priority
CREATE INDEX idx_document_uploads_queue
ON document_uploads(processing_status, processing_priority DESC, created_at ASC)
WHERE processing_status = 'pending';

-- Deduplication by checksum within project
CREATE INDEX idx_document_uploads_checksum
ON document_uploads(project_id, checksum)
WHERE checksum IS NOT NULL;

-- Filter by document class
CREATE INDEX idx_document_uploads_class
ON document_uploads(project_id, document_class)
WHERE document_class IS NOT NULL;

-- Filter by upload source
CREATE INDEX idx_document_uploads_source
ON document_uploads(project_id, upload_source);

-- ============================================================================
-- Full-Text Search Index on signal_chunks
-- ============================================================================

-- Add FTS index for hybrid search (vector + keyword)
CREATE INDEX IF NOT EXISTS idx_signal_chunks_fts
ON signal_chunks USING gin(to_tsvector('english', content));

-- ============================================================================
-- Extend signal_chunks for document tracking
-- ============================================================================

-- Link chunks to their source document upload
ALTER TABLE signal_chunks
ADD COLUMN IF NOT EXISTS document_upload_id UUID REFERENCES document_uploads(id);

-- Track page number for document chunks
ALTER TABLE signal_chunks
ADD COLUMN IF NOT EXISTS page_number INTEGER;

-- Track section path (e.g., "Requirements > Authentication > OAuth")
ALTER TABLE signal_chunks
ADD COLUMN IF NOT EXISTS section_path TEXT;

-- Index for finding chunks by document
CREATE INDEX IF NOT EXISTS idx_signal_chunks_document
ON signal_chunks(document_upload_id)
WHERE document_upload_id IS NOT NULL;

-- ============================================================================
-- Updated_at Trigger
-- ============================================================================

CREATE OR REPLACE FUNCTION update_document_uploads_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_document_uploads_updated_at ON document_uploads;
CREATE TRIGGER trigger_document_uploads_updated_at
    BEFORE UPDATE ON document_uploads
    FOR EACH ROW
    EXECUTE FUNCTION update_document_uploads_updated_at();

-- ============================================================================
-- Hybrid Search Function
-- ============================================================================

CREATE OR REPLACE FUNCTION hybrid_search_chunks(
    query_text TEXT,
    query_embedding vector(1536),
    p_project_id UUID,
    match_count INTEGER DEFAULT 20,
    vector_weight FLOAT DEFAULT 0.7,
    keyword_weight FLOAT DEFAULT 0.3,
    filter_document_class TEXT DEFAULT NULL,
    filter_authority TEXT DEFAULT NULL,
    filter_section_type TEXT DEFAULT NULL
)
RETURNS TABLE (
    chunk_id UUID,
    signal_id UUID,
    content TEXT,
    metadata JSONB,
    vector_score FLOAT,
    keyword_score FLOAT,
    combined_score FLOAT,
    boosted_score FLOAT
) AS $$
DECLARE
    authority_boost FLOAT;
BEGIN
    RETURN QUERY
    WITH vector_results AS (
        -- Get top candidates by vector similarity
        SELECT
            sc.id,
            sc.signal_id,
            sc.content,
            sc.metadata,
            (1 - (sc.embedding <=> query_embedding))::FLOAT AS v_score
        FROM signal_chunks sc
        JOIN signals s ON sc.signal_id = s.id
        WHERE s.project_id = p_project_id
        AND (filter_document_class IS NULL
             OR sc.metadata->>'document_class' = filter_document_class)
        AND (filter_authority IS NULL
             OR sc.metadata->>'authority' = filter_authority)
        AND (filter_section_type IS NULL
             OR sc.metadata->>'section_type' = filter_section_type)
        ORDER BY sc.embedding <=> query_embedding
        LIMIT match_count * 3  -- Get more candidates for hybrid ranking
    ),
    keyword_results AS (
        -- Get keyword match scores for the vector candidates
        SELECT
            sc.id,
            ts_rank_cd(
                to_tsvector('english', sc.content),
                plainto_tsquery('english', query_text),
                32  -- Normalization: divide by document length
            )::FLOAT AS k_score
        FROM signal_chunks sc
        JOIN signals s ON sc.signal_id = s.id
        WHERE s.project_id = p_project_id
        AND to_tsvector('english', sc.content) @@ plainto_tsquery('english', query_text)
        AND (filter_document_class IS NULL
             OR sc.metadata->>'document_class' = filter_document_class)
        AND (filter_authority IS NULL
             OR sc.metadata->>'authority' = filter_authority)
    ),
    combined AS (
        SELECT
            v.id,
            v.signal_id,
            v.content,
            v.metadata,
            v.v_score,
            COALESCE(k.k_score, 0.0) AS k_score,
            (vector_weight * v.v_score + keyword_weight * COALESCE(k.k_score, 0.0))::FLOAT AS c_score,
            -- Authority boost: client=3x, consultant=2x, research=1.5x, other=1x
            CASE
                WHEN v.metadata->>'authority' = 'client' THEN 3.0
                WHEN v.metadata->>'authority' = 'consultant' THEN 2.0
                WHEN v.metadata->>'authority' = 'research' THEN 1.5
                ELSE 1.0
            END AS auth_boost
        FROM vector_results v
        LEFT JOIN keyword_results k ON v.id = k.id
    )
    SELECT
        c.id AS chunk_id,
        c.signal_id,
        c.content,
        c.metadata,
        c.v_score AS vector_score,
        c.k_score AS keyword_score,
        c.c_score AS combined_score,
        (c.c_score * c.auth_boost)::FLOAT AS boosted_score
    FROM combined c
    ORDER BY (c.c_score * c.auth_boost) DESC
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Row Level Security
-- ============================================================================

ALTER TABLE document_uploads ENABLE ROW LEVEL SECURITY;

-- Users can view document uploads for projects they're members of
CREATE POLICY "Users can view document uploads for their projects"
ON document_uploads FOR SELECT
USING (
    project_id IN (
        SELECT pm.project_id FROM project_members pm
        WHERE pm.user_id = auth.uid()
    )
);

-- Users can insert document uploads for projects they're members of
CREATE POLICY "Users can insert document uploads for their projects"
ON document_uploads FOR INSERT
WITH CHECK (
    project_id IN (
        SELECT pm.project_id FROM project_members pm
        WHERE pm.user_id = auth.uid()
    )
);

-- Users can update document uploads for their projects (for status updates)
CREATE POLICY "Users can update document uploads for their projects"
ON document_uploads FOR UPDATE
USING (
    project_id IN (
        SELECT pm.project_id FROM project_members pm
        WHERE pm.user_id = auth.uid()
    )
);

-- Service role bypass for background processing
CREATE POLICY "Service role can manage all document uploads"
ON document_uploads FOR ALL
USING (auth.role() = 'service_role');

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON TABLE document_uploads IS
'Tracks uploaded documents (PDF, DOCX, XLSX, PPTX, images) and their processing status';

COMMENT ON COLUMN document_uploads.checksum IS
'SHA256 hash for deduplication - same file in same project is detected';

COMMENT ON COLUMN document_uploads.document_class IS
'AI-classified document type: prd, transcript, spec, email, presentation, spreadsheet, wireframe, generic';

COMMENT ON COLUMN document_uploads.processing_priority IS
'1-100, higher = process first. PRDs/transcripts get higher priority than generic docs';

COMMENT ON COLUMN document_uploads.extraction_method IS
'How content was extracted: native (text layer), ocr (Tesseract), vision (Claude), hybrid';

COMMENT ON COLUMN document_uploads.authority IS
'Source authority for retrieval boosting: client (3x), consultant (2x)';

COMMENT ON FUNCTION hybrid_search_chunks IS
'Hybrid search combining vector similarity (0.7) and keyword matching (0.3) with authority boosting';
