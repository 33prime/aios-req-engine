-- Migration 0027: Batch Proposals Table
-- Purpose: Staging table for batch proposals with preview/apply workflow
-- Created: 2025-12-29

-- Batch proposals table for context-aware prototype coach
CREATE TABLE IF NOT EXISTS batch_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,

    -- Core metadata
    title TEXT NOT NULL,
    description TEXT,
    proposal_type TEXT NOT NULL CHECK (proposal_type IN ('features', 'prd', 'vp', 'personas', 'mixed')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'previewed', 'applied', 'discarded')),

    -- Changes array: stores all proposed modifications
    changes JSONB NOT NULL DEFAULT '[]',
    /*
      Each change object structure:
      {
        entity_type: 'feature' | 'prd_section' | 'vp_step' | 'persona',
        operation: 'create' | 'update' | 'delete',
        entity_id: UUID | null,
        before: {...} | null,
        after: {...},
        evidence: [
          {
            chunk_id: UUID,
            excerpt: "relevant text...",
            rationale: "why this evidence supports the change"
          }
        ],
        rationale: "explanation for this change"
      }
    */

    -- Summary counts for quick display
    creates_count INT DEFAULT 0,
    updates_count INT DEFAULT 0,
    deletes_count INT DEFAULT 0,

    -- Context preservation
    user_request TEXT,
    context_snapshot JSONB,
    /*
      Context snapshot structure:
      {
        project: {...},
        summary: {...},
        focused_entity: {...},
        intent: "..."
      }
    */

    -- Lifecycle timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    previewed_at TIMESTAMPTZ,
    applied_at TIMESTAMPTZ,
    applied_by TEXT,

    -- Metadata
    created_by TEXT,
    error_message TEXT
);

-- Indexes for common queries
CREATE INDEX idx_batch_proposals_project ON batch_proposals(project_id);
CREATE INDEX idx_batch_proposals_conversation ON batch_proposals(conversation_id);
CREATE INDEX idx_batch_proposals_status ON batch_proposals(status);
CREATE INDEX idx_batch_proposals_type ON batch_proposals(proposal_type);
CREATE INDEX idx_batch_proposals_created ON batch_proposals(created_at DESC);

-- Index for finding pending proposals
CREATE INDEX idx_batch_proposals_pending ON batch_proposals(project_id, status) WHERE status = 'pending';

-- Comments
COMMENT ON TABLE batch_proposals IS 'Staging table for batch proposals with preview/apply workflow';
COMMENT ON COLUMN batch_proposals.changes IS 'JSONB array of change objects with entity_type, operation, before/after, evidence, and rationale';
COMMENT ON COLUMN batch_proposals.context_snapshot IS 'JSONB snapshot of project context at proposal creation time';
COMMENT ON COLUMN batch_proposals.status IS 'Lifecycle: pending → previewed → applied/discarded';
