import { apiRequest } from './core'
import type {
  Feature,
  VpStep,
  Persona,
  Signal,
  Project,
  ProjectDetailWithDashboard,
  StageStatusResponse,
  AdvanceStageRequest,
  AdvanceStageResponse,
} from '../../types/api'

// State APIs
export const getFeatures = (projectId: string) =>
  apiRequest<Feature[]>(`/state/features?project_id=${projectId}`)

// PRD sections removed - use features, personas, VP steps instead

export const getVpSteps = (projectId: string) =>
  apiRequest<VpStep[]>(`/state/vp?project_id=${projectId}`)

export const getPersonas = (projectId: string) =>
  apiRequest<Persona[]>(`/state/personas?project_id=${projectId}`)

// Evidence APIs
export const getSignal = (signalId: string) =>
  apiRequest<Signal>(`/signals/${signalId}`)

// Projects CRUD APIs
export const listProjects = (status = 'active', search?: string) => {
  const params = new URLSearchParams({ status })
  if (search) params.append('search', search)
  return apiRequest<{
    projects: ProjectDetailWithDashboard[]
    total: number
    owner_profiles: Record<string, {
      first_name?: string
      last_name?: string
      photo_url?: string
    }>
  }>(`/projects?${params}`)
}

export const createProject = (data: { name: string; description?: string; auto_ingest_description?: boolean }) =>
  apiRequest<Project>(`/projects`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

// Enhanced project creation with guided context
export interface CreateProjectContextPayload {
  name: string
  brief: string
  company_name?: string
  company_website?: string
}

export const createProjectWithContext = (payload: CreateProjectContextPayload) => {
  // Use the brief directly as the description - no transformation needed
  return apiRequest<Project>('/projects', {
    method: 'POST',
    body: JSON.stringify({
      name: payload.name,
      description: payload.brief,
      auto_ingest_description: true,
      // Pass additional context metadata
      metadata: {
        company_name: payload.company_name,
        company_website: payload.company_website,
      },
    }),
  })
}

export const getProjectDetails = (projectId: string) =>
  apiRequest<ProjectDetailWithDashboard>(`/projects/${projectId}`)

// Stage Progression APIs
export const getStageStatus = (projectId: string) =>
  apiRequest<StageStatusResponse>(`/projects/${projectId}/stage-status`)

export const advanceStage = (projectId: string, request: AdvanceStageRequest) =>
  apiRequest<AdvanceStageResponse>(`/projects/${projectId}/stage`, {
    method: 'PATCH',
    body: JSON.stringify(request),
  })

export const updateProject = (projectId: string, updates: { name?: string; description?: string; status?: string; tags?: string[]; metadata?: Record<string, unknown> }) =>
  apiRequest<Project>(`/projects/${projectId}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })

// Revisions APIs
export const listEntityRevisions = (entityType: string, entityId: string, limit = 20) =>
  apiRequest<{
    entity_type: string
    entity_id: string
    revisions: Array<{
      id: string
      entity_type: string
      entity_id: string
      revision_number: number
      change_type: string
      changes: Record<string, any>
      diff_summary: string
      created_at: string
      created_by?: string
      source_signal_id?: string
    }>
    total: number
  }>(`/state/${entityType}/${entityId}/revisions?limit=${limit}`)

// Persona feature coverage (for Gaps tab)
export interface PersonaFeatureCoverage {
  addressed_goals: string[]
  unaddressed_goals: string[]
  feature_matches: Array<{
    goal: string
    features: Array<{ id: string; name: string; match_type: string }>
  }>
  coverage_score: number
}

export const getPersonaCoverage = (personaId: string) =>
  apiRequest<PersonaFeatureCoverage>(`/personas/${personaId}/coverage`)

// Delete Cascade APIs
export interface FeatureCascadeImpact {
  feature: {
    id: string
    name: string
    category?: string
    is_mvp?: boolean
  }
  affected_vp_steps: Array<{ id: string; step_index: number; label: string }>
  affected_personas: Array<{ id: string; name: string; slug?: string }>
  total_vp_steps: number
  total_personas: number
  affected_vp_count: number
  affected_persona_count: number
  impact_percentage: number
  suggest_bulk_rebuild: boolean
}

export interface PersonaCascadeImpact {
  persona: {
    id: string
    name: string
    slug?: string
    role?: string
  }
  affected_features: Array<{ id: string; name: string; category?: string }>
  affected_vp_steps: Array<{ id: string; step_index: number; label: string }>
  total_features: number
  total_vp_steps: number
  total_personas: number
  affected_feature_count: number
  affected_vp_count: number
  impact_percentage: number
  suggest_bulk_rebuild: boolean
}

export interface DeleteFeatureResult {
  deleted: boolean
  feature_id: string
  feature_name: string
  cleaned_personas: Array<{ id: string; name: string }>
  cleaned_persona_count: number
}

export interface DeletePersonaResult {
  deleted: boolean
  persona_id: string
  persona_name: string
  cleaned_features: Array<{ id: string; name: string }>
  cleaned_feature_count: number
}

export const getFeatureCascadeImpact = (featureId: string) =>
  apiRequest<FeatureCascadeImpact>(`/features/${featureId}/impact`)

export const deleteFeature = (featureId: string, cleanupReferences = true) =>
  apiRequest<DeleteFeatureResult>(`/features/${featureId}?cleanup_references=${cleanupReferences}`, {
    method: 'DELETE',
  })

export const getPersonaCascadeImpact = (personaId: string) =>
  apiRequest<PersonaCascadeImpact>(`/personas/${personaId}/impact`)

export const deletePersona = (personaId: string, cleanupReferences = true) =>
  apiRequest<DeletePersonaResult>(`/personas/${personaId}?cleanup_references=${cleanupReferences}`, {
    method: 'DELETE',
  })

// ============================================
// Client Portal Admin APIs
// ============================================

// Portal Configuration
export interface PortalConfig {
  portal_enabled: boolean
  portal_phase?: 'pre_call' | 'post_call' | 'building' | 'testing'
  discovery_call_date?: string
  client_display_name?: string
}

export const getPortalConfig = (projectId: string) =>
  apiRequest<{
    portal_enabled: boolean
    portal_phase: string
    discovery_call_date: string | null
    call_completed_at: string | null
    client_display_name: string | null
  }>(`/projects/${projectId}`)

export const updatePortalConfig = (projectId: string, config: Partial<PortalConfig>) =>
  apiRequest<{ success: boolean }>(`/admin/projects/${projectId}/portal`, {
    method: 'PATCH',
    body: JSON.stringify(config),
  })

// Project Members (Clients)
export interface ProjectMember {
  id: string
  user_id: string
  role: 'consultant' | 'client'
  invited_at: string
  accepted_at: string | null
  user?: {
    id: string
    email: string
    first_name: string | null
    last_name: string | null
    company_name: string | null
  }
}

export const getProjectMembers = async (projectId: string) => {
  const members = await apiRequest<ProjectMember[]>(
    `/admin/projects/${projectId}/members`
  )
  return { members, total: members.length }
}

export const inviteClient = (
  projectId: string,
  data: {
    email: string
    first_name?: string
    last_name?: string
    company_name?: string
    send_email?: boolean
  }
) =>
  apiRequest<{
    user: { id: string; email: string; first_name?: string; last_name?: string }
    project_member: { id: string; role: string }
    magic_link_sent: boolean
    magic_link_error?: string
  }>(`/admin/projects/${projectId}/invite`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const removeProjectMember = (projectId: string, userId: string) =>
  apiRequest<{ success: boolean }>(`/admin/projects/${projectId}/members/${userId}`, {
    method: 'DELETE',
  })

// Info Requests (Pre-call questions, Post-call actions)
export interface InfoRequest {
  id: string
  project_id: string
  phase: 'pre_call' | 'post_call'
  created_by: 'ai' | 'consultant'
  display_order: number
  title: string
  description: string | null
  request_type: 'question' | 'document' | 'tribal_knowledge'
  input_type: 'text' | 'file' | 'multi_text' | 'text_and_file'
  priority: 'high' | 'medium' | 'low' | 'none' | null
  best_answered_by: string | null
  status: 'not_started' | 'in_progress' | 'complete' | 'skipped'
  answer_data: Record<string, any> | null
  why_asking: string | null
  example_answer: string | null
  created_at: string
}

// ============================================
// Tasks APIs
// ============================================

export const getProjectTasks = (projectId: string) =>
  apiRequest<{ project_id: string; tasks: Array<{ id: string; title: string; description?: string; priority: 'high' | 'medium' | 'low'; category: string; action_url?: string; action_type?: string; entity_id?: string; entity_type?: string }>; total: number }>(`/projects/${projectId}/tasks`)

// ============================================
// Project Status API (for AI Assistant)
// ============================================

export interface ProjectStatusResponse {
  project: {
    id: string
    name: string
    description: string | null
  }
  company: {
    name: string | null
    industry: string | null
    stage: string | null
    location: string | null
    website: string | null
    unique_selling_point: string | null
  } | null
  strategic: {
    pains: Array<{ description: string; status: string | null }>
    goals: Array<{ description: string; status: string | null }>
    kpis: Array<{ description: string; measurement: string | null; status: string | null }>
    total_drivers: number
    confirmed_drivers: number
  }
  market: {
    competitors: Array<{ name: string; notes: string }>
    design_refs: string[]
    constraints: Array<{ name: string; type: string | null }>
  }
  product: {
    features: {
      total: number
      mvp: number
      confirmed: number
      items: Array<{ name: string; is_mvp: boolean; status: string | null }>
    }
    personas: {
      total: number
      primary: number
      confirmed: number
      items: Array<{ name: string; role: string | null; is_primary: boolean }>
    }
    vp_steps: {
      total: number
      items: Array<{ name: string; order: number }>
    }
  }
  stakeholders: {
    total: number
    items: Array<{ name: string; role: string | null; type: string | null }>
  }
  signals: {
    total: number
  }
  readiness: {
    score: number
    blockers: string[]
    suggestions: string[]
  }
}

export const getProjectStatus = (projectId: string) =>
  apiRequest<ProjectStatusResponse>(`/state/project-status?project_id=${projectId}`)

// ============================================
// Readiness Score API
// ============================================

export interface ReadinessFactorScore {
  score: number
  max_score: number
  details: string | null
}

export interface ReadinessRecommendation {
  action: string
  impact: string
  effort: 'low' | 'medium' | 'high'
  priority: number
  dimension: string | null
}

export interface ReadinessDimensionScore {
  score: number
  weight: number
  weighted_score: number
  factors: Record<string, ReadinessFactorScore>
  blockers: string[]
  recommendations: ReadinessRecommendation[]
  summary: string | null
}

export interface ReadinessCapApplied {
  cap_id: string
  limit: number
  reason: string
}

export interface GateAssessment {
  gate_name: string
  is_satisfied: boolean
  confidence: number
  completeness: number
  status: string
  reason_not_satisfied?: string
  how_to_acquire?: string
}

export interface ReadinessScore {
  score: number
  ready: boolean
  threshold: number
  dimensions: Record<string, ReadinessDimensionScore>
  caps_applied: ReadinessCapApplied[]
  top_recommendations: ReadinessRecommendation[]
  computed_at: string
  confirmed_entities: number
  total_entities: number
  client_signals_count: number
  meetings_completed: number
  // Gate-based readiness fields
  phase?: string
  gates?: GateAssessment[]
  gate_score?: number
  total_readiness?: number
  prototype_gates_satisfied?: number
  prototype_gates_total?: number
  build_gates_satisfied?: number
  build_gates_total?: number
}

export const getReadinessScore = (projectId: string, forceRefresh = false) =>
  apiRequest<ReadinessScore>(`/projects/${projectId}/readiness${forceRefresh ? '?force_refresh=true' : ''}`)
