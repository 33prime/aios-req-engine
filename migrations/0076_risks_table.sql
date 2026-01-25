-- Migration: Risks Table
-- Description: Create first-class risks entity table (extracts from strategic_context.risks JSONB)
-- Date: 2026-01-25
-- Part of: Strategic Foundation Entity Enhancement (Phase 1, Task #7)

-- =========================
-- Create risks table with universal entity pattern
-- =========================

CREATE TABLE IF NOT EXISTS risks (
    -- Primary key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

    -- Core risk fields
    title TEXT NOT NULL,
    description TEXT NOT NULL,

    -- Risk classification
    risk_type TEXT NOT NULL
        CHECK (risk_type IN ('technical', 'business', 'market', 'team', 'timeline', 'budget', 'compliance', 'security', 'operational', 'strategic')),
    severity TEXT NOT NULL
        CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    likelihood TEXT DEFAULT 'medium'
        CHECK (likelihood IN ('very_high', 'high', 'medium', 'low', 'very_low')),
    status TEXT DEFAULT 'active'
        CHECK (status IN ('identified', 'active', 'mitigated', 'resolved', 'accepted')),

    -- Enrichment fields
    impact TEXT,
    mitigation_strategy TEXT,
    owner TEXT,
    detection_signals TEXT[],
    probability_percentage INTEGER CHECK (probability_percentage IS NULL OR (probability_percentage >= 0 AND probability_percentage <= 100)),
    estimated_cost TEXT,
    mitigation_cost TEXT,

    -- Evidence attribution (universal entity pattern)
    evidence JSONB DEFAULT '[]'::jsonb,
    source_signal_ids UUID[] DEFAULT '{}'::uuid[],

    -- Version tracking (universal entity pattern)
    version INTEGER DEFAULT 1,
    created_by TEXT DEFAULT 'system'
        CHECK (created_by IN ('system', 'consultant', 'client', 'di_agent')),

    -- Enrichment tracking (universal entity pattern)
    enrichment_status TEXT DEFAULT 'none'
        CHECK (enrichment_status IN ('none', 'pending', 'enriched', 'failed')),
    enrichment_attempted_at TIMESTAMPTZ,
    enrichment_error TEXT,

    -- Confirmation workflow (universal entity pattern)
    confirmation_status TEXT DEFAULT 'ai_generated'
        CHECK (confirmation_status IN ('ai_generated', 'confirmed_consultant', 'needs_client', 'confirmed_client')),
    confirmed_fields JSONB DEFAULT '{}'::jsonb,
    confirmed_by UUID,
    confirmed_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =========================
-- Indexes
-- =========================

-- Core queries
CREATE INDEX IF NOT EXISTS idx_risks_project ON risks(project_id);
CREATE INDEX IF NOT EXISTS idx_risks_type ON risks(project_id, risk_type);
CREATE INDEX IF NOT EXISTS idx_risks_severity ON risks(project_id, severity);
CREATE INDEX IF NOT EXISTS idx_risks_status ON risks(project_id, status);

-- Risk matrix queries (likelihood x severity)
CREATE INDEX IF NOT EXISTS idx_risks_matrix
    ON risks(project_id, severity, likelihood)
    WHERE status IN ('identified', 'active');

-- Enrichment and tracking
CREATE INDEX IF NOT EXISTS idx_risks_enrichment_status
    ON risks(project_id, enrichment_status);
CREATE INDEX IF NOT EXISTS idx_risks_confirmation
    ON risks(project_id, confirmation_status);
CREATE INDEX IF NOT EXISTS idx_risks_version
    ON risks(project_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_risks_created_by
    ON risks(project_id, created_by);

-- Evidence queries
CREATE INDEX IF NOT EXISTS idx_risks_evidence
    ON risks USING gin(evidence);
CREATE INDEX IF NOT EXISTS idx_risks_confirmed_fields
    ON risks USING gin(confirmed_fields);

-- =========================
-- Trigger for updated_at
-- =========================

CREATE OR REPLACE FUNCTION update_risks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS risks_updated_at ON risks;
CREATE TRIGGER risks_updated_at
    BEFORE UPDATE ON risks
    FOR EACH ROW
    EXECUTE FUNCTION update_risks_updated_at();

-- =========================
-- Comments
-- =========================

COMMENT ON TABLE risks IS 'First-class risk entities - extracted from strategic_context.risks JSONB';

-- Core fields
COMMENT ON COLUMN risks.title IS 'Short risk title (e.g., "Key developer might leave", "Regulatory approval delay")';
COMMENT ON COLUMN risks.description IS 'Detailed description of the risk';

-- Risk classification
COMMENT ON COLUMN risks.risk_type IS 'Category: technical, business, market, team, timeline, budget, compliance, security, operational, strategic';
COMMENT ON COLUMN risks.severity IS 'Impact severity: critical (project-threatening), high (major setback), medium (manageable), low (minor)';
COMMENT ON COLUMN risks.likelihood IS 'Probability: very_high (>75%), high (50-75%), medium (25-50%), low (10-25%), very_low (<10%)';
COMMENT ON COLUMN risks.status IS 'Current state: identified (new), active (tracking), mitigated (reduced), resolved (eliminated), accepted (won''t address)';

-- Enrichment fields
COMMENT ON COLUMN risks.impact IS 'Detailed impact if risk materializes (e.g., "3 month delay + $200K cost overrun")';
COMMENT ON COLUMN risks.mitigation_strategy IS 'How to prevent/reduce this risk (e.g., "Retain key developer with equity + backup training")';
COMMENT ON COLUMN risks.owner IS 'Who owns mitigation (e.g., "CTO", "Project Manager", "Legal team")';
COMMENT ON COLUMN risks.detection_signals IS 'Early warning signs (e.g., ["developer updating LinkedIn", "missed 2 standups", "mentioned other opportunities"])';
COMMENT ON COLUMN risks.probability_percentage IS 'Numeric probability estimate (0-100%)';
COMMENT ON COLUMN risks.estimated_cost IS 'Financial impact if risk occurs (e.g., "$50K-150K", "10-20% revenue reduction")';
COMMENT ON COLUMN risks.mitigation_cost IS 'Cost to mitigate (e.g., "$10K retention bonus", "20 hours consultant time")';

-- Universal entity pattern
COMMENT ON COLUMN risks.evidence IS 'Array of evidence objects: [{"signal_id": "...", "chunk_id": "...", "text": "...", "confidence": 0.95}]';
COMMENT ON COLUMN risks.source_signal_ids IS 'Array of signal IDs that identified this risk';
COMMENT ON COLUMN risks.version IS 'Version number, incremented on each update for change tracking';
COMMENT ON COLUMN risks.created_by IS 'Who created this entity: system (auto-extract), consultant, client, di_agent';
COMMENT ON COLUMN risks.enrichment_status IS 'Enrichment state: none (not enriched), pending (queued), enriched (complete), failed (error)';
COMMENT ON COLUMN risks.enrichment_attempted_at IS 'Timestamp of last enrichment attempt';
COMMENT ON COLUMN risks.enrichment_error IS 'Error message if enrichment failed';
COMMENT ON COLUMN risks.confirmation_status IS 'Entity-level confirmation: ai_generated, confirmed_consultant, needs_client, confirmed_client';
COMMENT ON COLUMN risks.confirmed_fields IS 'Field-level confirmation tracking: {"title": "confirmed_consultant", "severity": "ai_generated"}';
COMMENT ON COLUMN risks.confirmed_by IS 'User ID who confirmed this entity';
COMMENT ON COLUMN risks.confirmed_at IS 'Timestamp of last confirmation';

-- =========================
-- Data migration notes
-- =========================

-- Risks are currently stored as JSONB in strategic_context.risks:
-- Format: [{ category, description, severity, mitigation, evidence_ids }]
--
-- Migration to this table:
-- - category → risk_type
-- - description → description (also extract title from first sentence)
-- - severity → severity
-- - mitigation → mitigation_strategy
-- - evidence_ids → source_signal_ids
--
-- This migration will be handled by a separate data backfill script (Task #15)
