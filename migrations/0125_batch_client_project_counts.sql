-- =============================================================================
-- Migration 0125: Batch RPC functions for client/project loading performance
--
-- Eliminates N+1 query patterns:
--   1. get_client_summary_counts: batch project + stakeholder counts per client
--   2. get_batch_project_entity_counts: batch entity counts for multiple projects
--
-- Also adds missing FK indexes identified in performance audit.
-- =============================================================================

-- =============================================================================
-- 1. get_client_summary_counts: returns project_count + stakeholder_count
--    for an array of client IDs in a single query.
--    Replaces: get_client_project_count() + get_client_stakeholder_count() per row
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_client_summary_counts(p_client_ids uuid[])
RETURNS TABLE(client_id uuid, project_count bigint, stakeholder_count bigint)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    c.id AS client_id,
    COALESCE(pc.cnt, 0) AS project_count,
    COALESCE(sc.cnt, 0) AS stakeholder_count
  FROM unnest(p_client_ids) AS c(id)
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt
    FROM public.projects p
    WHERE p.client_id = c.id
  ) pc ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt
    FROM public.stakeholders s
    WHERE s.project_id IN (
      SELECT p2.id FROM public.projects p2 WHERE p2.client_id = c.id
    )
  ) sc ON true;
$$;


-- =============================================================================
-- 2. get_batch_project_entity_counts: returns entity counts for multiple
--    projects at once. Replaces per-project RPC loop in get_client_projects().
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_batch_project_entity_counts(p_project_ids uuid[])
RETURNS TABLE(project_id uuid, counts jsonb)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    p.id AS project_id,
    jsonb_build_object(
      'signals',          COALESCE(sig.cnt, 0),
      'vp_steps',         COALESCE(vps.cnt, 0),
      'features',         COALESCE(feat.cnt, 0),
      'personas',         COALESCE(pers.cnt, 0),
      'business_drivers', COALESCE(bd.cnt, 0)
    ) AS counts
  FROM unnest(p_project_ids) AS p(id)
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt FROM public.signals WHERE project_id = p.id
  ) sig ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt FROM public.vp_steps WHERE project_id = p.id
  ) vps ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt FROM public.features WHERE project_id = p.id
  ) feat ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt FROM public.personas WHERE project_id = p.id
  ) pers ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt FROM public.business_drivers WHERE project_id = p.id
  ) bd ON true;
$$;


-- =============================================================================
-- 3. Missing FK indexes (from performance audit)
-- =============================================================================

-- clients.created_by — FK to auth.users, no index
CREATE INDEX IF NOT EXISTS idx_clients_created_by
  ON public.clients(created_by);

-- signals.run_id — FK to jobs, no index
CREATE INDEX IF NOT EXISTS idx_signals_run_id
  ON public.signals(run_id);

-- stakeholders.extracted_from_signal_id — FK to signals, no index
CREATE INDEX IF NOT EXISTS idx_stakeholders_extracted_from_signal_id
  ON public.stakeholders(extracted_from_signal_id)
  WHERE extracted_from_signal_id IS NOT NULL;

-- data_entities: composite for common filter patterns
CREATE INDEX IF NOT EXISTS idx_data_entities_project_confirmation
  ON public.data_entities(project_id, confirmation_status);

-- workflows: composite for current/future pairing queries
CREATE INDEX IF NOT EXISTS idx_workflows_project_state_type
  ON public.workflows(project_id, state_type);

-- vp_steps: composite for ordering within workflow
CREATE INDEX IF NOT EXISTS idx_vp_steps_workflow_sort
  ON public.vp_steps(workflow_id, sort_order)
  WHERE workflow_id IS NOT NULL;
