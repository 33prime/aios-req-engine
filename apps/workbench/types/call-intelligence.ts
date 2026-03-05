/**
 * Call Intelligence types — mirrors backend schemas_call_intelligence.py
 */

// Status machine
export type CallRecordingStatus =
  | 'pending'
  | 'bot_scheduled'
  | 'recording'
  | 'transcribing'
  | 'analyzing'
  | 'complete'
  | 'skipped'
  | 'failed'

// Enums
export type ReactionType = 'excited' | 'interested' | 'neutral' | 'confused' | 'resistant'
export type CallSignalType = 'pain_point' | 'goal' | 'budget_indicator' | 'timeline' | 'decision_criteria' | 'risk_factor'
export type NuggetType = 'testimonial' | 'soundbite' | 'statistic' | 'use_case' | 'objection' | 'vision_statement'
export type SentimentType = 'positive' | 'neutral' | 'negative'

// Core interfaces — match RecordingResponse from backend
export interface CallRecording {
  id: string
  project_id: string
  meeting_id?: string | null
  recall_bot_id?: string | null
  meeting_bot_id?: string | null
  title?: string | null
  status: CallRecordingStatus
  audio_url?: string | null
  video_url?: string | null
  recording_url?: string | null
  duration_seconds?: number | null
  signal_id?: string | null
  error_message?: string | null
  error_step?: string | null
  created_at: string
  updated_at: string
}

// TranscriptResponse from backend
export interface CallTranscript {
  id: string
  recording_id: string
  full_text: string
  segments: TranscriptSegment[]
  speaker_map: Record<string, string>
  word_count: number
  language: string
  provider: string
  model: string
}

// AnalysisResponse from backend
export interface CallAnalysis {
  id: string
  recording_id: string
  engagement_score?: number | null
  talk_ratio: Record<string, number>
  engagement_timeline: Array<Record<string, unknown>>
  executive_summary?: string | null
  custom_dimensions: Record<string, unknown>
  dimension_packs_used: string[]
  model?: string | null
  tokens_input: number
  tokens_output: number
}

// Child record types (returned as dict[] from backend)
export interface FeatureInsight {
  id: string
  recording_id: string
  feature_name: string
  reaction: ReactionType
  quote?: string | null
  context?: string | null
  timestamp_seconds?: number | null
  is_aha_moment: boolean
}

export interface CallSignal {
  id: string
  recording_id: string
  signal_type: CallSignalType
  title: string
  description?: string | null
  intensity: number
  quote?: string | null
}

export interface ContentNugget {
  id: string
  recording_id: string
  nugget_type: NuggetType
  content: string
  speaker?: string | null
  reuse_score: number
}

export interface CompetitiveMention {
  id: string
  recording_id: string
  competitor_name: string
  sentiment: SentimentType
  context?: string | null
  quote?: string | null
  feature_comparison?: string | null
}

export interface TranscriptSegment {
  speaker: string
  text: string
  start: number
  end: number
}

// Discovery Themes (v3 — workflow-first, replaces call_goals + questions + focus_areas)
export interface MissionTheme {
  theme: string
  context: string
  question: string
  explores: string
  evidence: string[]
  confidence: number
  priority: 'critical' | 'high' | 'medium'
}

export interface MeetingFrame {
  phase: string
  question_goal: string
  categories: string[]
}

// Strategy Brief types — enriched stakeholder intelligence
export interface StakeholderIntel {
  name: string
  role?: string
  influence: string
  stakeholder_type: string
  key_concerns: string[]
  approach_notes: string
  // Enrichment fields (optional — populated when SI agent has run)
  priorities?: string[]
  domain_expertise?: string[]
  engagement_level?: string | null
  decision_authority?: string | null
  approval_required_for?: string[]
  veto_power_over?: string[]
  win_conditions?: string[]
  risk_if_disengaged?: string | null
  preferred_channel?: string | null
  profile_completeness?: number
  topic_mentions?: Record<string, number>
  owns_entities?: string[]
}

export interface MissionCriticalQuestion {
  question: string
  why_important: string
  target_stakeholder: string
  gap_ids: string[]
}

export interface CallGoal {
  goal: string
  success_criteria: string
  linked_gap_ids: string[]
}

export interface DealReadinessSnapshot {
  score: number
  components: { name: string; score: number; max: number; details: string }[]
  gaps_and_risks: { title: string; severity: string; description: string }[]
}

export interface AmbiguitySnapshot {
  score: number
  factors: Record<string, { confidence_gap: number; contradiction_rate: number; coverage_sparsity: number; gap_density: number }>
  top_ambiguous_beliefs: { summary: string; confidence: number; domain: string }[]
}

export interface FocusArea {
  area: string
  priority: 'high' | 'medium' | 'low'
  context: string
}

export interface ProjectAwarenessSnapshot {
  phase: string
  flow_summary: string
  whats_next: string[]
  whats_working?: string[]
  whats_discovered?: string[]
}

export interface CriticalRequirement {
  name: string
  entity_type: string
  status: string
  context: string
}

export interface GoalResult {
  goal: string
  achieved: 'yes' | 'partial' | 'no' | 'unknown'
  evidence: string
  gaps_remaining: string[]
}

export interface ReadinessDelta {
  before_score: number
  after_score: number
  component_deltas: { name: string; before: number; after: number }[]
}

export interface CallStrategyBrief {
  id: string
  project_id: string
  meeting_id?: string | null
  recording_id?: string | null
  stakeholder_intel: StakeholderIntel[]
  mission_critical_questions: MissionCriticalQuestion[]
  call_goals: CallGoal[]
  deal_readiness_snapshot: DealReadinessSnapshot
  ambiguity_snapshot: AmbiguitySnapshot
  focus_areas: FocusArea[]
  project_awareness_snapshot: ProjectAwarenessSnapshot
  critical_requirements?: CriticalRequirement[]
  mission_themes?: MissionTheme[]
  meeting_frame?: MeetingFrame | null
  retrieval_metadata?: Record<string, unknown> | null
  goal_results?: GoalResult[] | null
  readiness_delta?: ReadinessDelta | null
  generated_by?: string
  model?: string | null
  created_at: string
  updated_at?: string
}

// Consultant performance types
export interface ConsultantPerformance {
  question_quality: { score: number; open_vs_closed_ratio: number; best_question: string; missed_opportunities: string[] }
  active_listening: { score: number; paraphrase_count: number; follow_up_depth: number; examples: string[] }
  discovery_depth: { score: number; surface_questions: number; deep_questions: number; reframe_moments: string[] }
  objection_handling: { score: number; objections_surfaced: number; objections_addressed: number; technique_notes: string[] }
  next_steps_clarity: { score: number; commitments_made: string[]; follow_ups_assigned: string[]; ambiguous_items: string[] }
  consultant_talk_ratio: { consultant_share: number; ideal_range: string; assessment: string }
  consultant_summary: string
}

// Aggregated detail response — matches CallDetails from backend
export interface CallDetails {
  recording: CallRecording
  transcript?: CallTranscript | null
  analysis?: CallAnalysis | null
  feature_insights: FeatureInsight[]
  call_signals: CallSignal[]
  content_nuggets: ContentNugget[]
  competitive_mentions: CompetitiveMention[]
  consultant_performance?: ConsultantPerformance | null
  strategy_brief?: CallStrategyBrief | null
}
