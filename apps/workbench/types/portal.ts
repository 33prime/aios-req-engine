/** Portal TypeScript types for the Client Portal v1 — Validation Machine. */

// ============================================================================
// Enums / Literals
// ============================================================================

export type PortalRole = 'client_admin' | 'client_user'
export type VerdictType = 'confirmed' | 'refine' | 'flag'
export type AssignmentStatus = 'pending' | 'in_progress' | 'completed' | 'skipped'
export type InfoRequestType = 'question' | 'document' | 'tribal_knowledge'
export type InfoRequestInputType = 'text' | 'file' | 'multi_text' | 'text_and_file'
export type InfoRequestPhase = 'pre_call' | 'post_call'
export type InfoRequestPriority = 'high' | 'medium' | 'low' | 'none'
export type InfoRequestStatus = 'not_started' | 'in_progress' | 'complete' | 'skipped'

export type ValidationEntityType =
  | 'workflow'
  | 'business_driver'
  | 'feature'
  | 'persona'
  | 'vp_step'
  | 'prototype_epic'

// ============================================================================
// Validation
// ============================================================================

export interface ValidationItem {
  id: string
  entity_type: ValidationEntityType
  entity_id: string
  name: string
  summary?: string | null
  details: Record<string, unknown>
  priority: number
  reason?: string | null
  assignment_id?: string | null
  existing_verdict?: VerdictType | null
  existing_notes?: string | null
  is_assigned_to_me: boolean
}

export interface ValidationQueueResponse {
  total_pending: number
  by_type: Record<string, number>
  urgent_count: number
  items: ValidationItem[]
}

export interface SubmitVerdictRequest {
  entity_type: string
  entity_id: string
  verdict: VerdictType
  notes?: string | null
  refinement_details?: Record<string, unknown> | null
}

export interface VerdictResponse {
  verdict_id: string
  entity_type: string
  entity_id: string
  verdict: VerdictType
  signal_id?: string | null
}

// ============================================================================
// Dashboard
// ============================================================================

export interface PortalDashboard {
  project_id: string
  project_name: string
  phase: string
  portal_role: PortalRole
  call_info?: {
    consultant_name: string
    scheduled_date?: string
    completed_date?: string
    duration_minutes: number
  } | null
  progress: {
    total_items: number
    completed_items: number
    percentage: number
    status_breakdown: Record<string, number>
  }
  info_requests: unknown[]
  due_date?: string | null
  agenda_summary?: string | null
  agenda_bullets: string[]
  validation_summary?: ValidationQueueResponse | null
  upcoming_meeting?: {
    id: string
    title: string
    scheduled_at: string
    meeting_type?: string
  } | null
  prototype_status?: {
    id: string
    status: string
    deploy_url?: string
    created_at: string
  } | null
  team_summary?: {
    member_count: number
    total_assignments: number
    completed_assignments: number
    completion_pct: number
  } | null
  recent_activity: Array<{
    id: string
    entity_type: string
    entity_id: string
    verdict: string
    notes?: string
    created_at: string
    stakeholders?: { name: string; role: string }
  }>
}

// ============================================================================
// Team
// ============================================================================

export interface TeamMember {
  user_id: string
  email: string
  first_name?: string | null
  last_name?: string | null
  portal_role: PortalRole
  stakeholder_id?: string | null
  stakeholder_name?: string | null
  total_assignments: number
  completed_assignments: number
  pending_assignments: number
}

export interface TeamInviteRequest {
  email: string
  first_name?: string
  last_name?: string
  portal_role?: PortalRole
  stakeholder_id?: string
}

export interface TeamProgress {
  total_assignments: number
  completed: number
  pending: number
  in_progress: number
  completion_percentage: number
  members: TeamMember[]
}

// ============================================================================
// Stakeholder Prototype Review
// ============================================================================

export interface StakeholderEpic {
  index: number
  title: string
  theme?: string | null
  narrative?: string | null
  features: Array<{ name: string; id?: string }>
  primary_route?: string | null
  verdict?: VerdictType | null
  notes?: string | null
  source?: string | null
  stakeholder_id?: string | null
  is_assigned_to_me: boolean
}

export interface StakeholderReviewData {
  session_id: string
  prototype_id: string
  deploy_url?: string
  epics: StakeholderEpic[]
  total_epics: number
}

// ============================================================================
// Client Exploration (Portal v2)
// ============================================================================

export interface EpicAssumption {
  text: string
  source_type: string // 'resolved_decision' | 'pain_point' | 'open_question' | 'inferred'
}

export interface EpicConfig {
  epic_index: number
  enabled: boolean
  display_order: number
  consultant_note?: string | null
  narrative_override?: string | null
  assumptions: EpicAssumption[]
  title?: string
  narrative?: string
}

export interface ClientEpic {
  index: number
  title: string
  narrative: string
  consultant_note?: string | null
  assumptions: EpicAssumption[]
  primary_route?: string | null
  features: Array<{ name: string; description?: string }>
}

export interface ClientExplorationData {
  session_id: string
  deploy_url?: string | null
  project_name: string
  consultant_name?: string | null
  epics: ClientEpic[]
  welcome_message?: string | null
}

export interface AssumptionResult {
  text: string
  source_type: string
  response?: string | null // 'agree' | 'disagree' | null
}

export interface EpicResult {
  epic_index: number
  title: string
  assumptions: AssumptionResult[]
  time_spent_seconds?: number | null
}

export interface ClientExplorationResults {
  session_id: string
  epics: EpicResult[]
  inspirations: Array<{
    id: string
    epic_index?: number | null
    text: string
    created_at: string
  }>
  total_time_seconds?: number | null
  completed_at?: string | null
}

// ============================================================================
// Workflow Validation
// ============================================================================

export interface PortalWorkflowVerdict {
  workflow_id: string
  verdict: string
  signal_id?: string | null
}

// ============================================================================
// Info Requests (Questions)
// ============================================================================

export interface InfoRequest {
  id: string
  project_id: string
  title: string
  description: string | null
  request_type: InfoRequestType
  input_type: InfoRequestInputType
  phase: InfoRequestPhase
  priority: InfoRequestPriority | null
  best_answered_by: string | null
  status: InfoRequestStatus
  answer_data: Record<string, unknown> | null
  why_asking: string | null
  example_answer: string | null
  pro_tip: string | null
  display_order: number
  created_by: 'ai' | 'consultant'
  created_at: string
}

export interface InfoRequestWithDelta extends InfoRequest {
  readiness_delta?: { before: number; after: number; change: number; gates_affected: string[] }
  signal_id?: string | null
  confirmations_resolved: number
}

// ============================================================================
// Station Panel Types
// ============================================================================

export type StationSlug =
  | 'competitors'
  | 'design'
  | 'constraints'
  | 'documents'
  | 'ai_wishlist'
  | 'tribal'
  | 'workflow'
  | 'epic'

export interface ProjectContextData {
  id: string
  project_id: string
  problem_main: string | null
  problem_why_now: string | null
  success_future: string | null
  success_wow: string | null
  key_users: Array<{
    name: string
    role?: string | null
    frustrations?: string[]
    helps?: string[]
  }>
  design_love: Array<{
    name: string
    url?: string | null
    what_like?: string | null
  }>
  design_avoid: string | null
  competitors: Array<{
    name: string
    worked?: string | null
    didnt_work?: string | null
    why_left?: string | null
  }>
  tribal_knowledge: string[]
  metrics: Array<{
    metric: string
    current?: string
    goal?: string
  }>
  completion_scores: {
    problem: number
    success: number
    users: number
    design: number
    competitors: number
    tribal: number
    files: number
    overall: number
  }
  overall_completion: number
}

export interface StationChatMessage {
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isStreaming?: boolean
  toolCalls?: Array<{
    tool_name: string
    status: 'complete' | 'error'
    result?: Record<string, unknown>
  }>
}
