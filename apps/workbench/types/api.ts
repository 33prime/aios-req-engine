// API response types matching the backend schemas

export interface Job {
  id: string
  project_id?: string
  job_type: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  input: Record<string, unknown>
  output: Record<string, unknown>
  error?: string
  run_id: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface Feature {
  id: string
  name: string
  category: string
  is_mvp: boolean
  status: string
  confidence: string
  details?: Record<string, unknown>
  evidence: Record<string, unknown>[]
  confirmation_status?: 'ai_generated' | 'confirmed_consultant' | 'confirmed_client' | 'needs_client'
  created_at: string
  updated_at: string

  // V2 enrichment fields
  overview?: string | null
  target_personas?: Array<{
    persona_id?: string | null
    persona_name: string
    role: 'primary' | 'secondary'
    context: string
  }>
  user_actions?: string[]
  system_behaviors?: string[]
  ui_requirements?: string[]
  rules?: string[]
  integrations?: string[]
  enrichment_status?: 'none' | 'enriched' | 'stale' | null
  enriched_at?: string | null
}

// PrdSection removed - PRD is now generated from features, personas, VP steps

export interface Persona {
  id: string
  project_id: string
  slug: string
  name: string
  role: string | null
  demographics: Record<string, any>
  psychographics: Record<string, any>
  goals: string[]
  pain_points: string[]
  description: string | null
  related_features: string[]
  related_vp_steps: string[]
  confirmation_status: 'ai_generated' | 'confirmed_consultant' | 'confirmed_client' | 'needs_client'
  confirmed_by: string | null
  confirmed_at: string | null
  created_at: string
  updated_at: string
  overview: string | null
  key_workflows: Array<{ name: string; description: string; steps: string[]; features_used: string[] }>
  enrichment_status: 'none' | 'enriched' | 'stale' | null
  enriched_at: string | null
  coverage_score?: number
  health_score?: number
}

// V2 evidence item for VP steps
export interface VpEvidence {
  chunk_id?: string | null
  excerpt: string
  source_type: 'signal' | 'research' | 'inferred'
  rationale: string
}

// V2 feature reference in VP step
export interface VpFeatureRef {
  feature_id: string
  feature_name: string
  role: 'core' | 'supporting'
}

export interface VpStep {
  id: string
  step_index: number
  label: string
  status: string
  description: string
  enrichment?: Record<string, unknown>
  evidence?: VpEvidence[]
  user_benefit_pain?: string
  ui_overview?: string
  value_created?: string
  kpi_impact?: string
  created_at: string
  updated_at: string

  // V2 fields
  actor_persona_id?: string | null
  actor_persona_name?: string | null
  narrative_user?: string | null
  narrative_system?: string | null
  features_used?: VpFeatureRef[]
  rules_applied?: string[]
  integrations_triggered?: string[]
  ui_highlights?: string[]
  confirmation_status?: 'ai_generated' | 'confirmed_consultant' | 'confirmed_client' | 'needs_client'
  has_signal_evidence?: boolean
  generation_status?: 'none' | 'generated' | 'stale'
  generated_at?: string | null
  is_stale?: boolean
  stale_reason?: string | null
  consultant_edited?: boolean
  consultant_edited_at?: string | null
}

export interface Confirmation {
  id: string
  kind: 'vp' | 'feature' | 'insight' | 'gate' | 'persona'
  title: string
  why: string
  ask: string
  status: 'open' | 'queued' | 'resolved' | 'dismissed'
  priority: 'low' | 'medium' | 'high'
  suggested_method: 'email' | 'meeting'
  evidence: Array<{
    chunk_id: string
    excerpt: string
    rationale: string
  }>
  created_at: string
  updated_at: string
}

export interface Signal {
  id: string
  project_id: string
  source: string
  signal_type: string
  raw_text: string
  metadata: Record<string, unknown>
  created_at: string
}

export interface Insight {
  id: string
  project_id: string
  title: string
  severity: 'minor' | 'important' | 'critical'
  gate: 'completeness' | 'validation' | 'assumption' | 'scope' | 'wow'
  finding: string
  why: string
  ask: string
  targets: Array<{
    kind: string
    entity_id: string
    label: string
  }>
  evidence: Array<{
    chunk_id: string
    excerpt: string
    rationale: string
  }>
  status: string
  decision?: string
  created_at: string
  updated_at: string
}

// Projects
export interface Project {
  id: string
  name: string
  description?: string
  prd_mode: 'initial' | 'maintenance'
  status: 'active' | 'archived' | 'completed'
  created_at: string
  updated_at?: string
  signal_id?: string // ID of auto-ingested description signal
  onboarding_job_id?: string // ID of onboarding job (for polling progress)
  launch_status?: 'building' | 'ready' | 'failed' | null
  active_launch_id?: string | null
}

export interface ProjectDetail extends Project {
  counts: {
    signals: number
    vp_steps: number
    features: number
    insights: number
    personas: number
  }
}

// Analytics
export interface ChunkUsageAnalytics {
  project_id: string
  top_chunks: Array<{
    chunk_id: string
    signal_id: string
    chunk_index: number
    content_preview: string
    citation_count: number
  }>
  total_citations: number
  citations_by_entity_type: Record<string, number>
  unused_signals: Array<Signal & {
    chunk_count: number
    impact_count: number
    source_label?: string
    source_type?: string
    source_timestamp?: string
  }>
  unused_signals_count: number
}

// ============================================================================
// Organizations
// ============================================================================

export type OrganizationRole = 'Owner' | 'Admin' | 'Member'
export type InvitationStatus = 'pending' | 'accepted' | 'expired' | 'cancelled'
export type AvailabilityStatus = 'Available' | 'Busy' | 'Away'
export type PlatformRole = 'user' | 'admin' | 'super_admin'

export interface Organization {
  id: string
  name: string
  slug?: string
  created_by_user_id?: string
  logo_url?: string
  settings: Record<string, any>
  created_at: string
  updated_at: string
  archived_at?: string
  deleted_at?: string
  deleted_by_user_id?: string
}

export interface OrganizationWithRole extends Organization {
  current_user_role: OrganizationRole
}

export interface OrganizationSummary {
  id: string
  name: string
  slug?: string
  logo_url?: string
  member_count: number
  project_count: number
  created_at: string
}

export interface OrganizationCreate {
  name: string
  slug?: string
  logo_url?: string
  settings?: Record<string, any>
}

export interface OrganizationUpdate {
  name?: string
  slug?: string
  logo_url?: string
  settings?: Record<string, any>
}

export interface OrganizationMember {
  id: string
  organization_id: string
  user_id: string
  organization_role: OrganizationRole
  invited_by_user_id?: string
  joined_at: string
  created_at: string
}

export interface OrganizationMemberPublic {
  id: string
  user_id: string
  email: string
  first_name?: string
  last_name?: string
  photo_url?: string
  organization_role: OrganizationRole
  joined_at: string
}

export interface Invitation {
  id: string
  organization_id: string
  email: string
  organization_role: OrganizationRole
  invited_by_user_id: string
  invite_token: string
  status: InvitationStatus
  created_at: string
  expires_at: string
  accepted_at?: string
}

export interface InvitationWithOrg extends Invitation {
  organization_name: string
  organization_logo_url?: string
  invited_by_name?: string
}

export interface InvitationCreate {
  email: string
  organization_role?: OrganizationRole
}

export interface Profile {
  id: string
  user_id: string
  first_name?: string
  last_name?: string
  email: string
  photo_url?: string
  linkedin?: string
  meeting_link?: string
  phone_number?: string
  city?: string
  state?: string
  country?: string
  platform_role: PlatformRole
  expertise_areas: string[]
  certifications: string[]
  bio?: string
  availability_status: AvailabilityStatus
  capacity: number
  timezone?: string
  preferences: Record<string, any>
  created_at: string
  updated_at: string

  // Consultant enrichment fields
  enrichment_status?: 'pending' | 'enriching' | 'enriched' | 'failed'
  enriched_profile?: Record<string, any>
  industry_expertise?: string[]
  methodology_expertise?: string[]
  consulting_style?: Record<string, any>
  consultant_summary?: string
  profile_completeness?: number
  enriched_at?: string
  enrichment_source?: string
}

export interface ConsultantEnrichRequest {
  linkedin_text?: string
  website_text?: string
  additional_context?: string
}

export interface ConsultantEnrichResponse {
  status: string
  message: string
  enriched_profile?: Record<string, any>
  profile_completeness: number
}

export interface ConsultantEnrichmentStatus {
  enrichment_status: string
  profile_completeness: number
  enriched_at?: string
  enrichment_source?: string
  enriched_profile: Record<string, any>
  industry_expertise: string[]
  methodology_expertise: string[]
  consulting_style: Record<string, any>
  consultant_summary?: string
}

export interface ProfileUpdate {
  first_name?: string
  last_name?: string
  photo_url?: string
  linkedin?: string
  meeting_link?: string
  phone_number?: string
  city?: string
  state?: string
  country?: string
  bio?: string
  timezone?: string
  expertise_areas?: string[]
  certifications?: string[]
  availability_status?: AvailabilityStatus
  capacity?: number
  preferences?: Record<string, any>
}

// ============================================================================
// Discovery Prep
// ============================================================================

export type PrepStatus = 'draft' | 'confirmed' | 'sent'
export type DocPriority = 'high' | 'medium' | 'low'

export interface PrepQuestion {
  id: string
  question: string
  best_answered_by: string
  why_important: string
  confirmed: boolean
  client_answer?: string
  answered_at?: string
}

export interface DocRecommendation {
  id: string
  document_name: string
  priority: DocPriority
  why_important: string
  confirmed: boolean
  uploaded_file_id?: string
  uploaded_at?: string
}

export interface DiscoveryPrepBundle {
  id: string
  project_id: string
  agenda_summary?: string
  agenda_bullets: string[]
  questions: PrepQuestion[]
  documents: DocRecommendation[]
  status: PrepStatus
  sent_to_portal_at?: string
  generated_at: string
  updated_at: string
}

// ============================================================================
// Meetings
// ============================================================================

export type MeetingType = 'discovery' | 'validation' | 'review' | 'other'
export type MeetingStatus = 'scheduled' | 'completed' | 'cancelled'

export interface Meeting {
  id: string
  project_id: string
  title: string
  description?: string
  meeting_type: MeetingType
  status: MeetingStatus
  meeting_date: string
  meeting_time: string
  duration_minutes: number
  timezone: string
  stakeholder_ids: string[]
  agenda?: Record<string, any>
  summary?: string
  highlights?: Record<string, any>
  google_calendar_event_id?: string
  google_meet_link?: string
  created_by?: string
  created_at: string
  updated_at: string
  // Joined fields
  project_name?: string
}

// ============================================================================
// Communication Integrations
// ============================================================================

export type RecordingDefault = 'on' | 'off' | 'ask'
export type BotStatus = 'deploying' | 'joining' | 'recording' | 'processing' | 'done' | 'failed' | 'cancelled'
export type ConsentStatus = 'pending' | 'all_consented' | 'opted_out' | 'expired'

export interface IntegrationSettings {
  google_connected: boolean
  scopes_granted: string[]
  calendar_sync_enabled: boolean
  recording_default: RecordingDefault
}

export interface GoogleStatusResponse {
  connected: boolean
  scopes: string[]
  calendar_sync_enabled: boolean
}

export interface EmailSubmission {
  project_id: string
  sender: string
  recipients: string[]
  cc: string[]
  subject: string
  body: string
  html_body?: string
}

export interface EmailTokenResponse {
  id: string
  project_id: string
  token: string
  reply_to_address: string
  allowed_sender_domain?: string
  allowed_sender_emails: string[]
  expires_at: string
  is_active: boolean
  emails_received: number
  max_emails: number
  created_at: string
}

export interface MeetingBot {
  id: string
  meeting_id: string
  recall_bot_id: string
  status: BotStatus
  consent_status: ConsentStatus
  signal_id?: string
  transcript_url?: string
  recording_url?: string
  error_message?: string
  created_at: string
  updated_at: string
}

// ============================================================================
// Status Narrative
// ============================================================================

export interface StatusNarrative {
  where_today: string
  where_going: string
  updated_at?: string
}

// ============================================================================
// Extended Project (with new dashboard fields)
// ============================================================================

export type ProjectStage = 'discovery' | 'validation' | 'prototype' | 'prototype_refinement' | 'proposal' | 'build' | 'live'

export interface ProjectWithDashboard extends Project {
  created_by?: string
  stage: ProjectStage
  client_name?: string
  status_narrative?: StatusNarrative
  portal_enabled?: boolean
  portal_phase?: 'pre_call' | 'post_call' | 'building' | 'testing'
  readiness_score?: number
  stage_eligible?: boolean | null
}

// ============================================================================
// Stage Progression
// ============================================================================

export interface StageGateCriterion {
  gate_name: string
  gate_label: string
  satisfied: boolean
  confidence: number
  required: boolean
  missing: string[]
  how_to_acquire: string[]
}

export interface StageStatusResponse {
  current_stage: string
  next_stage: string | null
  can_advance: boolean
  criteria: StageGateCriterion[]
  criteria_met: number
  criteria_total: number
  progress_pct: number
  transition_description: string
  is_final_stage: boolean
}

export interface AdvanceStageRequest {
  target_stage: string
  force?: boolean
  reason?: string
}

export interface AdvanceStageResponse {
  previous_stage: string
  current_stage: string
  forced: boolean
  message: string
}

export interface ProjectDetailWithDashboard extends ProjectWithDashboard {
  counts: {
    signals: number
    vp_steps: number
    features: number
    insights: number
    personas: number
  }
  /** Full cached readiness data for instant display */
  cached_readiness_data?: {
    score: number
    ready: boolean
    threshold: number
    dimensions: Record<string, { score: number; weight: number; weighted_score: number }>
    caps_applied: Array<{ cap_id: string; limit: number; reason: string }>
    top_recommendations: Array<{ action: string; impact: string; effort: string; priority: number }>
    computed_at: string
    confirmed_entities: number
    total_entities: number
    client_signals_count: number
    meetings_completed: number
    // Gate-based readiness fields (DI Agent integration)
    phase?: string  // "insufficient" | "prototype_ready" | "build_ready"
    prototype_ready?: boolean
    build_ready?: boolean
    gates?: {
      prototype_gates: Record<string, any>
      build_gates: Record<string, any>
    }
    next_milestone?: string  // "prototype" | "build" | "complete"
    blocking_gates?: string[]
    gate_score?: number
  } | null
}

// ============================================================================
// Collaboration System (Linear Phase Workflow)
// ============================================================================

export type CollaborationPhase =
  | 'pre_discovery'
  | 'discovery'
  | 'validation'
  | 'prototype'
  | 'proposal'
  | 'build'
  | 'delivery'

export type PhaseStepStatus = 'locked' | 'available' | 'in_progress' | 'completed'

export type PendingItemType =
  | 'feature'
  | 'persona'
  | 'vp_step'
  | 'question'
  | 'document'
  | 'kpi'
  | 'goal'
  | 'pain_point'
  | 'requirement'
  | 'competitor'
  | 'design_preference'
  | 'stakeholder'

export type PendingItemSource =
  | 'phase_workflow'
  | 'needs_review'
  | 'ai_generated'
  | 'manual'

// Phase Progress

export interface PhaseStep {
  id: string
  label: string
  status: PhaseStepStatus
  progress?: { current: number; total: number }
  unlock_message?: string
}

export interface PhaseGate {
  id: string
  label: string
  condition: string
  met: boolean
  current_value?: string | number
  required_for_completion: boolean
}

export interface PhaseProgressConfig {
  phase: CollaborationPhase
  steps: PhaseStep[]
  gates: PhaseGate[]
  readiness_score: number
}

// Pending Items Queue

export interface PendingItem {
  id: string
  item_type: PendingItemType
  source: PendingItemSource
  entity_id?: string
  title: string
  description?: string
  why_needed?: string
  priority: 'high' | 'medium' | 'low'
  created_at: string
  added_by?: string
}

export interface PendingItemsQueue {
  items: PendingItem[]
  by_type: Record<string, number>
  total_count: number
}

// Client Package (AI-Synthesized)

export interface SynthesizedQuestion {
  id: string
  question_text: string
  hint?: string
  suggested_answerer?: string
  why_asking?: string
  example_answer?: string
  covers_items: string[]
  covers_summary?: string
  sequence_order: number
}

export interface ActionItem {
  id: string
  title: string
  description?: string
  item_type: 'document' | 'task' | 'approval'
  hint?: string
  why_needed?: string
  covers_items: string[]
  sequence_order: number
}

export interface AssetSuggestion {
  id: string
  category: 'sample_data' | 'process' | 'data_systems' | 'integration'
  title: string
  description: string
  why_valuable: string
  examples: string[]
  priority: 'high' | 'medium' | 'low'
  phase_relevant: CollaborationPhase[]
}

export interface ClientPackage {
  id: string
  project_id: string
  status: 'draft' | 'sent' | 'responses_received'
  questions: SynthesizedQuestion[]
  action_items: ActionItem[]
  suggested_assets: AssetSuggestion[]
  source_items: string[]
  source_items_count: number
  questions_count: number
  action_items_count: number
  suggestions_count: number
  created_at: string
  sent_at?: string
  updated_at: string
}

// Main Response

export interface PhaseProgressResponse {
  project_id: string
  current_phase: CollaborationPhase
  phases: Array<{
    phase: CollaborationPhase
    status: 'locked' | 'active' | 'completed'
    completed_at?: string
  }>
  phase_config: PhaseProgressConfig
  readiness_score: number
  readiness_gates: PhaseGate[]
  pending_queue: PendingItemsQueue
  draft_package?: ClientPackage
  sent_package?: ClientPackage
  package_responses?: {
    package_id: string
    question_responses: Array<{
      question_id: string
      answer_text: string
      answered_by?: string
      answered_by_name?: string
      answered_at: string
    }>
    action_item_responses: Array<{
      action_item_id: string
      status: 'complete' | 'skipped' | 'partial'
      files: Array<{ id: string; name: string; url: string }>
      notes?: string
      completed_by?: string
      completed_at: string
    }>
    questions_answered: number
    questions_total: number
    action_items_completed: number
    action_items_total: number
    overall_progress: number
  }
  portal_enabled: boolean
  clients_count: number
  last_client_activity?: string
}

// =============================================================================
// Admin Panel Types
// =============================================================================

export interface AdminDashboardStats {
  total_users: number
  active_users_7d: number
  total_projects: number
  active_projects: number
  total_clients: number
  total_signals: number
  total_icp_signals: number
  total_cost_usd: number
  cost_7d_usd: number
  total_tokens: number
  projects_by_stage: Record<string, number>
  users_by_role: Record<string, number>
  recent_signups: Array<{ user_id: string; name?: string; email?: string; photo_url?: string; platform_role: string; created_at: string }>
}

export interface AdminUserSummary {
  user_id: string
  email: string
  first_name?: string | null
  last_name?: string | null
  photo_url?: string | null
  platform_role: string
  enrichment_status?: string | null
  profile_completeness: number
  project_count: number
  signal_count: number
  total_cost_usd: number
  total_tokens: number
  last_active?: string | null
  created_at: string
}

export interface AdminUserDetail {
  profile: Record<string, any>
  projects: Array<Record<string, any>>
  total_signals_submitted: number
  signals_by_type: Record<string, number>
  total_entities_generated: number
  icp_scores: Array<{ profile_name: string; score: number; signal_count: number; computed_at?: string }>
  recent_signals: Array<Record<string, any>>
  enriched_profile?: {
    consultant_summary?: string
    expertise_areas?: string[]
    industry_expertise?: string[]
    methodology_expertise?: string[]
  } | null
  total_cost_usd: number
  total_tokens_input: number
  total_tokens_output: number
  cost_by_workflow: Record<string, number>
  cost_by_model: Record<string, number>
  cost_30d_usd: number
  recent_llm_calls: Array<Record<string, any>>
}

export interface AdminCostAnalytics {
  total_cost_usd: number
  total_tokens_input: number
  total_tokens_output: number
  total_calls: number
  cost_by_workflow: Array<{ workflow: string; cost: number; calls: number; tokens: number }>
  cost_by_model: Array<{ model: string; provider: string; cost: number; calls: number; tokens: number }>
  cost_by_user: Array<{ user_id: string; name: string; email: string; cost: number; calls: number }>
  daily_cost: Array<{ date: string; cost: number; calls: number }>
}

export interface AdminProjectSummary {
  id: string
  name: string
  stage?: string | null
  status?: string | null
  client_name?: string | null
  owner_id?: string | null
  owner_name?: string | null
  owner_photo_url?: string | null
  signal_count: number
  feature_count: number
  readiness_score?: number | null
  created_at: string
}

export interface LeaderboardEntry {
  rank: number
  user_id: string
  name: string
  email: string
  photo_url?: string | null
  score: number
  signal_count: number
  computed_at?: string
}

// Eval Pipeline
export interface EvalDashboardStats {
  total_runs: number
  avg_score: number
  first_pass_rate: number
  top_gaps: Array<{ dimension: string; count: number }>
  version_distribution: Record<string, number>
  score_trend: Array<{ date: string; score: number }>
  avg_iterations: number
  total_cost_usd: number
}

export interface EvalRunListItem {
  id: string
  prompt_version_id: string
  prototype_id: string
  iteration_number: number
  overall_score: number
  det_composite: number
  llm_overall: number
  action: 'pending' | 'accept' | 'retry' | 'notify'
  estimated_cost_usd: number
  created_at: string
}

export interface EvalGap {
  id: string
  eval_run_id: string
  dimension: string
  description: string
  severity: 'high' | 'medium' | 'low'
  feature_ids: string[]
  gap_pattern?: string | null
  resolved_in_run_id?: string | null
  resolved_at?: string | null
  created_at: string
}

export interface EvalRunDetail extends EvalRunListItem {
  det_handoff_present: boolean
  det_feature_id_coverage: number
  det_file_structure: number
  det_route_count: number
  det_jsdoc_coverage: number
  llm_feature_coverage: number
  llm_structure: number
  llm_mock_data: number
  llm_flow: number
  llm_feature_id: number
  file_tree: string[]
  feature_scan: Record<string, string[]>
  handoff_content?: string | null
  recommendations: string[]
  deterministic_duration_ms: number
  llm_duration_ms: number
  tokens_input: number
  tokens_output: number
  tokens_cache_read: number
  tokens_cache_create: number
  gaps: EvalGap[]
}

export interface EvalPromptVersion {
  id: string
  prototype_id: string
  version_number: number
  prompt_text: string
  parent_version_id?: string | null
  generation_model?: string | null
  generation_chain?: string | null
  input_context_snapshot: Record<string, unknown>
  learnings_injected: Record<string, unknown>[]
  tokens_input: number
  tokens_output: number
  estimated_cost_usd: number
  created_at: string
  latest_score?: number | null
  latest_action?: string | null
}

export interface EvalPromptDiff {
  version_a: EvalPromptVersion
  version_b: EvalPromptVersion
}

export interface EvalLearning {
  id: string
  category: string
  learning: string
  source_prototype_id?: string | null
  effectiveness_score: number
  active: boolean
  eval_run_id?: string | null
  dimension?: string | null
  gap_pattern?: string | null
  created_at: string
}

// Notifications
export interface Notification {
  id: string
  type: string
  title: string
  body: string | null
  project_id: string | null
  entity_type?: string | null
  entity_id?: string | null
  read: boolean
  created_at: string
  metadata: Record<string, unknown>
}

// Project Pulse
export interface ProjectPulse {
  score: number
  summary: string
  background: string | null
  vision: string | null
  entity_counts: Record<string, number>
  strengths: string[]
  next_actions: Array<{
    title: string
    description: string
    priority: string
  }>
  first_visit: boolean
}

// Client Pulse (lightweight engagement metrics for Collaborate view)
export interface ClientPulse {
  pending_count: number
  unread_count: number
  next_meeting: { title: string; date: string } | null
  last_client_activity: string | null
}

// Client Activity (unified timeline entry)
export interface ClientActivityItem {
  id: string
  type: 'answer' | 'upload' | 'view' | 'annotation' | 'confirmation'
  actor_name: string
  description: string
  timestamp: string
  entity_type?: string
  entity_id?: string
}

// Chat Summary (from onboarding chat)
export interface ChatSummary {
  name: string
  problem: string
  users: string
  features: string
  org_fit: string
}

// =============================================================================
// Signal Processing Results
// =============================================================================

export interface EntityChangeItem {
  entity_type: string
  entity_id: string
  entity_label: string
  revision_type: 'created' | 'updated' | 'merged' | 'enriched'
  changes: Record<string, unknown>
  diff_summary: string | null
  created_at: string
}

export interface MemoryUpdateItem {
  id: string
  node_type: 'fact' | 'belief' | 'insight'
  content: string
  confidence: number | null
  status: string
  created_at: string
}

export interface ProcessingSummary {
  total_entities_affected: number
  created: number
  updated: number
  merged: number
  escalated: number
  memory_facts_added: number
  by_entity_type: Record<string, number>
  triage_strategy: string
  confidence_distribution: Record<string, number>
}

export interface ProcessingResultsResponse {
  signal_id: string
  patch_summary: Record<string, unknown>
  entity_changes: EntityChangeItem[]
  memory_updates: MemoryUpdateItem[]
  summary: ProcessingSummary
}

export interface BatchConfirmRequest {
  signal_id: string
  scope: 'new' | 'updates' | 'all' | 'defer'
}

export interface BatchConfirmResponse {
  confirmed_count: number
  entity_ids: string[]
  tasks_created: number
}

// =============================================================================
// Pulse Engine
// =============================================================================

export interface PulseSnapshot {
  id: string | null
  project_id: string
  stage: string
  stage_progress: number
  gates: string[]
  gates_met: number
  gates_total: number
  health: Record<string, {
    entity_type: string
    count: number
    confirmed: number
    stale: number
    confirmation_rate: number
    staleness_rate: number
    coverage: string
    quality: number
    freshness: number
    health_score: number
    directive: string
    target: number
  }>
  actions: Array<{
    sentence: string
    impact_score: number
    entity_type: string | null
    unblocks_gate: boolean
  }>
  risks: {
    contradiction_count: number
    stale_clusters: number
    critical_questions: number
    single_source_types: number
    risk_score: number
  }
  forecast: {
    prototype_readiness: number
    spec_completeness: number
    confidence_index: number
    coverage_index: number
  }
  extraction_directive: Record<string, unknown>
  config_version: string
  rules_fired: string[]
  trigger: string
  created_at: string | null
}

// =============================================================================
// Pulse Admin
// =============================================================================

export interface AdminPulseConfigSummary {
  id: string
  project_id: string | null
  version: string
  label: string
  is_active: boolean
  created_at: string
}

export interface AdminProjectPulse {
  project_id: string
  project_name: string
  stage: string
  stage_progress: number
  health_scores: Record<string, number>
  risk_score: number
  top_action: string | null
  snapshot_count: number
  last_snapshot_at: string | null
}
