-- Pre-build intelligence storage
-- Phase 0 output: epic plan, feature depth specs, computed before code generation

ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS prebuild_intelligence JSONB;
ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS feature_build_specs JSONB;
