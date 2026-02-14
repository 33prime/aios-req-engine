'use client'

import { useMemo } from 'react'
import { Users, Zap, AlertTriangle, ArrowRight } from 'lucide-react'
import type { PersonaBRDSummary, WorkflowPair, WorkflowStepSummary } from '@/types/workspace'

// Boilerplate patterns to exclude from journey strips
const BOILERPLATE = [
  /sign\s*up/i, /sign\s*in/i, /log\s*in/i, /log\s*out/i,
  /register/i, /registration/i, /password\s*reset/i, /forgot\s*password/i,
  /onboarding/i, /welcome/i, /getting\s*started/i, /basic\s*navigation/i, /homepage/i,
]

interface CanvasActorsRowProps {
  actors: (PersonaBRDSummary & { canvas_role: 'primary' | 'secondary' })[]
  workflowPairs: WorkflowPair[]
  onSynthesize: () => void
  isSynthesizing: boolean
  synthesisStale: boolean
  hasValuePath: boolean
  onActorClick?: (actor: PersonaBRDSummary) => void
}

export function CanvasActorsRow({
  actors,
  workflowPairs,
  onSynthesize,
  isSynthesizing,
  synthesisStale,
  hasValuePath,
  onActorClick,
}: CanvasActorsRowProps) {
  const primaryActors = actors.filter((a) => a.canvas_role === 'primary')
  const secondaryActors = actors.filter((a) => a.canvas_role === 'secondary')

  // Build actor → future steps map
  const actorSteps = useMemo(() => {
    const map: Record<string, WorkflowStepSummary[]> = {}
    for (const actor of actors) {
      const steps: WorkflowStepSummary[] = []
      for (const pair of workflowPairs) {
        for (const step of pair.future_steps) {
          if (step.actor_persona_id === actor.id && !BOILERPLATE.some((p) => p.test(step.label))) {
            steps.push(step)
          }
        }
      }
      steps.sort((a, b) => a.step_index - b.step_index)
      map[actor.id] = steps
    }
    return map
  }, [actors, workflowPairs])

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-[#3FAF7A]" />
          <h2 className="text-[16px] font-semibold text-[#333333]">Canvas Actors</h2>
          <span className="text-[12px] text-[#999999]">({actors.length})</span>
        </div>

        <div className="flex items-center gap-2">
          {synthesisStale && hasValuePath && (
            <span className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-amber-700 bg-amber-50 rounded-lg">
              <AlertTriangle className="w-3 h-3" />
              Path outdated
            </span>
          )}
          <button
            onClick={onSynthesize}
            disabled={isSynthesizing || actors.length === 0}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-[12px] font-semibold text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSynthesizing ? (
              <>
                <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white" />
                Synthesizing...
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5" />
                {hasValuePath ? 'Regenerate Path' : 'Synthesize Value Path'}
              </>
            )}
          </button>
        </div>
      </div>

      <div className="flex gap-4 flex-wrap">
        {primaryActors.map((actor) => (
          <ActorCard
            key={actor.id}
            actor={actor}
            isPrimary
            journeySteps={actorSteps[actor.id] || []}
            onClick={onActorClick ? () => onActorClick(actor) : undefined}
          />
        ))}
        {secondaryActors.map((actor) => (
          <ActorCard
            key={actor.id}
            actor={actor}
            isPrimary={false}
            journeySteps={actorSteps[actor.id] || []}
            onClick={onActorClick ? () => onActorClick(actor) : undefined}
          />
        ))}
      </div>
    </section>
  )
}

function ActorCard({
  actor,
  isPrimary,
  journeySteps,
  onClick,
}: {
  actor: PersonaBRDSummary
  isPrimary: boolean
  journeySteps: WorkflowStepSummary[]
  onClick?: () => void
}) {
  const goals = actor.goals || []
  const painPoints = actor.pain_points || []

  return (
    <div
      className={`flex-1 min-w-[260px] max-w-[400px] text-left bg-white rounded-2xl shadow-md border transition-all ${
        isPrimary ? 'border-l-4 border-l-[#3FAF7A]' : 'border-l-4 border-l-[#0A1E2F]'
      } border-[#E5E5E5] ${onClick ? 'cursor-pointer hover:shadow-lg hover:border-[#3FAF7A]/40' : ''}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onClick() } : undefined}
    >
      {/* Top section: identity + pain/goal */}
      <div className="px-5 py-4">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-8 h-8 rounded-full bg-[#F4F4F4] flex items-center justify-center shrink-0">
            <Users className="w-4 h-4 text-[#666666]" />
          </div>
          <div className="min-w-0">
            <p className="text-[14px] font-semibold text-[#333333] truncate">{actor.name}</p>
            {actor.role && (
              <p className="text-[11px] text-[#999999] truncate">{actor.role}</p>
            )}
          </div>
          <span className={`ml-auto shrink-0 px-2 py-0.5 text-[10px] font-medium rounded-full ${
            isPrimary
              ? 'bg-[#E8F5E9] text-[#25785A]'
              : 'bg-[#F0F0F0] text-[#666666]'
          }`}>
            {isPrimary ? 'Primary' : 'Secondary'}
          </span>
        </div>

        {painPoints.length > 0 && (
          <p className="text-[11px] text-[#999999] mt-2 line-clamp-1 italic">
            Pain: {painPoints[0]}
          </p>
        )}
        {goals.length > 0 && (
          <p className="text-[11px] text-[#25785A] mt-1 line-clamp-1 italic">
            Goal: {goals[0]}
          </p>
        )}
      </div>

      {/* Bottom section: inline journey */}
      {journeySteps.length > 0 && (
        <div className="border-t border-[#E5E5E5] px-4 py-2.5 bg-[#FAFAFA] rounded-b-2xl">
          <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide">
            {journeySteps.slice(0, 6).map((step, idx) => (
              <div key={step.id} className="flex items-center shrink-0">
                <span className={`px-2 py-0.5 text-[10px] font-medium rounded whitespace-nowrap ${
                  isPrimary
                    ? 'bg-[#E8F5E9] text-[#25785A]'
                    : 'bg-[#F0F0F0] text-[#666666]'
                }`}>
                  {step.label}
                </span>
                {idx < Math.min(journeySteps.length, 6) - 1 && (
                  <ArrowRight className="w-2.5 h-2.5 text-[#E5E5E5] shrink-0 mx-0.5" />
                )}
              </div>
            ))}
            {journeySteps.length > 6 && (
              <span className="text-[10px] text-[#999999] ml-1">+{journeySteps.length - 6}</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
