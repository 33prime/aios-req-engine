-- Phase 2C.3: VP Step Enrichment Agent
-- Add enrichment JSONB column to vp_steps table for storing enrichment metadata

ALTER TABLE public.vp_steps
ADD COLUMN IF NOT EXISTS enrichment jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Optional metadata columns for tracking enrichment
ALTER TABLE public.vp_steps
ADD COLUMN IF NOT EXISTS enrichment_model text null,
ADD COLUMN IF NOT EXISTS enrichment_prompt_version text null,
ADD COLUMN IF NOT EXISTS enrichment_schema_version text null,
ADD COLUMN IF NOT EXISTS enrichment_updated_at timestamptz null;

-- Index on enrichment_updated_at for filtering recently enriched steps
CREATE INDEX IF NOT EXISTS idx_vp_steps_enrichment_updated_at
ON public.vp_steps (enrichment_updated_at desc)
WHERE enrichment_updated_at IS NOT NULL;
