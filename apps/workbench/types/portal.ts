/** Portal TypeScript types for the Client Portal v1 — Validation Machine. */

// ============================================================================
// Enums / Literals
// ============================================================================

export type PortalRole = 'client_admin' | 'client_user'
export type VerdictType = 'confirmed' | 'refine' | 'flag'
export type AssignmentStatus = 'pending' | 'in_progress' | 'completed' | 'skipped'

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
