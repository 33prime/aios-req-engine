-- Migration: Workspace Redesign
-- Date: 2026-01-29
-- Description: Add fields to support new workspace layout with prototype URLs and feature-to-step mapping

-- ============================================================================
-- Projects: Add prototype and pitch fields
-- ============================================================================

-- Prototype URL (deployed app URL)
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS prototype_url TEXT;

-- When prototype was last updated
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS prototype_updated_at TIMESTAMPTZ;

-- The Story / pitch line for requirements canvas
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS pitch_line TEXT;

-- ============================================================================
-- Features: Add direct mapping to value path steps
-- ============================================================================

-- Direct feature-to-step mapping for drag & drop
ALTER TABLE public.features ADD COLUMN IF NOT EXISTS vp_step_id UUID REFERENCES public.vp_steps(id) ON DELETE SET NULL;

-- Index for efficient lookups of features by step
CREATE INDEX IF NOT EXISTS idx_features_vp_step_id ON public.features(vp_step_id) WHERE vp_step_id IS NOT NULL;

-- ============================================================================
-- Comments
-- ============================================================================

COMMENT ON COLUMN public.projects.prototype_url IS 'URL of deployed prototype (Vercel, Replit, etc.)';
COMMENT ON COLUMN public.projects.prototype_updated_at IS 'When the prototype was last updated/deployed';
COMMENT ON COLUMN public.projects.pitch_line IS 'One-line story: "Building X for Y to achieve Z"';
COMMENT ON COLUMN public.features.vp_step_id IS 'Which value path step this feature enables (for canvas drag & drop)';
