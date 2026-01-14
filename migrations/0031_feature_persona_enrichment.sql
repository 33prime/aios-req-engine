-- Migration: Feature & Persona Enrichment
-- Description: Add structured enrichment columns for detailed feature specs and persona workflows
-- Date: 2025-01-05

-- =========================
-- Features: Add enrichment columns for mini-spec structure
-- =========================

-- Overview: Business-friendly description of what the feature does
ALTER TABLE features
ADD COLUMN IF NOT EXISTS overview TEXT;

-- Target personas: Who uses this feature and how
-- Format: [{persona_id, persona_name, role: 'primary'|'secondary', context: "Uses this to..."}]
ALTER TABLE features
ADD COLUMN IF NOT EXISTS target_personas JSONB DEFAULT '[]'::jsonb;

-- User actions: What the user does, step by step
-- Format: ["Taps Start to begin", "Enters client info", ...]
ALTER TABLE features
ADD COLUMN IF NOT EXISTS user_actions JSONB DEFAULT '[]'::jsonb;

-- System behaviors: What happens behind the scenes
-- Format: ["Starts audio recording", "Sends to transcription service", ...]
ALTER TABLE features
ADD COLUMN IF NOT EXISTS system_behaviors JSONB DEFAULT '[]'::jsonb;

-- UI requirements: What the user sees
-- Format: ["One question at a time", "Large Next button", "Progress indicator", ...]
ALTER TABLE features
ADD COLUMN IF NOT EXISTS ui_requirements JSONB DEFAULT '[]'::jsonb;

-- Rules: Simple validation and business rules (consultant-friendly)
-- Format: ["Cannot start without client name", "Recording auto-stops after 30 min", ...]
ALTER TABLE features
ADD COLUMN IF NOT EXISTS rules JSONB DEFAULT '[]'::jsonb;

-- Integrations: External systems this feature connects with
-- Format: ["HubSpot", "Stripe", "OpenAI Whisper", ...]
ALTER TABLE features
ADD COLUMN IF NOT EXISTS integrations JSONB DEFAULT '[]'::jsonb;

-- Enrichment tracking
ALTER TABLE features
ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'none'
  CHECK (enrichment_status IN ('none', 'enriched', 'stale'));

ALTER TABLE features
ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;

-- Index for enrichment status filtering
CREATE INDEX IF NOT EXISTS idx_features_enrichment_status
ON features(project_id, enrichment_status);

-- =========================
-- Personas: Add enrichment columns for detailed profiles
-- =========================

-- Overview: Detailed description of who this persona is
ALTER TABLE personas
ADD COLUMN IF NOT EXISTS overview TEXT;

-- Key workflows: How this persona uses features together
-- Format: [{name: "Daily Survey Flow", steps: ["Opens app", "Selects client", ...], features: ["Survey Interface", "Client Intake"]}]
ALTER TABLE personas
ADD COLUMN IF NOT EXISTS key_workflows JSONB DEFAULT '[]'::jsonb;

-- Enrichment tracking
ALTER TABLE personas
ADD COLUMN IF NOT EXISTS enrichment_status TEXT DEFAULT 'none'
  CHECK (enrichment_status IN ('none', 'enriched', 'stale'));

ALTER TABLE personas
ADD COLUMN IF NOT EXISTS enriched_at TIMESTAMPTZ;

-- Index for enrichment status filtering
CREATE INDEX IF NOT EXISTS idx_personas_enrichment_status
ON personas(project_id, enrichment_status);

-- =========================
-- Comments
-- =========================

COMMENT ON COLUMN features.overview IS
  'Business-friendly description of what the feature does and why it matters';

COMMENT ON COLUMN features.target_personas IS
  'Array of personas who use this feature: [{persona_id, persona_name, role, context}]';

COMMENT ON COLUMN features.user_actions IS
  'Step-by-step user actions: ["Taps Start", "Enters info", ...]';

COMMENT ON COLUMN features.system_behaviors IS
  'Behind-the-scenes system behaviors: ["Starts recording", "Sends to API", ...]';

COMMENT ON COLUMN features.ui_requirements IS
  'What the user sees: ["One question at a time", "Progress indicator", ...]';

COMMENT ON COLUMN features.rules IS
  'Simple validation/business rules: ["Cannot start without name", ...]';

COMMENT ON COLUMN features.integrations IS
  'External systems: ["HubSpot", "Stripe", ...]';

COMMENT ON COLUMN features.enrichment_status IS
  'Enrichment state: none (not enriched), enriched (up to date), stale (needs re-enrichment)';

COMMENT ON COLUMN personas.overview IS
  'Detailed description of who this persona is and what they care about';

COMMENT ON COLUMN personas.key_workflows IS
  'How this persona uses features together: [{name, steps, features}]';

COMMENT ON COLUMN personas.enrichment_status IS
  'Enrichment state: none (not enriched), enriched (up to date), stale (needs re-enrichment)';
