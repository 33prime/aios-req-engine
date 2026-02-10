-- Migration 0107: Add RLS policies for prototype_sessions and prototype_feedback
--
-- These tables had RLS enabled but NO policies, meaning only service_role could
-- access them. When the auth middleware mutates the shared Supabase client's auth
-- state (replacing service_role with the user's JWT), operations fail with 42501.
-- Adding proper authenticated-role policies fixes this.

-- ============================================================================
-- Helper: check project access via prototype_id
-- ============================================================================

CREATE OR REPLACE FUNCTION can_access_prototype(proto_id uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE SECURITY DEFINER
SET search_path TO ''
AS $$
DECLARE
  proj_id UUID;
BEGIN
  SELECT project_id INTO proj_id
  FROM public.prototypes
  WHERE id = proto_id;

  IF proj_id IS NULL THEN
    RETURN FALSE;
  END IF;

  RETURN public.can_access_project(proj_id);
END;
$$;

-- ============================================================================
-- prototype_sessions policies
-- ============================================================================

CREATE POLICY prototype_sessions_select ON prototype_sessions
  FOR SELECT TO authenticated
  USING (can_access_prototype(prototype_id));

CREATE POLICY prototype_sessions_insert ON prototype_sessions
  FOR INSERT TO authenticated
  WITH CHECK (can_access_prototype(prototype_id));

CREATE POLICY prototype_sessions_update ON prototype_sessions
  FOR UPDATE TO authenticated
  USING (can_access_prototype(prototype_id));

CREATE POLICY prototype_sessions_delete ON prototype_sessions
  FOR DELETE TO authenticated
  USING (can_access_prototype(prototype_id));

-- ============================================================================
-- prototype_feedback policies
-- ============================================================================

CREATE POLICY prototype_feedback_select ON prototype_feedback
  FOR SELECT TO authenticated
  USING (can_access_prototype(
    (SELECT prototype_id FROM prototype_sessions WHERE id = session_id)
  ));

CREATE POLICY prototype_feedback_insert ON prototype_feedback
  FOR INSERT TO authenticated
  WITH CHECK (can_access_prototype(
    (SELECT prototype_id FROM prototype_sessions WHERE id = session_id)
  ));

CREATE POLICY prototype_feedback_update ON prototype_feedback
  FOR UPDATE TO authenticated
  USING (can_access_prototype(
    (SELECT prototype_id FROM prototype_sessions WHERE id = session_id)
  ));

CREATE POLICY prototype_feedback_delete ON prototype_feedback
  FOR DELETE TO authenticated
  USING (can_access_prototype(
    (SELECT prototype_id FROM prototype_sessions WHERE id = session_id)
  ));
