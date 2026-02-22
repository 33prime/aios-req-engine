import { apiRequest } from './core'
import type {
  Prototype,
  FeatureOverlay,
  PrototypeSession,
  PrototypeFeedback,
  SubmitFeedbackRequest,
  SessionContext,
  PromptAuditResult,
  DesignProfile,
  DesignSelection,
  FeatureVerdict,
  ConvergenceSnapshot,
} from '../../types/prototype'

// ============================================
// Prototype Refinement APIs
// ============================================

export const getDesignProfile = (projectId: string) =>
  apiRequest<DesignProfile>(`/projects/${projectId}/workspace/design-profile`)

export const generatePrototype = (projectId: string, designSelection?: DesignSelection) =>
  apiRequest<{ prototype_id: string; prompt_length: number; features_included: number; flows_included: number }>('/prototypes/generate', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, design_selection: designSelection }),
  })

export const ingestPrototype = (projectId: string, repoUrl: string, deployUrl?: string) =>
  apiRequest<{ prototype_id: string; local_path: string; handoff_found: boolean; status: string }>('/prototypes/ingest', {
    method: 'POST',
    body: JSON.stringify({ project_id: projectId, repo_url: repoUrl, deploy_url: deployUrl }),
  })

export const getPrototype = (prototypeId: string) =>
  apiRequest<Prototype>(`/prototypes/${prototypeId}`)

export const getPrototypeForProject = (projectId: string) =>
  apiRequest<Prototype>(`/prototypes/by-project/${projectId}`)

export const getPrototypeOverlays = (prototypeId: string) =>
  apiRequest<FeatureOverlay[]>(`/prototypes/${prototypeId}/overlays`)

export const getPrototypeAudit = (prototypeId: string) =>
  apiRequest<PromptAuditResult | { message: string }>(`/prototypes/${prototypeId}/audit`)

export const triggerPrototypeAnalysis = (prototypeId: string) =>
  apiRequest<{ prototype_id: string; run_id: string; features_analyzed: number; errors: number; status: string }>(
    `/prototypes/${prototypeId}/analyze`,
    { method: 'POST' }
  )

export const retryPrototype = (prototypeId: string) =>
  apiRequest<{ prototype_id: string; prompt_version: number; prompt_length: number }>(
    `/prototypes/${prototypeId}/retry`,
    { method: 'POST' }
  )

// ============================================
// Prototype Sessions
// ============================================

export const createPrototypeSession = (prototypeId: string) =>
  apiRequest<PrototypeSession>('/prototype-sessions', {
    method: 'POST',
    body: JSON.stringify({ prototype_id: prototypeId }),
  })

export const getPrototypeSession = (sessionId: string) =>
  apiRequest<PrototypeSession>(`/prototype-sessions/${sessionId}`)

export const listPrototypeSessions = (prototypeId: string) =>
  apiRequest<PrototypeSession[]>(`/prototype-sessions/by-prototype/${prototypeId}`)

export const submitPrototypeFeedback = (sessionId: string, data: SubmitFeedbackRequest) =>
  apiRequest<PrototypeFeedback>(`/prototype-sessions/${sessionId}/feedback`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const prototypeSessionChat = (
  sessionId: string,
  message: string,
  context?: SessionContext,
  modelOverride?: string,
  featureId?: string
) =>
  apiRequest<{ response: string; extracted_feedback: Record<string, unknown>[] }>(
    `/prototype-sessions/${sessionId}/chat`,
    {
      method: 'POST',
      body: JSON.stringify({
        message,
        context,
        model_override: modelOverride || undefined,
        feature_id: featureId || undefined,
      }),
    }
  )

export const endConsultantReview = (sessionId: string) =>
  apiRequest<{ session_id: string; client_review_token: string; client_review_url: string }>(
    `/prototype-sessions/${sessionId}/end-review`,
    { method: 'POST' }
  )

export const synthesizePrototypeFeedback = (sessionId: string) =>
  apiRequest<{
    session_id: string
    features_with_feedback: number
    new_features_discovered: number
    high_priority_changes: number
    session_summary: string
  }>(`/prototype-sessions/${sessionId}/synthesize`, { method: 'POST' })

export const triggerPrototypeCodeUpdate = (sessionId: string) =>
  apiRequest<{
    session_id: string
    files_changed: number
    build_passed: boolean
    commit_sha: string | null
    summary: string
  }>(`/prototype-sessions/${sessionId}/update-code`, { method: 'POST' })

export const getPrototypeConvergence = (prototypeId: string) =>
  apiRequest<ConvergenceSnapshot>(
    `/prototype-sessions/convergence/${prototypeId}`
  )

// ============================================
// Client Review
// ============================================

export const getPrototypeClientData = (sessionId: string, token: string) =>
  apiRequest<{
    prototype_id: string
    deploy_url: string | null
    session_number: number
    features_analyzed: number
    questions: Array<{ id: string; question: string; category: string; priority: string }>
    feature_reviews: Array<{
      feature_name: string
      overlay_id: string
      consultant_verdict: FeatureVerdict | null
      consultant_notes: string | null
      suggested_verdict: FeatureVerdict | null
      validation_question: string | null
      validation_why: string | null
      validation_area: string | null
      spec_summary: string | null
      implementation_status: string | null
      confidence: number
      status: string
    }>
  }>(`/prototype-sessions/${sessionId}/client-data?token=${token}`)

export const submitFeatureVerdict = (
  prototypeId: string,
  overlayId: string,
  verdict: FeatureVerdict,
  source: 'consultant' | 'client',
  notes?: string
) =>
  apiRequest<{ overlay_id: string; source: string; verdict: string; notes: string | null }>(
    `/prototypes/${prototypeId}/overlays/${overlayId}/verdict`,
    {
      method: 'PUT',
      body: JSON.stringify({ verdict, source, notes: notes || null }),
    }
  )

export const completeClientReview = (sessionId: string, token: string) =>
  apiRequest<{ session_id: string; status: string }>(
    `/prototype-sessions/${sessionId}/complete-client-review?token=${token}`,
    { method: 'POST' }
  )

// ============================================
// Feature Mapping
// ============================================

/**
 * Map a feature to a value path step (or unmap if stepId is null).
 */
export const mapFeatureToStep = (
  projectId: string,
  featureId: string,
  vpStepId: string | null
) =>
  apiRequest<{ success: boolean; feature_id: string; vp_step_id: string | null }>(
    `/projects/${projectId}/workspace/features/${featureId}/map-to-step`,
    {
      method: 'PATCH',
      body: JSON.stringify({ vp_step_id: vpStepId }),
    }
  )
