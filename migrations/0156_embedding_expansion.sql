-- 0156_embedding_expansion.sql
-- Add embedding columns to unlocks and prototype_feedback tables.
-- Extends match_entities RPC with unlock and prototype_feedback unions.

-- 1. Add embedding column to unlocks
ALTER TABLE unlocks
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

CREATE INDEX IF NOT EXISTS idx_unlocks_embedding
  ON unlocks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)
  WHERE embedding IS NOT NULL;

-- 2. Add embedding + denormalized project_id to prototype_feedback
ALTER TABLE prototype_feedback
  ADD COLUMN IF NOT EXISTS embedding vector(1536),
  ADD COLUMN IF NOT EXISTS project_id UUID;

CREATE INDEX IF NOT EXISTS idx_prototype_feedback_embedding
  ON prototype_feedback USING ivfflat (embedding vector_cosine_ops) WITH (lists = 10)
  WHERE embedding IS NOT NULL;

-- Backfill project_id from session → prototype chain
UPDATE prototype_feedback pf
SET project_id = p.project_id
FROM prototype_sessions ps
JOIN prototypes p ON p.id = ps.prototype_id
WHERE pf.session_id = ps.id
  AND pf.project_id IS NULL;

-- 3. Extend match_entities RPC with unlock + prototype_feedback unions
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
        UNION ALL
        -- 11. Unlocks
        SELECT id, 'unlock'::text, title, (1-(embedding <=> query_embedding))::float4
        FROM public.unlocks WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'unlock' = ANY(filter_entity_types))
        UNION ALL
        -- 12. Prototype Feedback
        SELECT id, 'prototype_feedback'::text, LEFT(content, 80), (1-(embedding <=> query_embedding))::float4
        FROM public.prototype_feedback WHERE project_id = filter_project_id AND embedding IS NOT NULL
          AND (filter_entity_types IS NULL OR 'prototype_feedback' = ANY(filter_entity_types))
    ) AS combined ORDER BY similarity DESC LIMIT match_count;
$$;
