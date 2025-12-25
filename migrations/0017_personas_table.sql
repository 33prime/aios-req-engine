-- Migration: Personas Table
-- Description: Extract personas from prd_sections JSON to dedicated table with stable IDs
-- Date: 2025-12-25
-- Phase: 0 - Foundation

-- =========================
-- Create personas table
-- =========================
CREATE TABLE IF NOT EXISTS personas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL,
  slug TEXT NOT NULL,  -- stable identifier (e.g., "sarah-chen-pm")
  name TEXT NOT NULL,
  role TEXT,
  demographics JSONB DEFAULT '{}'::jsonb,
  psychographics JSONB DEFAULT '{}'::jsonb,
  goals TEXT[] DEFAULT ARRAY[]::TEXT[],
  pain_points TEXT[] DEFAULT ARRAY[]::TEXT[],
  description TEXT,
  related_features UUID[] DEFAULT ARRAY[]::UUID[],
  related_vp_steps UUID[] DEFAULT ARRAY[]::UUID[],

  -- Confirmation tracking (universal model)
  confirmation_status TEXT DEFAULT 'ai_generated'
    CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
  confirmed_by UUID,
  confirmed_at TIMESTAMPTZ,

  -- Timestamps
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- Constraints
  UNIQUE(project_id, slug)
);

-- =========================
-- Indexes
-- =========================
CREATE INDEX IF NOT EXISTS idx_personas_project
  ON personas(project_id);

CREATE INDEX IF NOT EXISTS idx_personas_project_slug
  ON personas(project_id, slug);

CREATE INDEX IF NOT EXISTS idx_personas_confirmation_status
  ON personas(project_id, confirmation_status);

CREATE INDEX IF NOT EXISTS idx_personas_confirmed_by
  ON personas(confirmed_by, confirmed_at DESC) WHERE confirmed_by IS NOT NULL;

-- =========================
-- Trigger for updated_at
-- =========================
DROP TRIGGER IF EXISTS trg_personas_updated_at ON personas;
CREATE TRIGGER trg_personas_updated_at
  BEFORE UPDATE ON personas
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- =========================
-- Comments
-- =========================
COMMENT ON TABLE personas IS
  'User personas with stable IDs for surgical updates and routing';

COMMENT ON COLUMN personas.slug IS
  'Stable identifier (kebab-case, e.g., "sarah-chen-pm") for routing claims';

COMMENT ON COLUMN personas.name IS
  'Persona display name (e.g., "Sarah Chen")';

COMMENT ON COLUMN personas.role IS
  'Persona role/title (e.g., "Product Manager")';

COMMENT ON COLUMN personas.demographics IS
  'Demographic details as JSONB: {age_range, location, company_type, etc.}';

COMMENT ON COLUMN personas.psychographics IS
  'Psychographic details as JSONB: {values, motivations, behaviors, etc.}';

COMMENT ON COLUMN personas.goals IS
  'Array of persona goals/objectives';

COMMENT ON COLUMN personas.pain_points IS
  'Array of persona pain points/frustrations';

COMMENT ON COLUMN personas.description IS
  'Optional longer-form persona description';

COMMENT ON COLUMN personas.related_features IS
  'Array of feature UUIDs this persona uses/needs';

COMMENT ON COLUMN personas.related_vp_steps IS
  'Array of VP step UUIDs this persona interacts with';

COMMENT ON COLUMN personas.confirmation_status IS
  'Confirmation workflow status: ai_generated → confirmed_consultant → needs_client → confirmed_client';

-- =========================
-- Data Migration Script
-- =========================
-- This script extracts personas from prd_sections.enrichment.enhanced_fields.personas
-- and creates persona records with stable slugs

-- TEMPORARILY DISABLED: Run this manually after projects table is created
/*
DO $$
DECLARE
  section_record RECORD;
  persona_json JSONB;
  persona_slug TEXT;
  persona_name TEXT;
BEGIN
  -- Iterate through all PRD sections with slug='personas' that have enrichment data
  FOR section_record IN
    SELECT
      id,
      project_id,
      enrichment
    FROM prd_sections
    WHERE slug = 'personas'
      AND enrichment IS NOT NULL
      AND jsonb_path_exists(enrichment, '$.enhanced_fields.personas')
  LOOP
    -- Extract personas array from enrichment
    FOR persona_json IN
      SELECT jsonb_array_elements(section_record.enrichment->'enhanced_fields'->'personas')
    LOOP
      -- Generate slug from name (convert to lowercase, replace spaces with hyphens)
      persona_name := persona_json->>'name';
      persona_slug := lower(regexp_replace(persona_name, '[^a-zA-Z0-9]+', '-', 'g'));
      persona_slug := trim(both '-' from persona_slug);

      -- Insert persona if it doesn't already exist
      INSERT INTO personas (
        project_id,
        slug,
        name,
        role,
        demographics,
        psychographics,
        goals,
        pain_points,
        description,
        related_features,
        related_vp_steps,
        confirmation_status
      )
      VALUES (
        section_record.project_id,
        persona_slug,
        persona_name,
        persona_json->>'role',
        COALESCE(persona_json->'demographics', '{}'::jsonb),
        COALESCE(persona_json->'psychographics', '{}'::jsonb),
        COALESCE(
          ARRAY(SELECT jsonb_array_elements_text(persona_json->'goals')),
          ARRAY[]::TEXT[]
        ),
        COALESCE(
          ARRAY(SELECT jsonb_array_elements_text(persona_json->'pain_points')),
          ARRAY[]::TEXT[]
        ),
        persona_json->>'description',
        COALESCE(
          ARRAY(SELECT (jsonb_array_elements_text(persona_json->'related_features'))::uuid),
          ARRAY[]::UUID[]
        ),
        COALESCE(
          ARRAY(SELECT (jsonb_array_elements_text(persona_json->'related_vp_steps'))::uuid),
          ARRAY[]::UUID[]
        ),
        'ai_generated'  -- Default confirmation status for migrated personas
      )
      ON CONFLICT (project_id, slug) DO UPDATE SET
        name = EXCLUDED.name,
        role = EXCLUDED.role,
        demographics = EXCLUDED.demographics,
        psychographics = EXCLUDED.psychographics,
        goals = EXCLUDED.goals,
        pain_points = EXCLUDED.pain_points,
        description = EXCLUDED.description,
        updated_at = now();

    END LOOP;
  END LOOP;

  RAISE NOTICE 'Persona migration completed';
END $$;
*/

-- =========================
-- Note on PRD Sections Integration
-- =========================
-- After this migration, personas exist in two places:
--   1. personas table (new, canonical source for surgical updates)
--   2. prd_sections.enrichment.enhanced_fields.personas (legacy, for backward compatibility)
--
-- Going forward:
--   - Surgical updates will modify the personas table
--   - PRD enrichment can sync back to prd_sections if needed for UI compatibility
--   - Consider the personas table as the source of truth
