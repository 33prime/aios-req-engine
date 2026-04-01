-- Entity Vectors: dedicated multi-vector embedding storage.
-- Replaces per-table embedding columns as the canonical vector store.
-- Supports identity, intent, relationship, status, and convergence vectors.
-- Existing entity table embedding columns remain for backward compat during transition.

-- ══════════════════════════════════════════════════════════
-- Table
-- ══════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS entity_vectors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entity_id UUID NOT NULL,
    entity_type TEXT NOT NULL,
    vector_type TEXT NOT NULL
        CHECK (vector_type IN ('identity', 'intent', 'relationship', 'status', 'convergence')),
    embedding vector(1536) NOT NULL,
    source_text TEXT,  -- the text that was embedded (for debugging / recomputation, truncated)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(entity_id, entity_type, vector_type)
);

-- ══════════════════════════════════════════════════════════
-- Partial IVF-flat indexes — one per vector_type for efficient filtered search
-- ══════════════════════════════════════════════════════════

CREATE INDEX idx_entity_vectors_identity ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'identity';

CREATE INDEX idx_entity_vectors_intent ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'intent';

CREATE INDEX idx_entity_vectors_relationship ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'relationship';

CREATE INDEX idx_entity_vectors_status ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'status';

CREATE INDEX idx_entity_vectors_convergence ON entity_vectors
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50)
    WHERE vector_type = 'convergence';

-- Lookup indexes
CREATE INDEX idx_entity_vectors_entity ON entity_vectors(entity_id, entity_type);
CREATE INDEX idx_entity_vectors_project ON entity_vectors(project_id);
CREATE INDEX idx_entity_vectors_project_type ON entity_vectors(project_id, entity_type);

-- ══════════════════════════════════════════════════════════
-- RPC: match_entity_vectors
-- Searches ONE vector_type at a time. Caller runs 4 parallel
-- queries and merges results with weighted scoring in Python.
-- ══════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION match_entity_vectors(
    query_embedding vector(1536),
    match_count int,
    filter_project_id uuid,
    filter_vector_type text,
    filter_entity_types text[] DEFAULT NULL
)
RETURNS TABLE (
    entity_id uuid,
    entity_type text,
    vector_type text,
    similarity float4
)
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN QUERY
    SELECT
        ev.entity_id,
        ev.entity_type,
        ev.vector_type,
        (1 - (ev.embedding <=> query_embedding))::float4 AS similarity
    FROM entity_vectors ev
    WHERE ev.project_id = filter_project_id
      AND ev.vector_type = filter_vector_type
      AND (filter_entity_types IS NULL OR ev.entity_type = ANY(filter_entity_types))
    ORDER BY ev.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ══════════════════════════════════════════════════════════
-- RLS
-- ══════════════════════════════════════════════════════════

ALTER TABLE entity_vectors ENABLE ROW LEVEL SECURITY;

CREATE POLICY entity_vectors_service ON entity_vectors
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY entity_vectors_auth_read ON entity_vectors
    FOR SELECT TO authenticated USING (true);

CREATE POLICY entity_vectors_auth_insert ON entity_vectors
    FOR INSERT TO authenticated WITH CHECK (true);

CREATE POLICY entity_vectors_auth_update ON entity_vectors
    FOR UPDATE TO authenticated USING (true) WITH CHECK (true);

CREATE POLICY entity_vectors_auth_delete ON entity_vectors
    FOR DELETE TO authenticated USING (true);
