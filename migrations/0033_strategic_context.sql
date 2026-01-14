-- Migration: Strategic Context & Stakeholders
-- Description: Add tables for strategic context (replacing PRD) and stakeholder tracking
-- Date: 2025-01-05

-- =========================
-- Strategic Context Table
-- =========================

CREATE TABLE IF NOT EXISTS strategic_context (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL UNIQUE REFERENCES projects(id) ON DELETE CASCADE,

  -- Project type determines which sections to show
  project_type TEXT DEFAULT 'internal'
    CHECK (project_type IN ('internal', 'market_product')),

  -- Executive Summary (auto-generated, consultant-editable)
  executive_summary TEXT,

  -- The Opportunity (structured)
  -- Format: { problem_statement, business_opportunity, client_motivation, strategic_fit, market_gap }
  opportunity JSONB DEFAULT '{}'::jsonb,

  -- The Risks (structured)
  -- Format: [{ category, description, severity, mitigation, evidence_ids }]
  risks JSONB DEFAULT '[]'::jsonb,

  -- Investment Case (differs by project_type)
  -- Internal: { efficiency_gains, cost_reduction, risk_mitigation, roi_estimate, roi_timeframe }
  -- Market: { tam, sam, som, revenue_projection, market_timing, competitive_advantage }
  investment_case JSONB DEFAULT '{}'::jsonb,

  -- Success Metrics / KPIs
  -- Format: [{ metric, target, current, evidence_ids }]
  success_metrics JSONB DEFAULT '[]'::jsonb,

  -- Project Constraints
  -- Format: { budget, timeline, team_size, technical[], compliance[] }
  constraints JSONB DEFAULT '{}'::jsonb,

  -- Evidence & Confirmation (follows existing patterns)
  evidence JSONB DEFAULT '[]'::jsonb,
  confirmation_status TEXT DEFAULT 'ai_generated'
    CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
  confirmed_by UUID,
  confirmed_at TIMESTAMPTZ,

  -- Enrichment tracking
  enrichment_status TEXT DEFAULT 'none'
    CHECK (enrichment_status IN ('none', 'enriched', 'stale')),
  enriched_at TIMESTAMPTZ,
  generation_model TEXT,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_strategic_context_project ON strategic_context(project_id);

-- =========================
-- Stakeholders Table
-- =========================

CREATE TABLE IF NOT EXISTS stakeholders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- Identity
  name TEXT NOT NULL,
  email TEXT,  -- Contact email
  role TEXT,  -- Job title
  organization TEXT,  -- Company/department

  -- Stakeholder classification
  stakeholder_type TEXT NOT NULL
    CHECK (stakeholder_type IN ('champion', 'sponsor', 'blocker', 'influencer', 'end_user')),
  influence_level TEXT DEFAULT 'medium'
    CHECK (influence_level IN ('high', 'medium', 'low')),

  -- Details
  priorities JSONB DEFAULT '[]'::jsonb,  -- What matters to them
  concerns JSONB DEFAULT '[]'::jsonb,    -- Their worries/objections
  notes TEXT,

  -- Link to persona (if this stakeholder maps to a persona)
  linked_persona_id UUID REFERENCES personas(id) ON DELETE SET NULL,

  -- Evidence & Confirmation
  evidence JSONB DEFAULT '[]'::jsonb,
  confirmation_status TEXT DEFAULT 'ai_generated'
    CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
  confirmed_by UUID,
  confirmed_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stakeholders_project ON stakeholders(project_id);
CREATE INDEX IF NOT EXISTS idx_stakeholders_type ON stakeholders(project_id, stakeholder_type);
CREATE INDEX IF NOT EXISTS idx_stakeholders_persona ON stakeholders(linked_persona_id) WHERE linked_persona_id IS NOT NULL;

-- =========================
-- Comments
-- =========================

COMMENT ON TABLE strategic_context IS
  'Strategic context for a project - the big picture business case, replacing PRD';

COMMENT ON COLUMN strategic_context.project_type IS
  'internal = internal software project, market_product = product for market';

COMMENT ON COLUMN strategic_context.opportunity IS
  'Structured opportunity data: problem_statement, business_opportunity, client_motivation, strategic_fit';

COMMENT ON COLUMN strategic_context.risks IS
  'Array of risks: [{category, description, severity, mitigation, evidence_ids}]';

COMMENT ON COLUMN strategic_context.investment_case IS
  'ROI/investment data - structure differs by project_type';

COMMENT ON COLUMN strategic_context.success_metrics IS
  'KPIs: [{metric, target, current, evidence_ids}]';

COMMENT ON COLUMN strategic_context.constraints IS
  'Project constraints: budget, timeline, team_size, technical[], compliance[]';

COMMENT ON TABLE stakeholders IS
  'Project stakeholders with influence tracking';

COMMENT ON COLUMN stakeholders.stakeholder_type IS
  'champion = internal advocate, sponsor = decision maker, blocker = opposition, influencer = opinion leader, end_user = actual user';

COMMENT ON COLUMN stakeholders.influence_level IS
  'Level of influence on project decisions';

COMMENT ON COLUMN stakeholders.linked_persona_id IS
  'Optional link to a persona if this stakeholder represents a user type';
