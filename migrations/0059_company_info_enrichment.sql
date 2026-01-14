-- Migration: Company Info Enrichment
-- Description: Add enrichment fields for Firecrawl + AI company analysis
-- Date: 2025-01-14

-- =========================
-- Add enrichment fields to company_info
-- =========================

-- Core enrichment data (HTML for Quill display)
ALTER TABLE company_info
ADD COLUMN IF NOT EXISTS unique_selling_point TEXT,
ADD COLUMN IF NOT EXISTS customers TEXT,              -- HTML (Quill)
ADD COLUMN IF NOT EXISTS products_services TEXT,      -- HTML (Quill)
ADD COLUMN IF NOT EXISTS industry_overview TEXT,      -- HTML (Quill)
ADD COLUMN IF NOT EXISTS industry_trends TEXT,        -- HTML (Quill)
ADD COLUMN IF NOT EXISTS fast_facts TEXT;             -- HTML (Quill)

-- Classification fields
ALTER TABLE company_info
ADD COLUMN IF NOT EXISTS company_type TEXT
    CHECK (company_type IN ('Startup', 'SMB', 'Enterprise', 'Agency', 'Government', 'Non-Profit')),
ADD COLUMN IF NOT EXISTS industry_display TEXT,       -- "PropTech • Construction"
ADD COLUMN IF NOT EXISTS industry_naics TEXT;         -- NAICS classification

-- Context data (stored but not displayed in UI)
ALTER TABLE company_info
ADD COLUMN IF NOT EXISTS data_dictionary JSONB DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS industry_use_cases JSONB DEFAULT '[]'::jsonb;

-- Source tracking
ALTER TABLE company_info
ADD COLUMN IF NOT EXISTS enrichment_source TEXT
    CHECK (enrichment_source IN ('website_scrape', 'ai_inference', 'client_portal', 'manual')),
ADD COLUMN IF NOT EXISTS enrichment_confidence FLOAT DEFAULT 0.5,
ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS raw_website_content TEXT;    -- Cache scraped markdown

-- Field-level confirmation tracking
ALTER TABLE company_info
ADD COLUMN IF NOT EXISTS confirmed_fields JSONB DEFAULT '{}'::jsonb;
-- Example: {"industry": "confirmed_client", "unique_selling_point": "ai_generated"}

-- =========================
-- Comments
-- =========================

COMMENT ON COLUMN company_info.unique_selling_point IS 'Core value proposition (2 sentences)';
COMMENT ON COLUMN company_info.customers IS 'HTML describing target customers/segments';
COMMENT ON COLUMN company_info.products_services IS 'HTML describing main offerings';
COMMENT ON COLUMN company_info.industry_overview IS 'HTML with industry context (3-4 paragraphs)';
COMMENT ON COLUMN company_info.industry_trends IS 'HTML with current market trends';
COMMENT ON COLUMN company_info.fast_facts IS 'HTML with key market facts: market size, tech trends, pain points';
COMMENT ON COLUMN company_info.company_type IS 'Company classification: Startup, SMB, Enterprise, Agency, Government, Non-Profit';
COMMENT ON COLUMN company_info.industry_display IS 'Formatted industry string: "Industry1 • Industry2"';
COMMENT ON COLUMN company_info.industry_naics IS 'NAICS-style industry classification';
COMMENT ON COLUMN company_info.data_dictionary IS 'Product/service vocabulary for context (not displayed in UI)';
COMMENT ON COLUMN company_info.industry_use_cases IS 'Common use cases for this industry type';
COMMENT ON COLUMN company_info.enrichment_source IS 'How enrichment data was obtained';
COMMENT ON COLUMN company_info.enrichment_confidence IS 'Confidence score for enrichment data (0-1)';
COMMENT ON COLUMN company_info.raw_website_content IS 'Cached scraped markdown from company website';
COMMENT ON COLUMN company_info.confirmed_fields IS 'Field-level confirmation status tracking';
