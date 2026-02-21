-- 0149_vector_foundation.sql
-- Vector foundation for unified retrieval: entity embeddings, memory node embeddings,
-- GIN index on chunk metadata, and cross-entity vector search functions.

-- 1. GIN index on signal_chunks.metadata for JSONB containment queries
CREATE INDEX IF NOT EXISTS idx_signal_chunks_metadata_gin
    ON signal_chunks USING gin (metadata jsonb_path_ops);

-- 2. Entity embedding columns (9 entity tables)
ALTER TABLE features ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE personas ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE vp_steps ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE stakeholders ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE business_drivers ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE constraints ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE data_entities ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE competitor_references ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- 3. Memory node enhancements
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS embedding vector(1536);
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS chunk_id UUID REFERENCES signal_chunks(id);
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS source_quote TEXT;
ALTER TABLE memory_nodes ADD COLUMN IF NOT EXISTS speaker_name TEXT;
CREATE INDEX IF NOT EXISTS idx_memory_nodes_chunk ON memory_nodes(chunk_id) WHERE chunk_id IS NOT NULL;

-- 4. Unified cross-entity vector search function
CREATE OR REPLACE FUNCTION match_entities(
    query_embedding vector(1536),
    match_count int,
    filter_project_id uuid,
    filter_entity_types text[] DEFAULT NULL
) RETURNS TABLE (entity_id uuid, entity_type text, entity_name text, similarity float4)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = 'public' AS $$
    SELECT * FROM (
        SELECT id, 'feature'::text, name, (1-(embedding <=> query_embedding))::float4 AS similarity
        FROM public.features WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'feature' = ANY(filter_entity_types))
        UNION ALL
        SELECT id, 'persona'::text, name, (1-(embedding <=> query_embedding))::float4
        FROM public.personas WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'persona' = ANY(filter_entity_types))
        UNION ALL
        SELECT id, 'stakeholder'::text, name, (1-(embedding <=> query_embedding))::float4
        FROM public.stakeholders WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'stakeholder' = ANY(filter_entity_types))
        UNION ALL
        SELECT id, 'workflow'::text, name, (1-(embedding <=> query_embedding))::float4
        FROM public.workflows WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'workflow' = ANY(filter_entity_types))
        UNION ALL
        SELECT id, 'vp_step'::text, label, (1-(embedding <=> query_embedding))::float4
        FROM public.vp_steps WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'vp_step' = ANY(filter_entity_types))
        UNION ALL
        SELECT id, 'business_driver'::text, description, (1-(embedding <=> query_embedding))::float4
        FROM public.business_drivers WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'business_driver' = ANY(filter_entity_types))
        UNION ALL
        SELECT id, 'constraint'::text, title, (1-(embedding <=> query_embedding))::float4
        FROM public.constraints WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'constraint' = ANY(filter_entity_types))
        UNION ALL
        SELECT id, 'data_entity'::text, name, (1-(embedding <=> query_embedding))::float4
        FROM public.data_entities WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'data_entity' = ANY(filter_entity_types))
        UNION ALL
        SELECT id, 'competitor'::text, name, (1-(embedding <=> query_embedding))::float4
        FROM public.competitor_references WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'competitor' = ANY(filter_entity_types))
    ) AS combined ORDER BY similarity DESC LIMIT match_count;
$$;

-- 5. Memory node vector search function
CREATE OR REPLACE FUNCTION match_memory_nodes(
    query_embedding vector(1536),
    match_count int,
    filter_project_id uuid,
    filter_node_type text DEFAULT NULL
) RETURNS TABLE (node_id uuid, node_type text, summary text, content text, confidence float, similarity float4)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = 'public' AS $$
    SELECT mn.id, mn.node_type, mn.summary, mn.content, mn.confidence,
           (1-(mn.embedding <=> query_embedding))::float4 AS similarity
    FROM public.memory_nodes mn
    WHERE mn.project_id = filter_project_id AND mn.is_active = TRUE AND mn.embedding IS NOT NULL
      AND (filter_node_type IS NULL OR mn.node_type = filter_node_type)
    ORDER BY mn.embedding <=> query_embedding LIMIT match_count;
$$;
