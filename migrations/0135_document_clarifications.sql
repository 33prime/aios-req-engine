-- Migration: 0135_document_clarifications
-- Description: Add clarification columns to document_uploads for smart doc classification feedback

ALTER TABLE document_uploads
    ADD COLUMN IF NOT EXISTS needs_clarification BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS clarification_question TEXT,
    ADD COLUMN IF NOT EXISTS clarification_response TEXT,
    ADD COLUMN IF NOT EXISTS clarified_document_class TEXT,
    ADD COLUMN IF NOT EXISTS clarified_at TIMESTAMPTZ;
