-- Migration: 0120_v0_integration
-- Description: Add v0 tracking columns to prototypes for MCP-orchestrated pipeline
-- Date: 2026-02-16

-- Add v0 tracking columns
ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS v0_chat_id TEXT;
ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS v0_demo_url TEXT;
ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS v0_model TEXT;
ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS audit_action TEXT;
ALTER TABLE prototypes ADD COLUMN IF NOT EXISTS github_repo_url TEXT;

-- Fix CHECK constraint to include all statuses the code uses
-- (0103 was missing 'ingested' and 'archived')
ALTER TABLE prototypes DROP CONSTRAINT IF EXISTS prototypes_status_check;
ALTER TABLE prototypes ADD CONSTRAINT prototypes_status_check
  CHECK (status IN ('pending', 'generating', 'ingested', 'analyzed', 'active', 'archived', 'ready', 'failed'))
  NOT VALID;
ALTER TABLE prototypes VALIDATE CONSTRAINT prototypes_status_check;

-- Add CHECK for audit_action values
ALTER TABLE prototypes ADD CONSTRAINT prototypes_audit_action_check
  CHECK (audit_action IS NULL OR audit_action IN ('accept', 'retry', 'notify'))
  NOT VALID;
ALTER TABLE prototypes VALIDATE CONSTRAINT prototypes_audit_action_check;

-- Index for looking up prototypes by v0 chat ID
CREATE INDEX IF NOT EXISTS idx_prototypes_v0_chat_id ON prototypes (v0_chat_id) WHERE v0_chat_id IS NOT NULL;
