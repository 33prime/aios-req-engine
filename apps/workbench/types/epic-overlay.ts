/**
 * Types for the Epic Overlay system — mirrors backend schemas_epic_overlay.py.
 *
 * 4 tour flows:
 *   1. Vision Journey (5-7 epics)
 *   2. AI Deep Dive (2-3 cards)
 *   3. Horizons (H1/H2/H3)
 *   4. Discovery Threads (gap clusters)
 */

export type EpicTourPhase = 'vision_journey' | 'ai_deep_dive' | 'horizons' | 'discovery'

export interface EpicStoryBeat {
  content: string
  signal_id?: string | null
  chunk_id?: string | null
  speaker_name?: string | null
  source_label?: string | null
  entity_type?: string | null
  entity_id?: string | null
  confidence?: number | null
}

export interface EpicFeature {
  feature_id: string
  name: string
  description?: string | null
  slug?: string | null
  route?: string | null
  confidence: number
  implementation_status: 'functional' | 'partial' | 'placeholder'
  handoff_routes: string[]
  component_name?: string | null
}

export interface ProvenanceQuote {
  speaker_name: string
  quote_text: string
  source_label?: string | null
}

export interface ResolvedDecision {
  decision: string
  rationale?: string | null
  source_reference?: string | null
}

export interface Epic {
  epic_index: number
  title: string
  theme: string
  narrative: string
  provenance_quotes?: ProvenanceQuote[]
  resolved_decisions?: ResolvedDecision[]
  story_beats: EpicStoryBeat[]
  features: EpicFeature[]
  primary_route?: string | null
  all_routes: string[]
  solution_flow_step_ids: string[]
  phase: string
  open_questions: string[]
  gap_cluster_ids: string[]
  persona_names: string[]
  avg_confidence: number
  pain_points: string[]
}

export interface AIFlowCard {
  title: string
  narrative: string
  ai_role: string
  data_in: string[]
  behaviors: string[]
  guardrails: string[]
  output: string
  route?: string | null
  feature_ids: string[]
  solution_flow_step_ids: string[]
}

export interface HorizonCard {
  horizon: 1 | 2 | 3
  title: string
  subtitle: string
  unlock_summaries: string[]
  compound_decisions: string[]
  avg_confidence: number
  why_now: string[]
}

export interface DiscoveryThread {
  thread_id: string
  theme: string
  features: string[]
  feature_ids: string[]
  questions: string[]
  knowledge_type?: string | null
  speaker_hints: Array<{ name: string; role: string; mention_count: number }>
  severity: number
}

export type EpicVerdict = 'confirmed' | 'refine' | 'flag_for_client'
export type EpicCardType = 'vision' | 'ai_flow' | 'horizon' | 'discovery'

export interface EpicConfirmation {
  id: string
  session_id: string
  card_type: EpicCardType
  card_index: number
  verdict: EpicVerdict | null
  notes: string | null
  answer: string | null
  source: 'consultant' | 'client'
}

export interface SubmitEpicVerdictRequest {
  card_type: EpicCardType
  card_index: number
  verdict: EpicVerdict | null
  notes?: string | null
  answer?: string | null
  source?: 'consultant' | 'client'
}

export interface EpicOverlayPlan {
  vision_epics: Epic[]
  ai_flow_cards: AIFlowCard[]
  horizon_cards: HorizonCard[]
  discovery_threads: DiscoveryThread[]
  total_features_mapped: number
  total_features_unmapped: number
  generated_at?: string | null
  iteration: number
}

// Review state machine
export type ReviewState =
  | 'not_started'
  | 'in_progress'
  | 'complete'
  | 'updating'
  | 're_review'
  | 'ready_for_client'

export interface ReviewSummaryItem {
  card_index: number
  verdict: EpicVerdict
  notes?: string | null
  title?: string
}

export interface ReviewSummary {
  total_epics: number
  touched: number
  all_touched: boolean
  tallies: {
    confirmed: number
    refine: number
    flag_for_client: number
  }
  items: ReviewSummaryItem[]
  changes_brief?: string | null
}
