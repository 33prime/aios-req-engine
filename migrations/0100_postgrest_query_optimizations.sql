-- Migration: PostgREST Query Optimizations
-- Adds RPC functions to eliminate N+1 query patterns

-- =============================================================================
-- 1. get_project_entity_counts: replaces 5 sequential count queries
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_project_entity_counts(p_project_id uuid)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT jsonb_build_object(
    'signals', (SELECT count(*) FROM public.signals WHERE project_id = p_project_id),
    'vp_steps', (SELECT count(*) FROM public.vp_steps WHERE project_id = p_project_id),
    'features', (SELECT count(*) FROM public.features WHERE project_id = p_project_id),
    'personas', (SELECT count(*) FROM public.personas WHERE project_id = p_project_id),
    'business_drivers', (SELECT count(*) FROM public.business_drivers WHERE project_id = p_project_id)
  );
$$;

-- =============================================================================
-- 2. get_chunk_signal_map: batch resolve chunk_id -> signal_id, project_id
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_chunk_signal_map(p_chunk_ids uuid[])
RETURNS TABLE(chunk_id uuid, signal_id uuid, project_id uuid)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT sc.id AS chunk_id, sc.signal_id, s.project_id
  FROM public.signal_chunks sc
  JOIN public.signals s ON s.id = sc.signal_id
  WHERE sc.id = ANY(p_chunk_ids);
$$;

-- =============================================================================
-- 3. get_memory_graph_stats: replaces fetching 1000 rows to count by type
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_memory_graph_stats(p_project_id uuid)
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT jsonb_build_object(
    'total_nodes', (SELECT count(*) FROM public.memory_nodes WHERE project_id = p_project_id AND is_active = true),
    'facts_count', (SELECT count(*) FROM public.memory_nodes WHERE project_id = p_project_id AND is_active = true AND node_type = 'fact'),
    'beliefs_count', (SELECT count(*) FROM public.memory_nodes WHERE project_id = p_project_id AND is_active = true AND node_type = 'belief'),
    'insights_count', (SELECT count(*) FROM public.memory_nodes WHERE project_id = p_project_id AND is_active = true AND node_type = 'insight'),
    'average_belief_confidence', COALESCE(
      (SELECT avg(confidence) FROM public.memory_nodes WHERE project_id = p_project_id AND is_active = true AND node_type = 'belief'),
      0
    ),
    'total_edges', (SELECT count(*) FROM public.memory_edges WHERE project_id = p_project_id),
    'edges_by_type', COALESCE(
      (SELECT jsonb_object_agg(edge_type, cnt) FROM (
        SELECT edge_type, count(*) AS cnt
        FROM public.memory_edges
        WHERE project_id = p_project_id
        GROUP BY edge_type
      ) sub),
      '{}'::jsonb
    )
  );
$$;
