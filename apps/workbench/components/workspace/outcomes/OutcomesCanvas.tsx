'use client'

import React, { useState, useCallback } from 'react'
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
  name?: string | null
  category?: string | null
  priority?: string | null
  status?: string | null
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
  capabilities?: Array<{
    id: string
    name: string
    description: string
    quadrant: string
    badge: string
  }>
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
  journey: Array<{ step_id: string; title: string; step_index: number; phase: string; description?: string }>
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
  const [selectedEntity, setSelectedEntity] = useState<{
    type: 'actor' | 'feature' | 'workflow' | 'intelligence'
    id: string
    outcome: Outcome
  } | null>(null)

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

      {/* ── Outcomes with sidebar ── */}
      <div className="flex gap-4 items-start">
        <div className={`flex-1 min-w-0 transition-all duration-200`}>
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
                  selectedEntity={selectedEntity}
                  setSelectedEntity={setSelectedEntity}
                />
              ))}
            </div>
          )}
        </div>
        {selectedEntity && (
          <div className="w-[340px] flex-shrink-0 sticky top-6">
            <EntityInspector
              entity={selectedEntity}
              onClose={() => setSelectedEntity(null)}
              onNavigate={(type, id) => {
                const outcome = selectedEntity.outcome
                if (type === 'actor') {
                  const actor = outcome.actors.find(a => a.persona_name === id || a.persona_id === id)
                  if (actor) setSelectedEntity({ type: 'actor', id, outcome })
                } else if (type === 'feature') {
                  setSelectedEntity({ type: 'feature', id, outcome })
                } else if (type === 'workflow') {
                  setSelectedEntity({ type: 'workflow', id, outcome })
                } else if (type === 'intelligence') {
                  setSelectedEntity({ type: 'intelligence', id, outcome })
                }
              }}
              allWorkflows={workflows}
            />
          </div>
        )}
      </div>

      {/* ── Actors ── */}
      <SectionHeader icon={Users} title="Actors" count={actors.length} />
      <div className="grid grid-cols-2 gap-3 mb-8">
        {actors.map(actor => (
          <ActorCard key={actor.id} actor={actor} />
        ))}
      </div>

      {/* ── Workflows (BRD-style) ── */}
      {(() => {
        // Build workflow_pairs from raw workflows when backend doesn't provide them
        const pairs = (data.workflow_pairs?.length ?? 0) > 0
          ? data.workflow_pairs!
          : (data.workflows ?? [])
              .filter(wf => wf.steps.length > 0) // skip empty workflows
              .map(wf => ({
                id: wf.id,
                name: wf.name,
                description: wf.description,
                owner: null as string | null,
                confirmation_status: wf.confirmation_status,
                current_workflow_id: wf.id,
                future_workflow_id: null as string | null,
                current_steps: wf.steps,
                future_steps: [] as typeof wf.steps,
                roi: wf.roi ?? null,
                is_stale: false,
                stale_reason: null as string | null,
              }))
        if (pairs.length === 0) return null
        return (
          <div className="mt-6">
            <WorkflowsSection
              workflows={[]}
              workflowPairs={pairs as WorkflowPair[]}
              roiSummary={data.roi_summary}
              sectionTitle="Workflows"
              onConfirm={() => {}}
              onNeedsReview={() => {}}
              onConfirmAll={() => {}}
            />
          </div>
        )
      })()}
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
  outcome, isOpen, onToggle, onSendToChat, selectedEntity, setSelectedEntity,
}: {
  outcome: Outcome; isOpen: boolean; onToggle: () => void; onSendToChat?: (msg: string) => void
  selectedEntity: { type: string; id: string; outcome: Outcome } | null
  setSelectedEntity: (entity: { type: 'actor' | 'feature' | 'workflow' | 'intelligence'; id: string; outcome: Outcome } | null) => void
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
          {outcome.description && (
            <div className="text-[11px] text-[#4A5568] leading-snug mt-0.5">{outcome.description}</div>
          )}
          {/* Tags */}
          <div className="flex gap-1 flex-wrap mt-1.5">
            <span className={`text-[8px] font-semibold px-2 py-0.5 rounded ${
              outcome.horizon === 'h1' ? 'bg-green-50 text-green-700' : 'bg-teal-50 text-teal-700'
            }`}>
              {outcome.horizon.toUpperCase()}
            </span>
            {outcome.actors.map(a => (
              <span key={a.persona_name} className="text-[9px] font-medium px-2 py-0.5 rounded bg-[#F3F4F6] text-[#718096]">
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
          {/* Zone 1: Proof scenario */}
          <div className="px-4 pt-3 pb-2">
            <div className="text-[11px] font-semibold text-[#1D1D1F] mb-2">How we'll know this outcome has been achieved</div>
            <div className="border-l-[3px] border-[#3FAF7A] pl-4 py-2 bg-[#F7FAFC] rounded-r-lg italic text-[13px] text-[#1D1D1F] leading-relaxed">
              {outcome.proof_scenario || outcome.evidence?.[0]?.text || 'Proof scenario will be generated with more signals.'}
            </div>
          </div>

          {/* Zone 2: Actors */}
          <div className="px-4 pt-2 pb-2">
            <div className="text-[11px] font-semibold text-[#1D1D1F] mb-2">Who benefits the most when this outcome is achieved</div>
            <div className="grid grid-cols-2 gap-2">
              {outcome.actors.slice(0, 2).map(actor => (
                <div key={actor.persona_name}
                  className={`border rounded-lg p-3 bg-[#F7FAFC] border-l-[3px] cursor-pointer transition-all hover:border-[#3FAF7A] hover:shadow-sm ${
                    selectedEntity?.type === 'actor' && selectedEntity?.id === actor.persona_name ? 'border-[#3FAF7A] ring-2 ring-[#3FAF7A]/15' : 'border-[#E5E5E5]'
                  }`}
                  style={{ borderLeftColor: getPersonaColor(actor.persona_name) }}
                  onClick={(e) => { e.stopPropagation(); setSelectedEntity({ type: 'actor', id: actor.persona_name, outcome }) }}
                >
                  <div className="flex items-center gap-2 mb-1.5">
                    <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white" style={{ background: getPersonaColor(actor.persona_name) }}>
                      {actor.persona_name[0]}
                    </div>
                    <span className="text-[12px] font-bold text-[#1D1D1F]">{actor.persona_name}</span>
                  </div>
                  <div className="text-[11px] text-[#4A5568] leading-snug">
                    {actor.before_state?.substring(0, 35)}{actor.before_state && actor.before_state.length > 35 ? '...' : ''}<span className="text-[#3FAF7A] font-bold mx-1">{'\u2192'}</span>{actor.after_state?.substring(0, 35)}{actor.after_state && actor.after_state.length > 35 ? '...' : ''}
                  </div>
                  <div className="text-[10px] text-[#718096] mt-1.5 flex items-center gap-1">
                    <span className="w-1 h-1 rounded-full bg-[#3FAF7A]"></span>{actor.metric}
                  </div>
                </div>
              ))}
            </div>
            {outcome.actors.length > 2 && (
              <div className="text-[10px] font-semibold text-[#25785A] mt-2 cursor-pointer hover:underline">+{outcome.actors.length - 2} more actors</div>
            )}
          </div>

          {/* Zone 3: Capabilities (features) */}
          {outcome.connected_features && outcome.connected_features.length > 0 && (
            <div className="px-4 pt-2 pb-1">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-[#A0AEC0] mb-2">What capabilities enable this outcome</div>
              <div className="flex flex-wrap gap-1.5">
                {outcome.connected_features.filter(f => f.name).slice(0, 4).map(f => (
                  <span key={f.entity_id}
                    className={`text-[11px] font-medium px-3 py-1.5 rounded-lg cursor-pointer transition-all flex items-center gap-1.5 ${
                      selectedEntity?.type === 'feature' && selectedEntity?.id === f.entity_id
                        ? 'bg-[#3FAF7A]/15 text-[#25785A] border border-[#3FAF7A] ring-2 ring-[#3FAF7A]/10'
                        : 'bg-[rgba(63,175,122,0.06)] text-[#25785A] border border-[rgba(63,175,122,0.12)] hover:bg-[rgba(63,175,122,0.12)] hover:border-[#3FAF7A]'
                    }`}
                    onClick={(e) => { e.stopPropagation(); setSelectedEntity({ type: 'feature', id: f.entity_id, outcome }) }}
                  >{'\u2B21'} {f.name}</span>
                ))}
              </div>
              {outcome.connected_features.filter(f => f.name).length > 4 && (
                <div className="text-[10px] font-semibold text-[#25785A] mt-1.5">+{outcome.connected_features.filter(f => f.name).length - 4} more capabilities</div>
              )}
            </div>
          )}

          {/* Zone 4: Workflows */}
          {outcome.connected_workflows && outcome.connected_workflows.length > 0 && (
            <div className="px-4 pt-1 pb-1">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-[#A0AEC0] mb-2">Which user flows achieve this outcome</div>
              <div className="flex flex-wrap gap-1.5">
                {outcome.connected_workflows.filter(w => w.name).slice(0, 2).map(w => (
                  <span key={w.entity_id}
                    className={`text-[11px] font-medium px-3 py-1.5 rounded-lg cursor-pointer transition-all flex items-center gap-1.5 ${
                      selectedEntity?.type === 'workflow' && selectedEntity?.id === w.entity_id
                        ? 'bg-[#044159]/10 text-[#044159] border border-[#044159] ring-2 ring-[#044159]/10'
                        : 'bg-[rgba(4,65,89,0.04)] text-[#044159] border border-[rgba(4,65,89,0.1)] hover:bg-[rgba(4,65,89,0.1)] hover:border-[#044159]'
                    }`}
                    onClick={(e) => { e.stopPropagation(); setSelectedEntity({ type: 'workflow', id: w.entity_id, outcome }) }}
                  >{'\u27F3'} {w.name}</span>
                ))}
              </div>
              {outcome.connected_workflows.filter(w => w.name).length > 2 && (
                <div className="text-[10px] font-semibold text-[#044159] mt-1.5">+{outcome.connected_workflows.filter(w => w.name).length - 2} more flows</div>
              )}
            </div>
          )}

          {/* Zone 5: Intelligence capabilities */}
          {outcome.capabilities && outcome.capabilities.length > 0 && (
            <div className="px-4 pt-1 pb-2">
              <div className="text-[9px] font-semibold uppercase tracking-wider text-[#A0AEC0] mb-2">What intelligence powers this outcome</div>
              <div className="flex flex-wrap gap-1.5">
                {outcome.capabilities.slice(0, 4).map(cap => (
                  <span key={cap.id}
                    className={`text-[10px] font-medium px-2.5 py-1 rounded-md cursor-pointer transition-all flex items-center gap-1.5 ${
                      selectedEntity?.type === 'intelligence' && selectedEntity?.id === cap.id
                        ? 'bg-[#044159]/10 text-[#044159] border border-[#044159] ring-2 ring-[#044159]/10'
                        : 'bg-[rgba(4,65,89,0.04)] text-[#044159] border border-[rgba(4,65,89,0.06)] hover:bg-[rgba(4,65,89,0.08)] hover:border-[#044159]'
                    }`}
                    onClick={(e) => { e.stopPropagation(); setSelectedEntity({ type: 'intelligence', id: cap.id, outcome }) }}
                  >
                    <span className="w-1.5 h-1.5 rounded-full" style={{ background: cap.quadrant === 'knowledge' ? '#044159' : cap.quadrant === 'scoring' ? '#3FAF7A' : cap.quadrant === 'decision' ? '#25785A' : '#0A1E2F' }}></span>
                    {cap.name}
                  </span>
                ))}
              </div>
              {outcome.capabilities.length > 4 && (
                <div className="text-[10px] font-semibold text-[#044159] mt-1.5">+{outcome.capabilities.length - 4} more intelligence</div>
              )}
            </div>
          )}

          {/* Zone 6: Evidence */}
          {outcome.evidence && outcome.evidence.length > 0 && (
            <div className="px-4 pt-2 pb-3">
              <div className="text-[11px] font-semibold text-[#1D1D1F] mb-2">Requirements evidence</div>
              <div className="flex flex-col gap-1.5">
                {outcome.evidence.slice(0, 3).map((ev, i) => (
                  <div key={i} className="border-l-[3px] border-[#3FAF7A] pl-3 py-1.5 bg-[#F7FAFC] rounded-r-md">
                    <div className="text-[12px] italic text-[#4A5568] leading-snug">&ldquo;{ev.text}&rdquo;</div>
                    <div className="text-[10px] text-[#A0AEC0] mt-1">&mdash; {ev.source || 'Signal'}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Zone 7: Actions */}
          <div className="px-4 py-3 border-t border-[#F0F2F4] flex gap-2">
            <button className="text-[11px] font-semibold px-4 py-1.5 rounded-lg border border-[#E5E5E5] text-[#4A5568] hover:border-[#3FAF7A] hover:text-[#25785A] hover:bg-[rgba(63,175,122,0.03)] transition-all">
              Discuss in Chat
            </button>
            <button className="text-[11px] font-semibold px-4 py-1.5 rounded-lg border border-[#E5E5E5] text-[#4A5568] hover:border-[#3FAF7A] hover:text-[#25785A] hover:bg-[rgba(63,175,122,0.03)] transition-all">
              Sharpen
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Entity Inspector Sidebar ──

function EntityInspector({
  entity,
  onClose,
  onNavigate,
  allWorkflows,
}: {
  entity: { type: string; id: string; outcome: Outcome }
  onClose: () => void
  onNavigate: (type: string, id: string) => void
  allWorkflows: Workflow[]
}) {
  const { type, id, outcome } = entity

  // Find entity data based on type
  let icon = '', iconBg = '', title = '', typeName = '', content: React.ReactNode = null, footerLink = ''

  if (type === 'actor') {
    const actor = outcome.actors.find(a => a.persona_name === id || a.persona_id === id)
    if (!actor) return null
    icon = actor.persona_name[0]; iconBg = getPersonaColor(actor.persona_name)
    title = actor.persona_name; typeName = 'Actor'
    content = (
      <>
        <div className="mb-4">
          <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">Today</div>
          <div className="text-[12px] text-[#4A5568] leading-relaxed">{actor.before_state}</div>
        </div>
        <div className="mb-4">
          <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">Must Be True</div>
          <div className="text-[12px] text-[#25785A] font-medium leading-relaxed">{actor.after_state}</div>
        </div>
        <div className="mb-4">
          <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">Measurement</div>
          <div className="text-[12px] text-[#4A5568]">{actor.metric}</div>
        </div>
        {outcome.connected_features?.filter(f => f.name).length > 0 && (
          <div className="mb-4">
            <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">Capabilities</div>
            <div className="space-y-1">
              {outcome.connected_features.filter(f => f.name).slice(0, 3).map(f => (
                <div key={f.entity_id} className="text-[11px] text-[#4A5568] cursor-pointer hover:text-[#25785A] flex items-center gap-1.5 py-1 border-b border-[#F5F6F7] last:border-0"
                  onClick={() => onNavigate('feature', f.entity_id)}>
                  <span className="text-[#25785A]">{'\u2B21'}</span>{f.name}
                </div>
              ))}
            </div>
          </div>
        )}
      </>
    )
  }

  if (type === 'feature') {
    const feat = outcome.connected_features?.find(f => f.entity_id === id)
    if (!feat) return null
    icon = '\u2B21'; iconBg = '#3FAF7A'
    title = feat.name || 'Feature'; typeName = `Feature${feat.priority ? ' \u00B7 ' + feat.priority : ''}`
    content = (
      <>
        {feat.how_served && (
          <div className="mb-4">
            <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">How It Serves</div>
            <div className="text-[12px] text-[#4A5568] leading-relaxed">{feat.how_served}</div>
          </div>
        )}
        <div className="mb-4">
          <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">Outcomes</div>
          <div className="text-[11px] text-[#4A5568] flex items-center gap-1.5 py-1">
            <span className="text-[#3FAF7A]">{'\u25C9'}</span>{outcome.title.substring(0, 55)}{outcome.title.length > 55 ? '...' : ''}
          </div>
        </div>
        {outcome.evidence?.length > 0 && (
          <div className="mb-4">
            <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">Evidence</div>
            {outcome.evidence.slice(0, 2).map((ev, i) => (
              <div key={i} className="border-l-2 border-[#3FAF7A] pl-3 py-1.5 bg-[#F7FAFC] rounded-r-md mb-1.5">
                <div className="text-[10px] italic text-[#4A5568] leading-snug">&ldquo;{ev.text}&rdquo;</div>
                <div className="text-[9px] text-[#A0AEC0] mt-1">&mdash; {ev.source || 'Signal'}</div>
              </div>
            ))}
          </div>
        )}
        {feat.status && (
          <div className="mb-4">
            <span className="text-[10px] font-semibold text-[#25785A] bg-[rgba(63,175,122,0.08)] px-3 py-1 rounded-md">{'\u2713'} {feat.status}</span>
          </div>
        )}
      </>
    )
    footerLink = 'Open in BRD \u2192'
  }

  if (type === 'workflow') {
    const wf = outcome.connected_workflows?.find(w => w.entity_id === id)
    const wfData = allWorkflows.find(w => w.id === id)
    const name = wf?.name || wfData?.name || 'Workflow'
    icon = '\u27F3'; iconBg = '#044159'
    title = name; typeName = 'User Flow'
    content = (
      <>
        {wfData && (
          <>
            <div className="mb-4">
              <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">Actors</div>
              <div className="space-y-1">
                {outcome.actors.slice(0, 2).map(a => (
                  <div key={a.persona_name} className="text-[11px] text-[#4A5568] cursor-pointer hover:text-[#25785A] flex items-center gap-1.5 py-1 border-b border-[#F5F6F7] last:border-0"
                    onClick={() => onNavigate('actor', a.persona_name)}>
                    <div className="w-4 h-4 rounded-full flex items-center justify-center text-[7px] font-bold text-white" style={{ background: getPersonaColor(a.persona_name) }}>{a.persona_name[0]}</div>
                    {a.persona_name}
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </>
    )
    footerLink = 'Open in BRD \u2192'
  }

  if (type === 'intelligence') {
    const cap = outcome.capabilities?.find(c => c.id === id)
    if (!cap) return null
    const qColors: Record<string, string> = { knowledge: '#044159', scoring: '#3FAF7A', decision: '#25785A', ai: '#0A1E2F' }
    icon = '\u25C6'; iconBg = qColors[cap.quadrant] || '#044159'
    title = cap.name; typeName = `Intelligence \u00B7 ${cap.quadrant.charAt(0).toUpperCase() + cap.quadrant.slice(1)}`
    content = (
      <>
        {cap.description && (
          <div className="mb-4">
            <div className="text-[12px] text-[#4A5568] leading-relaxed">{cap.description}</div>
          </div>
        )}
        {outcome.connected_features?.filter(f => f.name).length > 0 && (
          <div className="mb-4">
            <div className="text-[9px] font-bold uppercase tracking-wider text-[#A0AEC0] mb-1.5">Powers Capabilities</div>
            <div className="space-y-1">
              {outcome.connected_features.filter(f => f.name).slice(0, 3).map(f => (
                <div key={f.entity_id} className="text-[11px] text-[#4A5568] cursor-pointer hover:text-[#25785A] flex items-center gap-1.5 py-1 border-b border-[#F5F6F7] last:border-0"
                  onClick={() => onNavigate('feature', f.entity_id)}>
                  <span className="text-[#25785A]">{'\u2B21'}</span>{f.name}
                </div>
              ))}
            </div>
          </div>
        )}
      </>
    )
    footerLink = 'Open in Data & AI \u2192'
  }

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 flex items-start gap-3 border-b border-[#F0F2F4]">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center text-white font-bold text-sm flex-shrink-0" style={{ background: iconBg }}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-bold text-[#1D1D1F] leading-snug">{title}</div>
          <div className="text-[9px] font-semibold uppercase tracking-wider text-[#A0AEC0] mt-0.5">{typeName}</div>
        </div>
        <button onClick={onClose} className="text-[#A0AEC0] hover:text-[#1D1D1F] text-sm p-1 rounded hover:bg-[#F3F4F6] transition-colors">{'\u2715'}</button>
      </div>
      {/* Body */}
      <div className="px-4 py-3 max-h-[480px] overflow-y-auto">
        {content}
      </div>
      {/* Footer */}
      {footerLink && (
        <div className="px-4 py-3 border-t border-[#F0F2F4]">
          <span className="text-[11px] font-semibold text-[#25785A] cursor-pointer hover:underline flex items-center gap-1 px-3 py-1.5 border border-[rgba(63,175,122,0.15)] rounded-md bg-[rgba(63,175,122,0.03)] hover:bg-[rgba(63,175,122,0.08)] transition-all inline-flex">
            {footerLink}
          </span>
        </div>
      )}
    </div>
  )
}

// ── Actor Card (expandable with happy path) ──

function ActorCard({ actor }: { actor: Actor }) {
  const [expanded, setExpanded] = useState(false)
  const [hpExpanded, setHpExpanded] = useState(false)
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

      {/* Expanded: full detail */}
      {expanded && (
        <div>
          {/* Description + goals/pain points */}
          {(actor.description || actor.goals.length > 0 || actor.pain_points.length > 0) && (
            <div className="border-t border-[#F3F4F6]" onClick={(e) => e.stopPropagation()}>
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
                    <span className="text-[7px] font-bold uppercase tracking-wider text-[#044159]">Pain Points</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {actor.pain_points.map((p, i) => (
                        <span key={i} className="text-[8px] font-medium px-2 py-0.5 rounded bg-[#E8EEF2] text-[#0A1E2F]">{p}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Outcomes */}
          {actor.outcomes.length > 0 && (
            <div className="border-t border-[#F3F4F6]" onClick={(e) => e.stopPropagation()}>
              <div className="px-4 py-3">
                <div className="text-[11px] font-semibold text-[#1D1D1F] mb-2 flex items-center gap-2">
                  Outcomes <span className="text-[#A0AEC0] font-normal">{actor.outcomes.length}</span>
                  <div className="flex-1 h-px bg-[#ECEEF1]" />
                </div>
                <div className="space-y-0.5">
                  {actor.outcomes.map(o => (
                    <div key={o.outcome_id} className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg hover:bg-[#F7FAFC] cursor-pointer transition-colors">
                      <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: o.outcome_strength >= 90 ? '#3FAF7A' : o.outcome_strength >= 70 ? '#25785A' : '#044159' }} />
                      <span className="text-[11px] text-[#1D1D1F] font-medium flex-1 truncate">{o.outcome_title}</span>
                      <span className="text-[8px] font-semibold px-1.5 py-0.5 rounded bg-[rgba(63,175,122,0.1)] text-[#25785A] flex-shrink-0">{o.outcome_horizon.toUpperCase()}</span>
                      <span className="text-[10px] font-bold flex-shrink-0 min-w-[20px] text-right" style={{ color: o.outcome_strength >= 90 ? '#3FAF7A' : o.outcome_strength >= 70 ? '#25785A' : '#044159' }}>{o.outcome_strength}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Happy Path */}
          {actor.journey.length > 0 && (
            <div className="border-t border-[#F3F4F6]" onClick={(e) => e.stopPropagation()}>
              <div className="px-4 py-3">
                <div className="text-[11px] font-semibold text-[#1D1D1F] mb-2 flex items-center gap-2">
                  Happy Path <span className="text-[#A0AEC0] font-normal">{actor.journey.length} steps</span>
                  <div className="flex-1 h-px bg-[#ECEEF1]" />
                </div>
                <div>
                  {(hpExpanded ? actor.journey : actor.journey.slice(0, 4)).map((step, i) => (
                    <div key={step.step_id} className="grid grid-cols-2 gap-0 border-b border-[#F5F6F7] last:border-0 py-2.5">
                      <div className="flex items-start gap-2.5 pr-4">
                        <span className={`w-[22px] h-[22px] rounded-full border-[1.5px] flex items-center justify-center text-[9px] font-bold flex-shrink-0 ${
                          i === 0 || step.step_index === actor.journey[actor.journey.length - 1].step_index
                            ? 'bg-[#3FAF7A] text-white border-[#3FAF7A]'
                            : 'border-[#D4D8DC] text-[#718096]'
                        }`}>{step.step_index}</span>
                        <div>
                          <div className="text-[11px] font-medium text-[#1D1D1F]">{step.title}</div>
                          <div className="text-[9px] text-[#A0AEC0] mt-0.5">{step.phase}</div>
                        </div>
                      </div>
                      <div className="text-[11px] text-[#718096] leading-snug border-l border-[#ECEEF1] pl-4 pt-0.5">
                        {step.description || ''}
                      </div>
                    </div>
                  ))}
                  {actor.journey.length > 4 && (
                    <div
                      className="text-[10px] font-semibold text-[#25785A] mt-2 pl-8 cursor-pointer hover:underline"
                      onClick={() => setHpExpanded(!hpExpanded)}
                    >
                      {hpExpanded ? 'Show fewer' : `+${actor.journey.length - 4} more steps`}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
