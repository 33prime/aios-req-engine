-- Migration: Brand Data & Design Selection
-- Description: Add brand extraction columns to company_info and design_selection to prototypes
-- Date: 2025-02-03

-- =========================
-- Brand data on company_info
-- =========================

ALTER TABLE company_info
ADD COLUMN IF NOT EXISTS logo_url TEXT,
ADD COLUMN IF NOT EXISTS brand_colors JSONB,
ADD COLUMN IF NOT EXISTS typography JSONB,
ADD COLUMN IF NOT EXISTS design_characteristics JSONB,
ADD COLUMN IF NOT EXISTS brand_scraped_at TIMESTAMPTZ;

COMMENT ON COLUMN company_info.logo_url IS 'Logo URL extracted from company website';
COMMENT ON COLUMN company_info.brand_colors IS 'Brand colors extracted from website: ["#hex", ...]';
COMMENT ON COLUMN company_info.typography IS 'Typography: {heading_font, body_font}';
COMMENT ON COLUMN company_info.design_characteristics IS 'Design characteristics: {overall_feel, spacing, corners, visual_weight}';
COMMENT ON COLUMN company_info.brand_scraped_at IS 'When brand data was last scraped';

-- =========================
-- Design selection on prototypes
-- =========================

ALTER TABLE prototypes
ADD COLUMN IF NOT EXISTS design_selection JSONB;

COMMENT ON COLUMN prototypes.design_selection IS 'Design selection: {option_id, tokens: {primary_color, ...}, source}';
