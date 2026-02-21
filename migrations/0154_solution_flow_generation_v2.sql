-- 0154_solution_flow_generation_v2.sql
-- Solution Flow Generation v2: parallel generation, confirmed-as-signal preservation,
-- staleness cascade, background narratives, step embeddings.

-- 1. New columns on solution_flow_steps
ALTER TABLE solution_flow_steps
  ADD COLUMN IF NOT EXISTS confidence_impact FLOAT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS background_narrative TEXT DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS generation_version INTEGER NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS preserved_from_version INTEGER DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- 2. Generation metadata on solution_flows
ALTER TABLE solution_flows
  ADD COLUMN IF NOT EXISTS last_readiness_check JSONB DEFAULT NULL,
  ADD COLUMN IF NOT EXISTS generation_metadata JSONB DEFAULT NULL;

-- 3. Embedding index (ivfflat for cosine similarity)
CREATE INDEX IF NOT EXISTS idx_solution_flow_steps_embedding
  ON solution_flow_steps USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)
  WHERE embedding IS NOT NULL;

-- 4. Extend match_entities RPC to include solution_flow_step
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
        UNION ALL
        SELECT id, 'solution_flow_step'::text, title, (1-(embedding <=> query_embedding))::float4
        FROM public.solution_flow_steps WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'solution_flow_step' = ANY(filter_entity_types))
    ) AS combined ORDER BY similarity DESC LIMIT match_count;
$$;
