-- Phase 2C: Feature Enrichment Agent
-- Add details JSONB column to features table for storing enrichment metadata

ALTER TABLE public.features
ADD COLUMN IF NOT EXISTS details jsonb NOT NULL DEFAULT '{}'::jsonb;

-- Optional metadata columns for tracking enrichment
ALTER TABLE public.features
ADD COLUMN IF NOT EXISTS details_model text null,
ADD COLUMN IF NOT EXISTS details_prompt_version text null,
ADD COLUMN IF NOT EXISTS details_schema_version text null,
ADD COLUMN IF NOT EXISTS details_updated_at timestamptz null;

-- Index on details_updated_at for filtering recently enriched features
CREATE INDEX IF NOT EXISTS idx_features_details_updated_at
ON public.features (details_updated_at desc)
WHERE details_updated_at IS NOT NULL;
