-- =============================================================================
-- Migration 0147: Batch dashboard V2 RPCs for home page performance
--
-- Consolidates N+1 query patterns into batch RPCs:
--   1. get_batch_portal_sync: portal sync status for multiple projects (1 query)
--   2. get_batch_pending_tasks: recent pending tasks across projects (1 query)
--   3. get_batch_owner_profiles: owner profiles for multiple users (1 query)
--
-- Combined with existing get_batch_task_stats + get_batch_next_action_inputs,
-- the home page now loads in ~5 queries total instead of ~40+.
-- =============================================================================


-- =============================================================================
-- 1. get_batch_portal_sync: returns portal sync status for multiple projects.
--    Replaces N × getCollaborationCurrent() calls, each of which ran 10-14
--    DB queries internally.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_batch_portal_sync(p_project_ids uuid[])
RETURNS TABLE(
  project_id uuid,
  portal_enabled boolean,
  portal_phase text,
  questions_sent bigint,
  questions_completed bigint,
  questions_in_progress bigint,
  questions_pending bigint,
  documents_sent bigint,
  documents_completed bigint,
  documents_in_progress bigint,
  documents_pending bigint,
  clients_invited bigint,
  clients_active bigint,
  last_client_activity timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    p.id AS project_id,
    COALESCE(proj.portal_enabled, false) AS portal_enabled,
    COALESCE(proj.portal_phase, 'pre_call') AS portal_phase,
    -- Questions
    COALESCE(ir.q_sent, 0) AS questions_sent,
    COALESCE(ir.q_completed, 0) AS questions_completed,
    COALESCE(ir.q_in_progress, 0) AS questions_in_progress,
    COALESCE(ir.q_pending, 0) AS questions_pending,
    -- Documents
    COALESCE(ir.d_sent, 0) AS documents_sent,
    COALESCE(ir.d_completed, 0) AS documents_completed,
    COALESCE(ir.d_in_progress, 0) AS documents_in_progress,
    COALESCE(ir.d_pending, 0) AS documents_pending,
    -- Clients
    COALESCE(mem.clients_invited, 0) AS clients_invited,
    COALESCE(mem.clients_active, 0) AS clients_active,
    -- Last activity
    ir.last_activity AS last_client_activity
  FROM unnest(p_project_ids) AS p(id)
  LEFT JOIN public.projects proj ON proj.id = p.id
  LEFT JOIN LATERAL (
    SELECT
      count(*) FILTER (WHERE request_type = 'question') AS q_sent,
      count(*) FILTER (WHERE request_type = 'question' AND status = 'complete') AS q_completed,
      count(*) FILTER (WHERE request_type = 'question' AND status = 'in_progress') AS q_in_progress,
      count(*) FILTER (WHERE request_type = 'question' AND status NOT IN ('complete', 'in_progress')) AS q_pending,
      count(*) FILTER (WHERE request_type = 'document') AS d_sent,
      count(*) FILTER (WHERE request_type = 'document' AND status = 'complete') AS d_completed,
      count(*) FILTER (WHERE request_type = 'document' AND status = 'in_progress') AS d_in_progress,
      count(*) FILTER (WHERE request_type = 'document' AND status NOT IN ('complete', 'in_progress')) AS d_pending,
      max(completed_at) AS last_activity
    FROM public.info_requests
    WHERE project_id = p.id
  ) ir ON true
  LEFT JOIN LATERAL (
    SELECT
      count(*) AS clients_invited,
      count(*) FILTER (WHERE accepted_at IS NOT NULL) AS clients_active
    FROM public.project_members
    WHERE project_id = p.id AND role = 'client'
  ) mem ON true;
$$;


-- =============================================================================
-- 2. get_batch_pending_tasks: returns recent pending tasks across multiple
--    projects in a single query. Replaces N × listTasks() round-trips.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_batch_pending_tasks(
  p_project_ids uuid[],
  p_limit int DEFAULT 10,
  p_max_age_days int DEFAULT 10
)
RETURNS TABLE(
  id uuid,
  project_id uuid,
  title text,
  task_type text,
  priority_score numeric,
  status text,
  requires_client_input boolean,
  source_type text,
  created_at timestamptz
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    t.id,
    t.project_id,
    t.title,
    t.task_type,
    t.priority_score,
    t.status,
    t.requires_client_input,
    t.source_type,
    t.created_at
  FROM public.tasks t
  WHERE t.project_id = ANY(p_project_ids)
    AND t.status = 'pending'
    AND t.created_at >= now() - make_interval(days => p_max_age_days)
  ORDER BY t.created_at DESC
  LIMIT p_limit;
$$;


-- =============================================================================
-- 3. get_batch_owner_profiles: returns profile data for multiple user IDs.
--    Replaces sequential get_profile_by_user_id() loop in list_all_projects.
-- =============================================================================

CREATE OR REPLACE FUNCTION public.get_batch_owner_profiles(p_user_ids uuid[])
RETURNS TABLE(
  user_id uuid,
  first_name text,
  last_name text,
  photo_url text
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    pr.user_id,
    pr.first_name,
    pr.last_name,
    pr.photo_url
  FROM public.profiles pr
  WHERE pr.user_id = ANY(p_user_ids);
$$;
