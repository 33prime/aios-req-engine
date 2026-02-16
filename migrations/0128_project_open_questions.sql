-- =============================================================================
-- Migration 0128: Project open questions lifecycle
--
-- Unifies open questions from 3 scattered sources (fact extraction JSONB,
-- project_memory JSONB, prototype_questions table) into a proper lifecycle
-- with status tracking, entity linking, and action engine integration.
-- =============================================================================

-- =============================================================================
-- 1. project_open_questions table
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.project_open_questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    why_it_matters TEXT,
    context TEXT,
    priority TEXT NOT NULL DEFAULT 'medium'
        CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    category TEXT DEFAULT 'general'
        CHECK (category IN ('requirements', 'stakeholder', 'technical',
                            'process', 'scope', 'validation', 'general')),
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'answered', 'dismissed', 'converted')),
    answer TEXT,
    answered_by TEXT,
    answered_at TIMESTAMPTZ,
    converted_to_type TEXT,
    converted_to_id UUID,
    source_type TEXT NOT NULL DEFAULT 'manual'
        CHECK (source_type IN ('fact_extraction', 'project_memory',
                               'prototype', 'manual', 'system')),
    source_id UUID,
    source_signal_id UUID,
    target_entity_type TEXT,
    target_entity_id UUID,
    suggested_owner TEXT CHECK (suggested_owner IN ('client', 'consultant', 'unknown')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_open_questions_project_status
    ON public.project_open_questions(project_id, status);

CREATE INDEX IF NOT EXISTS idx_open_questions_project_priority
    ON public.project_open_questions(project_id, priority);

CREATE INDEX IF NOT EXISTS idx_open_questions_source
    ON public.project_open_questions(source_type, source_id);

CREATE INDEX IF NOT EXISTS idx_open_questions_target
    ON public.project_open_questions(target_entity_type, target_entity_id);

-- Updated_at trigger
CREATE OR REPLACE TRIGGER set_open_questions_updated_at
    BEFORE UPDATE ON public.project_open_questions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- 2. RLS policies
-- =============================================================================

ALTER TABLE public.project_open_questions ENABLE ROW LEVEL SECURITY;

-- Service role: full access
CREATE POLICY "service_role_all_open_questions"
    ON public.project_open_questions
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- Authenticated: access questions for projects they can access
CREATE POLICY "authenticated_select_open_questions"
    ON public.project_open_questions
    FOR SELECT
    TO authenticated
    USING (true);

CREATE POLICY "authenticated_insert_open_questions"
    ON public.project_open_questions
    FOR INSERT
    TO authenticated
    WITH CHECK (true);

CREATE POLICY "authenticated_update_open_questions"
    ON public.project_open_questions
    FOR UPDATE
    TO authenticated
    USING (true)
    WITH CHECK (true);

CREATE POLICY "authenticated_delete_open_questions"
    ON public.project_open_questions
    FOR DELETE
    TO authenticated
    USING (true);

-- =============================================================================
-- 3. Extend get_batch_next_action_inputs RPC with question/staleness data
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
      'total_features', COALESCE(tf.cnt, 0),
      -- New fields for unified action engine
      'open_question_count', COALESCE(oq.total_open, 0),
      'critical_question_count', COALESCE(oq.critical_open, 0),
      'days_since_last_signal', COALESCE(ls.days_since, NULL),
      'stale_entity_count', COALESCE(se.cnt, 0)
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
  ) tf ON true
  LEFT JOIN LATERAL (
    SELECT
      count(*) FILTER (WHERE status = 'open') AS total_open,
      count(*) FILTER (WHERE status = 'open' AND priority = 'critical') AS critical_open
    FROM public.project_open_questions
    WHERE project_id = p.id
  ) oq ON true
  LEFT JOIN LATERAL (
    SELECT EXTRACT(DAY FROM NOW() - MAX(created_at))::int AS days_since
    FROM public.signals
    WHERE project_id = p.id
  ) ls ON true
  LEFT JOIN LATERAL (
    SELECT count(*) AS cnt
    FROM public.data_entities
    WHERE project_id = p.id AND is_stale = true
  ) se ON true;
$$;
