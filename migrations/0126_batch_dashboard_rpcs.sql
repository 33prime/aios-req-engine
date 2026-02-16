-- =============================================================================
-- Migration 0126: Batch dashboard RPCs for projects list performance
--
-- Eliminates per-project API call loops:
--   1. get_batch_task_stats: aggregate task stats for multiple projects
--   2. get_batch_next_action_inputs: lightweight data for next-action computation
-- =============================================================================

-- =============================================================================
-- 1. get_batch_task_stats: returns task statistics for multiple projects
--    in a single query. Replaces per-project get_task_stats() loop.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_batch_task_stats(p_project_ids uuid[])
RETURNS TABLE(
  project_id uuid,
  total bigint,
  by_status jsonb,
  by_type jsonb,
  client_relevant bigint,
  avg_priority numeric
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    p.id AS project_id,
    COALESCE(stats.total, 0) AS total,
    COALESCE(stats.by_status, '{}'::jsonb) AS by_status,
    COALESCE(stats.by_type, '{}'::jsonb) AS by_type,
    COALESCE(stats.client_relevant, 0) AS client_relevant,
    COALESCE(stats.avg_priority, 0) AS avg_priority
  FROM unnest(p_project_ids) AS p(id)
  LEFT JOIN LATERAL (
    SELECT
      count(*) AS total,
      (SELECT jsonb_object_agg(sub.status, sub.cnt) FROM (
        SELECT status, count(*) AS cnt FROM public.tasks WHERE project_id = p.id GROUP BY status
      ) sub) AS by_status,
      (SELECT jsonb_object_agg(sub.task_type, sub.cnt) FROM (
        SELECT task_type, count(*) AS cnt FROM public.tasks WHERE project_id = p.id GROUP BY task_type
      ) sub) AS by_type,
      count(*) FILTER (WHERE requires_client_input = true) AS client_relevant,
      round(avg(priority_score)::numeric, 2) AS avg_priority
    FROM public.tasks
    WHERE project_id = p.id
  ) stats ON true;
$$;


-- =============================================================================
-- 2. get_batch_next_action_inputs: returns lightweight data needed to compute
--    next actions for multiple projects without loading full BRD.
--    Replaces N calls to the heavy get_brd_workspace_data endpoint.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_batch_next_action_inputs(p_project_ids uuid[])
RETURNS TABLE(
  project_id uuid,
  inputs jsonb
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    p.id AS project_id,
    jsonb_build_object(
      'must_have_unconfirmed', COALESCE(mh.cnt, 0),
      'must_have_first_id', mh.first_id,
      'features_no_evidence', COALESCE(ne.cnt, 0),
      'features_no_evidence_first_id', ne.first_id,
      'high_pain_unconfirmed', COALESCE(hp.cnt, 0),
      'high_pain_first_id', hp.first_id,
      'has_vision', (pr.vision IS NOT NULL AND pr.vision != ''),
      'kpi_count', COALESCE(kpi.cnt, 0),
      'stakeholder_roles', COALESCE(sr.roles, '[]'::jsonb),
      'total_features', COALESCE(tf.cnt, 0)
    ) AS inputs
  FROM unnest(p_project_ids) AS p(id)
  LEFT JOIN public.projects pr ON pr.id = p.id
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt, min(id::text) AS first_id
    FROM public.features
    WHERE project_id = p.id
      AND priority_group = 'must_have'
      AND confirmation_status NOT IN ('confirmed_consultant', 'confirmed_client')
  ) mh ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt, min(id::text) AS first_id
    FROM public.features
    WHERE project_id = p.id
      AND (evidence IS NULL OR evidence = '[]'::jsonb)
  ) ne ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt, min(id::text) AS first_id
    FROM public.business_drivers
    WHERE project_id = p.id
      AND driver_type = 'pain'
      AND severity IN ('critical', 'high')
      AND confirmation_status NOT IN ('confirmed_consultant', 'confirmed_client')
  ) hp ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt
    FROM public.business_drivers
    WHERE project_id = p.id AND driver_type = 'kpi'
  ) kpi ON true
  LEFT JOIN LATERAL (
    SELECT jsonb_agg(DISTINCT lower(role)) AS roles
    FROM public.stakeholders
    WHERE project_id = p.id AND role IS NOT NULL
  ) sr ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt
    FROM public.features
    WHERE project_id = p.id
  ) tf ON true;
$$;
