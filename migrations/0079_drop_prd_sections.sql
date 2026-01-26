-- migrations/0079_drop_prd_sections.sql
-- Description: Drop prd_sections table - PRD is now generated on-demand from features, personas, VP steps
-- Date: 2025-01-26

-- Note: PRD sections functionality has been replaced by:
-- - Features table for product capabilities
-- - Personas table for user types
-- - VP Steps table for value path/journey
-- - Strategic Foundation entities (business_drivers, competitor_references, stakeholders, risks)
-- PRD documents are now generated on-the-fly as reports when needed.

-- First, drop indexes that reference prd_sections
DROP INDEX IF EXISTS idx_prd_sections_project_slug;
DROP INDEX IF EXISTS idx_prd_sections_project_updated;
DROP INDEX IF EXISTS idx_prd_sections_enrichment_updated_at;
DROP INDEX IF EXISTS idx_prd_sections_is_summary;

-- Drop trigger
DROP TRIGGER IF EXISTS trg_prd_sections_updated_at ON public.prd_sections;

-- Finally, drop the table
DROP TABLE IF EXISTS public.prd_sections CASCADE;

-- Note: The CASCADE will automatically drop any remaining foreign key constraints
-- that reference this table (if any exist from older migrations)
