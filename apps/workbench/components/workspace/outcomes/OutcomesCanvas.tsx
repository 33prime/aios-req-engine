'use client'

import { useState, useCallback } from 'react'
import { Target, Users, GitBranch, ChevronDown, ChevronUp, Loader2, AlertTriangle, MessageCircle, Sparkles } from 'lucide-react'
import { useOutcomesTab } from '@/lib/hooks/use-api'
import { IntelligenceSection } from '../brd/sections/IntelligenceSection'
import { WorkflowsSection } from '../brd/sections/WorkflowsSection'
import type { WorkflowPair, ROISummary } from '@/types/workspace'
import type { SynthesizedAction } from '@/lib/api/workspace'

// ============================================================================
// Types
// ============================================================================

interface ActorOutcome {
  persona_name: string
  persona_id?: string | null
  title: string
  before_state: string
  after_state: string
  metric: string
  strength_score: number
  status: string
  sharpen_prompt?: string | null
}

interface ConnectedEntity {
  entity_id: string
  entity_type: string
  link_type: string
  how_served?: string | null
}

interface Outcome {
  id: string
  title: string
  description: string
  strength_score: number
  strength_dimensions: Record<string, number>
  horizon: string
  status: string
  confirmation_status: string
  what_helps: string[]
  evidence: Array<{ direction: string; text: string; source?: string }>
  proof_scenario?: string
  success_measurement?: string
  actors: ActorOutcome[]
  connected_workflows: ConnectedEntity[]
  connected_constraints: ConnectedEntity[]
  connected_features: ConnectedEntity[]
  surfaces: ConnectedEntity[]
  tension_with?: { outcome_id: string; outcome_title: string } | null
}

interface Actor {
  id: string
  name: string
  role: string
  description: string
  goals: string[]
  pain_points: string[]
  outcomes: Array<{
    outcome_id: string
    outcome_title: string
    outcome_strength: number
    outcome_horizon: string
    actor_title: string
    actor_strength: number
    actor_status: string
    before_state?: string
    after_state?: string
    metric?: string
  }>
  outcome_count: number
  journey: Array<{ step_id: string; title: string; step_index: number; phase: string }>
}

interface Workflow {
  id: string
  name: string
  description: string
  state_type?: string
  confirmation_status: string
  steps: Array<{
    id: string
    label: string
    description?: string | null
    step_index: number
    actor_persona_name?: string
    time_minutes?: number | null
    automation_level?: string
    pain_description?: string | null
    benefit_description?: string | null
  }>
  step_count: number
  paired_steps?: Array<{
    id: string
    label: string
    description?: string | null
    step_index: number
    actor_persona_name?: string
    time_minutes?: number | null
    automation_level?: string
    pain_description?: string | null
    benefit_description?: string | null
  }> | null
  roi?: {
    current_total_minutes: number
    future_total_minutes: number
    time_saved_minutes: number
    time_saved_percent: number
    steps_automated: number
    steps_total: number
    cost_saved_per_week?: number
    cost_saved_per_year?: number
  } | null
  outcomes_served: Array<{ outcome_id: string; outcome_title: string }>
}

interface OutcomesTabData {
  macro_outcome: string | null
  outcome_thesis: string | null
  rollup: {
    total_outcomes: number
    strong_outcomes: number
    avg_strength: number
    total_actors: number
    total_workflows: number
    weak_outcomes: Array<{ title: string; strength: number }>
  }
  outcomes: Outcome[]
  actors: Actor[]
  workflows: Workflow[]
  workflow_pairs?: WorkflowPair[]
  roi_summary?: ROISummary[]
}

// ============================================================================
// Persona colors (matches BRD patterns)
// ============================================================================

const PERSONA_COLORS: Record<string, string> = {}
const COLOR_PALETTE = ['#3FAF7A', '#044159', '#0A1E2F', '#2D6B4A', '#C49A1A', '#8B5CF6']
let colorIdx = 0
function getPersonaColor(name: string): string {
  if (!PERSONA_COLORS[name]) {
    PERSONA_COLORS[name] = COLOR_PALETTE[colorIdx % COLOR_PALETTE.length]
    colorIdx++
  }
  return PERSONA_COLORS[name]
}

// ============================================================================
// Props
// ============================================================================

interface OutcomesCanvasProps {
  projectId: string
  onSendToChat?: (message: string) => void
  onActionClick?: (action: SynthesizedAction) => void
}

// ============================================================================
// Component
// ============================================================================

export function OutcomesCanvas({ projectId, onSendToChat, onActionClick }: OutcomesCanvasProps) {
  const { data: rawData, error: swrError, isLoading, mutate } = useOutcomesTab(projectId)
  const data = rawData as OutcomesTabData | undefined
  const loading = isLoading && !data
  const error = swrError ? (swrError as Error).message : null
  const [openOutcomes, setOpenOutcomes] = useState<Set<string>>(new Set())

  const toggleOutcome = useCallback((id: string) => {
    setOpenOutcomes(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }, [])

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-7 py-6">
        {/* Rollup skeleton */}
        <div className="bg-white rounded-2xl shadow-md border border-border p-5 mb-5 animate-pulse">
          <div className="h-5 bg-gray-200 rounded w-3/4 mb-3" />
          <div className="h-3 bg-gray-100 rounded w-1/2" />
        </div>
        {/* Outcome cards skeleton */}
        <div className="flex items-center gap-2 mb-3 mt-6">
          <div className="h-4 w-4 bg-gray-200 rounded" />
          <div className="h-3 bg-gray-200 rounded w-20" />
          <div className="flex-1 h-px bg-gray-100" />
        </div>
        {[1,2,3].map(i => (
          <div key={i} className="bg-white rounded-2xl shadow-md border border-border p-4 mb-2.5 animate-pulse">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-full bg-gray-200" />
              <div className="flex-1">
                <div className="h-3 bg-gray-200 rounded w-16 mb-2" />
                <div className="h-4 bg-gray-200 rounded w-3/4" />
              </div>
            </div>
          </div>
        ))}
        {/* Actors skeleton */}
        <div className="flex items-center gap-2 mb-3 mt-6">
          <div className="h-4 w-4 bg-gray-200 rounded" />
          <div className="h-3 bg-gray-200 rounded w-16" />
          <div className="flex-1 h-px bg-gray-100" />
        </div>
        <div className="grid grid-cols-2 gap-3 mb-8">
          {[1,2].map(i => (
            <div key={i} className="bg-white rounded-2xl shadow-md border border-border p-3.5 animate-pulse">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-gray-200" />
                <div className="flex-1">
                  <div className="h-3 bg-gray-200 rounded w-24 mb-1" />
                  <div className="h-2 bg-gray-100 rounded w-32" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <div className="flex items-center text-red-500 text-sm">
          <AlertTriangle className="w-4 h-4 mr-2" />
          {error}
        </div>
        <button
          onClick={() => mutate()}
          className="px-4 py-2 text-sm text-white bg-[#3FAF7A] rounded-lg hover:bg-[#25785A] transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  if (!data) return null

  const { outcomes, actors, workflows, rollup } = data as OutcomesTabData

  return (
    <div className="max-w-5xl mx-auto px-7 py-6 pb-24">
      {/* Document header */}
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <Target className="w-6 h-6 text-text-placeholder" />
          <h1 className="text-[28px] font-bold text-[#37352f]">Outcomes</h1>
        </div>
        <p className="mt-2 text-[13px] text-[#666666] leading-relaxed">
          The measurable changes this project must deliver — each outcome traced to actors, workflows, and evidence.
        </p>
      </div>

      {/* ── Intelligence (BRD-style) ── */}
      <IntelligenceSection
        projectId={projectId}
        onActionClick={onActionClick}
      />

      {/* ── Rollup ── */}
      <RollupSection
        macroOutcome={data.macro_outcome}
        rollup={rollup}
      />

      {/* ── Outcomes ── */}
      <SectionHeader icon={Target} title="Outcomes" count={outcomes.length} />
      {outcomes.length === 0 ? (
        <div className="border border-dashed border-[#D4D4D4] rounded-xl p-6 mb-8 text-center">
          <Sparkles className="w-6 h-6 text-[#3FAF7A] mx-auto mb-2" />
          <div className="text-[13px] font-semibold text-[#1D1D1F] mb-1">No outcomes yet</div>
          <p className="text-[11px] text-[#718096] leading-relaxed max-w-md mx-auto mb-3">
            Outcomes are generated when you feed signals into the system — meeting notes, PRDs, emails, or research docs.
            You can also create outcomes directly by describing what must change.
          </p>
          <button
            onClick={() => {
              // Trigger keyboard shortcut to open chat
              window.dispatchEvent(new KeyboardEvent('keydown', { key: 'j', metaKey: true }))
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-lg hover:bg-[#25785A] transition-colors"
          >
            <MessageCircle className="w-3.5 h-3.5" />
            Open chat to get started
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 mb-8">
          {outcomes.map(outcome => (
            <OutcomeCard
              key={outcome.id}
              outcome={outcome}
              isOpen={openOutcomes.has(outcome.id)}
              onToggle={() => toggleOutcome(outcome.id)}
              onSendToChat={onSendToChat}
            />
          ))}
        </div>
      )}

      {/* ── Actors ── */}
      <SectionHeader icon={Users} title="Actors" count={actors.length} />
      <div className="grid grid-cols-2 gap-3 mb-8">
        {actors.map(actor => (
          <ActorCard key={actor.id} actor={actor} />
        ))}
      </div>

      {/* ── Workflows (BRD-style) ── */}
      {(data.workflow_pairs?.length ?? 0) > 0 && (
        <div className="mt-6">
          <WorkflowsSection
            workflows={[]}
            workflowPairs={data.workflow_pairs}
            roiSummary={data.roi_summary}
            sectionTitle="Workflows"
            onConfirm={() => {}}
            onNeedsReview={() => {}}
            onConfirmAll={() => {}}
          />
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Sub-components
// ============================================================================

function SectionHeader({ icon: Icon, title, count }: { icon: any; title: string; count: number }) {
  return (
    <div className="flex items-center gap-2 mb-3 mt-6">
      <Icon className="w-4 h-4 text-[#0A1E2F]" />
      <span className="text-sm font-bold text-[#0A1E2F]">{title}</span>
      <span className="text-xs font-semibold text-[#A0AEC0]">{count}</span>
      <div className="flex-1 h-px bg-[#E5E5E5]" />
    </div>
  )
}

function RollupSection({ macroOutcome, rollup }: { macroOutcome: string | null; rollup: OutcomesTabData['rollup'] }) {
  const strengthColor = rollup.avg_strength >= 85 ? '#3FAF7A' : rollup.avg_strength >= 70 ? '#25785A' : '#C49A1A'

  return (
    <div className="bg-white rounded-2xl shadow-md border border-border p-5 mb-5">
      {macroOutcome && (
        <>
          <div className="text-[8px] font-bold uppercase tracking-[0.07em] text-[#A0AEC0] mb-1">
            Macro Outcome
          </div>
          <div className="text-lg font-bold text-[#0A1E2F] leading-snug mb-3">
            {macroOutcome}
          </div>
        </>
      )}
      <div className="flex items-center gap-4 text-xs text-[#4A5568]">
        <span><strong className="text-[#1D1D1F]">{rollup.total_outcomes}</strong> outcomes</span>
        <span><strong style={{ color: strengthColor }}>{rollup.strong_outcomes}</strong> strong (90+)</span>
        <span>Avg strength <strong style={{ color: strengthColor }}>{rollup.avg_strength}</strong></span>
        <span><strong className="text-[#1D1D1F]">{rollup.total_actors}</strong> actors</span>
        <span><strong className="text-[#1D1D1F]">{rollup.total_workflows}</strong> workflows</span>
      </div>
      {rollup.weak_outcomes.length > 0 && (
        <div className="mt-2 text-[10px] text-[#C49A1A] font-medium">
          Needs sharpening: {rollup.weak_outcomes.map(w => `${w.title.slice(0, 40)}... (${w.strength})`).join(', ')}
        </div>
      )}
    </div>
  )
}

// ── Outcome Card ──

function OutcomeCard({
  outcome, isOpen, onToggle, onSendToChat,
}: {
  outcome: Outcome; isOpen: boolean; onToggle: () => void; onSendToChat?: (msg: string) => void
}) {
  const circ = 2 * Math.PI * 15
  const offset = circ - (outcome.strength_score / 100) * circ
  const color = outcome.strength_score >= 90 ? '#3FAF7A' : outcome.strength_score >= 70 ? '#25785A' : '#C49A1A'

  return (
    <div className={`bg-white rounded-2xl shadow-md border border-border overflow-hidden transition-all ${isOpen ? 'ring-1 ring-[#3FAF7A] xl:col-span-2' : 'hover:border-[#D4D4D4]'}`}>
      {/* Header */}
      <div className="flex items-start gap-3 p-4 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#3FAF7A] focus-visible:rounded-xl" role="button" tabIndex={0} onClick={onToggle} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onToggle() } }}>
        {/* Strength ring */}
        <div className="relative w-10 h-10 flex-shrink-0 group/ring">
          <svg width={40} height={40} viewBox="0 0 40 40" style={{ transform: 'rotate(-90deg)' }}>
            <circle cx={20} cy={20} r={15} fill="none" stroke="#F3F4F6" strokeWidth={3} />
            <circle cx={20} cy={20} r={15} fill="none" stroke={color} strokeWidth={3}
              strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[11px] font-bold text-[#2D3748]">
            {outcome.strength_score}
          </span>
          {/* Strength dimension tooltip */}
          <div className="absolute -bottom-1 left-1/2 -translate-x-1/2 translate-y-full opacity-0 group-hover/ring:opacity-100 transition-opacity pointer-events-none z-20">
            <div className="bg-[#0A1E2F] text-white rounded-lg px-3 py-2 text-[8px] whitespace-nowrap shadow-lg mt-2">
              <div className="flex gap-3">
                {Object.entries(outcome.strength_dimensions || {}).map(([key, val]) => (
                  <div key={key} className="text-center">
                    <div className="font-bold text-[10px]">{typeof val === 'number' ? val : 0}</div>
                    <div className="text-[7px] text-gray-400 capitalize">{key.replace(/_/g, ' ')}</div>
                  </div>
                ))}
              </div>
              <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-[#0A1E2F] rotate-45" />
            </div>
          </div>
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-[7px] font-bold uppercase tracking-[0.06em] text-[#A0AEC0] mb-0.5">
            Outcome {outcome.horizon.toUpperCase()}
          </div>
          <div className="text-[13px] font-semibold text-[#1D1D1F] leading-snug">
            {outcome.title}
          </div>
          {/* Tags */}
          <div className="flex gap-1 flex-wrap mt-1.5">
            <span className={`text-[8px] font-semibold px-2 py-0.5 rounded ${
              outcome.horizon === 'h1' ? 'bg-green-50 text-green-700' : 'bg-teal-50 text-teal-700'
            }`}>
              {outcome.horizon.toUpperCase()}
            </span>
            {outcome.actors.map(a => (
              <span key={a.persona_name} className="text-[8px] font-medium px-2 py-0.5 rounded bg-gray-100 text-[#4A5568]"
                style={{ borderLeft: `2px solid ${getPersonaColor(a.persona_name)}` }}>
                {a.persona_name}
              </span>
            ))}
            {outcome.tension_with && (
              <span className="text-[8px] font-semibold px-2 py-0.5 rounded bg-amber-50 text-amber-700">
                ↔ Tension
              </span>
            )}
          </div>
        </div>

        {isOpen ? <ChevronUp className="w-4 h-4 text-[#A0AEC0] mt-1.5" /> : <ChevronDown className="w-4 h-4 text-[#A0AEC0] mt-1.5" />}
      </div>

      {/* Expanded body */}
      {isOpen && (
        <div className="border-t border-[#E5E5E5]">
          {/* Proof scenario */}
          {outcome.evidence?.length > 0 && (
            <div className="px-4 pt-3 pb-2">
              <div className="text-[7px] font-bold uppercase tracking-[0.06em] text-[#25785A] mb-1">
                How We Prove It
              </div>
              <div className="text-[11px] text-[#2D3748] leading-relaxed italic bg-[#F7FAFC] rounded-lg p-3 border-l-[3px] border-[#3FAF7A]">
                {outcome.evidence[0]?.text}
              </div>
            </div>
          )}

          {/* Actor outcomes */}
          <div className="px-4 pt-2 pb-3">
            <div className="text-[7px] font-bold uppercase tracking-[0.06em] text-[#A0AEC0] mb-2">
              Actor Outcomes ({outcome.actors.length})
            </div>
            {outcome.actors.map(actor => (
              <div key={actor.persona_name}
                className="flex gap-2.5 mb-2 p-2.5 bg-[#F7FAFC] rounded-lg"
                style={{ borderLeft: `3px solid ${getPersonaColor(actor.persona_name)}` }}>
                <div className="w-6 h-6 rounded-md flex items-center justify-center text-[9px] font-bold text-white flex-shrink-0"
                  style={{ background: getPersonaColor(actor.persona_name) }}>
                  {actor.persona_name[0]}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[9px] font-bold text-[#0A1E2F]">{actor.persona_name}</div>
                  <div className="text-[10px] text-[#2D3748] leading-snug mt-0.5">{actor.title}</div>
                  {actor.before_state && actor.after_state && (
                    <div className="grid grid-cols-[1fr_20px_1fr] gap-0 mt-1.5 border border-[#E5E5E5] rounded overflow-hidden text-[9px]">
                      <div className="p-1.5 bg-[rgba(4,65,89,0.02)]">
                        <div className="text-[6.5px] font-bold uppercase tracking-wider text-[#044159] mb-0.5">Today</div>
                        <span className="text-[#4A5568]">{actor.before_state}</span>
                      </div>
                      <div className="flex items-center justify-center bg-[#F3F4F6] text-[#3FAF7A] font-bold text-[11px]">→</div>
                      <div className="p-1.5 bg-[rgba(63,175,122,0.02)]">
                        <div className="text-[6.5px] font-bold uppercase tracking-wider text-[#25785A] mb-0.5">Must Be True</div>
                        <span className="text-[#25785A]">{actor.after_state}</span>
                      </div>
                    </div>
                  )}
                  {actor.metric && (
                    <div className="text-[8px] text-[#718096] mt-1">Measurement: {actor.metric}</div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Connected entities */}
          {(outcome.connected_workflows.length > 0 || outcome.connected_constraints.length > 0) && (
            <div className="px-4 pb-3">
              <div className="text-[7px] font-bold uppercase tracking-[0.06em] text-[#A0AEC0] mb-1.5">
                Connected Entities
              </div>
              <div className="flex flex-wrap gap-1">
                {outcome.connected_workflows.map(w => (
                  <span key={w.entity_id} className="text-[8px] font-medium px-2 py-1 rounded bg-[rgba(4,65,89,0.05)] border border-[rgba(4,65,89,0.1)] text-[#044159]">
                    {w.entity_type}: {w.entity_id.slice(0, 8)}
                  </span>
                ))}
                {outcome.connected_constraints.map(c => (
                  <span key={c.entity_id} className="text-[8px] font-medium px-2 py-1 rounded bg-[rgba(196,154,26,0.06)] border border-[rgba(196,154,26,0.12)] text-[#C49A1A]">
                    constraint: {c.entity_id.slice(0, 8)}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Actor Card (expandable with happy path) ──

function ActorCard({ actor }: { actor: Actor }) {
  const [expanded, setExpanded] = useState(false)
  const color = getPersonaColor(actor.name)

  return (
    <div
      className={`bg-white rounded-2xl shadow-md border border-border overflow-hidden transition-all cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#044159] ${
        expanded ? 'ring-1 ring-[#044159]/30 col-span-2' : 'hover:border-[#D4D4D4]'
      }`}
      role="button"
      tabIndex={0}
      onClick={() => setExpanded(!expanded)}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setExpanded(!expanded) } }}
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 p-3.5">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0"
          style={{ background: color }}>
          {actor.name[0]}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-bold text-[#0A1E2F]">{actor.name}</div>
          <div className="text-[9px] text-[#718096]">{actor.role}</div>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {actor.outcomes.length > 0 && (
            <span className="text-[8px] font-semibold px-1.5 py-0.5 rounded bg-green-50 text-green-700">
              {actor.outcomes.length} outcome{actor.outcomes.length !== 1 ? 's' : ''}
            </span>
          )}
          {actor.journey.length > 0 && (
            <span className="text-[8px] font-medium text-[#A0AEC0]">
              {actor.journey.length} steps
            </span>
          )}
          {expanded ? <ChevronUp className="w-3 h-3 text-[#A0AEC0]" /> : <ChevronDown className="w-3 h-3 text-[#A0AEC0]" />}
        </div>
      </div>

      {/* Collapsed: outcome dots */}
      {!expanded && actor.outcomes.length > 0 && (
        <div className="px-3.5 pb-3 flex flex-col gap-1">
          {actor.outcomes.slice(0, 3).map(o => (
            <div key={o.outcome_id} className="flex items-center gap-1.5 text-[9px] text-[#4A5568] leading-snug">
              <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{ background: o.outcome_strength >= 90 ? '#3FAF7A' : o.outcome_strength >= 70 ? '#25785A' : '#C49A1A' }} />
              <span className="truncate">{o.outcome_title}</span>
            </div>
          ))}
          {actor.outcomes.length > 3 && (
            <span className="text-[8px] text-[#A0AEC0] ml-3">+{actor.outcomes.length - 3} more</span>
          )}
        </div>
      )}

      {/* Expanded: full happy path */}
      {expanded && (
        <div className="border-t border-[#F3F4F6]" onClick={(e) => e.stopPropagation()}>
          {/* Description + goals/pain points */}
          {(actor.description || actor.goals.length > 0 || actor.pain_points.length > 0) && (
            <div className="px-4 py-3">
              {actor.description && (
                <p className="text-[11px] text-[#4A5568] leading-relaxed mb-2">{actor.description}</p>
              )}
              {actor.goals.length > 0 && (
                <div className="mb-2">
                  <span className="text-[7px] font-bold uppercase tracking-wider text-[#25785A]">Goals</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {actor.goals.map((g, i) => (
                      <span key={i} className="text-[8px] font-medium px-2 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">{g}</span>
                    ))}
                  </div>
                </div>
              )}
              {actor.pain_points.length > 0 && (
                <div>
                  <span className="text-[7px] font-bold uppercase tracking-wider text-[#C49A1A]">Pain Points</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {actor.pain_points.map((p, i) => (
                      <span key={i} className="text-[8px] font-medium px-2 py-0.5 rounded bg-[#FEF3CD] text-[#92620E]">{p}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Outcome state changes (before → after) */}
          {actor.outcomes.length > 0 && (
            <div className="border-t border-[#F3F4F6] px-4 py-3">
              <div className="text-[7px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-2">
                State Changes ({actor.outcomes.length})
              </div>
              {actor.outcomes.map(o => (
                <div key={o.outcome_id} className="mb-2 last:mb-0 p-2.5 bg-[#F7FAFC] rounded-lg" style={{ borderLeft: `3px solid ${color}` }}>
                  <div className="flex items-center gap-1.5 mb-1">
                    <div className="w-1.5 h-1.5 rounded-full"
                      style={{ background: o.outcome_strength >= 90 ? '#3FAF7A' : o.outcome_strength >= 70 ? '#25785A' : '#C49A1A' }} />
                    <span className="text-[9px] font-semibold text-[#1D1D1F]">{o.outcome_title}</span>
                    <span className={`text-[7px] font-bold px-1.5 py-0.5 rounded ${
                      o.outcome_horizon === 'h1' ? 'bg-green-50 text-green-700' : 'bg-teal-50 text-teal-700'
                    }`}>{o.outcome_horizon.toUpperCase()}</span>
                  </div>
                  {o.actor_title && (
                    <div className="text-[9px] text-[#4A5568] mb-1">{o.actor_title}</div>
                  )}
                  <div className="flex items-center gap-1 text-[8px]">
                    <span className="font-semibold text-[#044159]">{o.actor_strength}</span>
                    <span className="text-[#A0AEC0]">strength</span>
                    <span className={`ml-1 px-1.5 py-0.5 rounded text-[7px] font-medium ${
                      o.actor_status === 'confirmed' || o.actor_status === 'validated'
                        ? 'bg-green-50 text-green-700'
                        : o.actor_status === 'emerging'
                        ? 'bg-[#FEF3CD] text-[#92620E]'
                        : 'bg-gray-100 text-gray-500'
                    }`}>{o.actor_status}</span>
                  </div>
                  {(o.before_state || o.after_state) && (
                    <div className="grid grid-cols-[1fr_20px_1fr] gap-0 mt-1.5 border border-[#E5E5E5] rounded overflow-hidden text-[9px]">
                      <div className="p-1.5 bg-[rgba(4,65,89,0.02)]">
                        <div className="text-[6.5px] font-bold uppercase tracking-wider text-[#044159] mb-0.5">Today</div>
                        <span className="text-[#4A5568]">{o.before_state}</span>
                      </div>
                      <div className="flex items-center justify-center bg-[#F3F4F6] text-[#3FAF7A] font-bold text-[11px]">→</div>
                      <div className="p-1.5 bg-[rgba(63,175,122,0.02)]">
                        <div className="text-[6.5px] font-bold uppercase tracking-wider text-[#25785A] mb-0.5">Must Be True</div>
                        <span className="text-[#25785A]">{o.after_state}</span>
                      </div>
                    </div>
                  )}
                  {o.metric && (
                    <div className="text-[8px] text-[#718096] mt-1">Measurement: {o.metric}</div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Journey steps (happy path) */}
          {actor.journey.length > 0 && (
            <div className="border-t border-[#F3F4F6] px-4 py-3">
              <div className="text-[7px] font-bold uppercase tracking-wider text-[#044159] mb-2">
                Happy Path ({actor.journey.length} steps)
              </div>
              <div className="relative">
                {/* Vertical connector line */}
                <div className="absolute left-[11px] top-2 bottom-2 w-px bg-[#E2E8F0]" />
                <div className="space-y-1">
                  {actor.journey.map((step, i) => (
                    <div key={step.step_id} className="flex items-start gap-2.5 relative">
                      <div className="w-[23px] h-[23px] rounded-full bg-white border-2 border-[#044159] flex items-center justify-center text-[8px] font-bold text-[#044159] flex-shrink-0 z-10">
                        {step.step_index}
                      </div>
                      <div className="flex-1 py-1">
                        <div className="text-[10px] font-medium text-[#1D1D1F]">{step.title}</div>
                        <span className="text-[8px] text-[#A0AEC0]">{step.phase}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
