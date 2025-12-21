-- Phase 2C.2: PRD Section Enrichment Agent
-- Add enrichment JSONB column to prd_sections table for storing enrichment metadata

ALTER TABLE public.prd_sections
ADD COLUMN IF NOT EXISTS enrichment jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Optional metadata columns for tracking enrichment
ALTER TABLE public.prd_sections
ADD COLUMN IF NOT EXISTS enrichment_model text null,
ADD COLUMN IF NOT EXISTS enrichment_prompt_version text null,
ADD COLUMN IF NOT EXISTS enrichment_schema_version text null,
ADD COLUMN IF NOT EXISTS enrichment_updated_at timestamptz null;

-- Index on enrichment_updated_at for filtering recently enriched sections
CREATE INDEX IF NOT EXISTS idx_prd_sections_enrichment_updated_at
ON public.prd_sections (enrichment_updated_at desc)
WHERE enrichment_updated_at IS NOT NULL;
