import { apiRequest, ApiError, getAccessToken, API_BASE, ADMIN_API_KEY } from './core'

// =============================================================================
// Document Upload
// =============================================================================

export interface DocumentUploadResponse {
  id: string
  project_id: string
  original_filename: string
  file_type: string
  file_size_bytes: number
  processing_status: string
  is_duplicate: boolean
  duplicate_of?: string
}

export interface DocumentStatusResponse {
  id: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  original_filename: string
  message?: string
  started_at?: string
  completed_at?: string
  duration_ms?: number
  document_class?: string
  page_count?: number
  word_count?: number
  total_chunks?: number
  signal_id?: string
  error?: string
  needs_clarification?: boolean
  clarification_question?: string
  analysis_summary?: {
    applied?: number
    escalated?: number
    created?: number
    merged?: number
    updated?: number
    chat_summary?: string
  }
  entity_extraction_status?: 'pending' | 'processing' | 'completed' | 'not_applicable' | 'unknown'
  extracted_entities?: {
    features: Array<{ name: string; id: string }>
    personas: Array<{ name: string; id: string }>
    vp_steps: Array<{ name: string; id: string }>
    constraints: Array<{ name: string; id: string }>
    stakeholders: Array<{ name: string; id: string }>
    workflows: Array<{ name: string; id: string }>
    data_entities: Array<{ name: string; id: string }>
    business_drivers: Array<{ name: string; id: string }>
    competitors: Array<{ name: string; id: string }>
    vision: Array<{ name: string; id: string }>
    total_count: number
  }
}

/**
 * Upload a document for processing.
 * Uses FormData for multipart upload.
 */
export const uploadDocument = async (
  projectId: string,
  file: File,
  uploadSource: string = 'workbench',
  authority: string = 'consultant'
): Promise<DocumentUploadResponse> => {
  const url = `${API_BASE}/v1/projects/${projectId}/documents`

  const formData = new FormData()
  formData.append('file', file)
  formData.append('upload_source', uploadSource)
  formData.append('authority', authority)

  const token = getAccessToken()
  const headers: HeadersInit = {}

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  } else if (ADMIN_API_KEY) {
    headers['X-API-Key'] = ADMIN_API_KEY
  }

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }))
    throw new ApiError(response.status, errorData.detail || 'Upload failed')
  }

  return response.json()
}

/**
 * Get document processing status.
 */
export const getDocumentStatus = (documentId: string) =>
  apiRequest<DocumentStatusResponse>(`/documents/${documentId}/status`)

/**
 * Trigger immediate processing of a document.
 */
export const processDocument = (documentId: string) =>
  apiRequest<{ success: boolean }>(`/documents/${documentId}/process`, { method: 'POST' })

// ============================================================================
// Extracted Images
// ============================================================================

export interface ExtractedImage {
  id: string
  document_upload_id: string
  project_id: string
  storage_path: string
  mime_type: string
  file_size_bytes: number
  page_number?: number
  image_index: number
  source_context?: string
  vision_analysis?: string
  vision_model?: string
  vision_analyzed_at?: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
  signed_url?: string
}

export const listDocumentImages = (documentId: string) =>
  apiRequest<{ images: ExtractedImage[]; total: number }>(`/documents/${documentId}/images`)

export const getExtractedImage = (imageId: string) =>
  apiRequest<ExtractedImage>(`/documents/images/${imageId}`)

// ============================================================================
// Sources Tab API
// ============================================================================

/**
 * Document summary with usage stats
 */
export interface DocumentContributedTo {
  features: number
  personas: number
  vp_steps: number
  stakeholders: number
  workflows: number
  data_entities: number
  constraints: number
  business_drivers: number
  other: number
}

export interface DocumentSummaryItem {
  id: string
  original_filename: string
  file_type: string
  file_size_bytes: number
  page_count: number | null
  created_at: string
  content_summary: string | null
  usage_count: number
  contributed_to: DocumentContributedTo
  confidence_level: string
  processing_status: string
  signal_id?: string | null
  // Analysis fields from document classification
  quality_score?: number
  relevance_score?: number
  information_density?: number
  keyword_tags?: string[]
  key_topics?: string[]
}

export interface DocumentSummaryResponse {
  documents: DocumentSummaryItem[]
  total: number
}

/**
 * Get documents with AI summaries and usage statistics.
 */
export const getDocumentsSummary = (projectId: string) =>
  apiRequest<DocumentSummaryResponse>(`/projects/${projectId}/documents/summary`)

/**
 * Get a signed download URL for a document.
 */
export interface DocumentDownloadResponse {
  download_url: string
  filename: string
  mime_type: string
}

export const getDocumentDownloadUrl = (documentId: string) =>
  apiRequest<DocumentDownloadResponse>(`/documents/${documentId}/download`)

/**
 * Withdraw a document (soft delete).
 * Removes from retrieval but preserves data for audit.
 */
export const withdrawDocument = (documentId: string) =>
  apiRequest<{ status: string; document_id: string }>(
    `/documents/${documentId}/withdraw`,
    { method: 'POST' }
  )

/**
 * Hard delete a document (only for failed/pending documents).
 */
export const deleteDocument = (documentId: string, force = false) =>
  apiRequest<{ success: boolean; message: string }>(
    `/documents/${documentId}${force ? '?force=true' : ''}`,
    { method: 'DELETE' }
  )
