-- Add brand asset storage for prototype generation
-- Supports logo upload, brand guideline PDFs, reference images

ALTER TABLE prototypes
ADD COLUMN IF NOT EXISTS brand_assets JSONB DEFAULT '[]'::jsonb;
-- Array of: {type: "logo"|"guideline"|"image", url: "supabase_storage_url", label: "", mime_type: ""}
