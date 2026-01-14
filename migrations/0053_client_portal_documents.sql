-- Migration: 0053_client_portal_documents.sql
-- Description: Client documents metadata (files stored in Supabase Storage)
-- Date: 2026-01-12

-- Client documents (metadata - actual files in Supabase Storage)
CREATE TABLE IF NOT EXISTS client_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,

  -- File info
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL,  -- Supabase Storage path
  file_size INT NOT NULL,
  file_type TEXT NOT NULL,
  mime_type TEXT,

  -- Ownership
  uploaded_by UUID NOT NULL REFERENCES users(id),
  category TEXT NOT NULL CHECK (category IN ('client_uploaded', 'consultant_shared')),

  -- Processing status
  extracted_text TEXT,  -- If we extract content from the file
  signal_id UUID REFERENCES signals(id),  -- Link to signal if processed into chunks

  -- Link to info request (if uploaded in response to a specific request)
  info_request_id UUID REFERENCES info_requests(id) ON DELETE SET NULL,

  -- Description (optional, user-provided)
  description TEXT,

  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for client_documents
CREATE INDEX IF NOT EXISTS idx_client_documents_project ON client_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_client_documents_uploaded_by ON client_documents(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_client_documents_category ON client_documents(project_id, category);
CREATE INDEX IF NOT EXISTS idx_client_documents_info_request ON client_documents(info_request_id);
