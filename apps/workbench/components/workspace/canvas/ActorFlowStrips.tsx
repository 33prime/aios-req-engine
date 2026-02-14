'use client'

import { useMemo } from 'react'
import { ArrowRight } from 'lucide-react'
import type { WorkflowPair, WorkflowStepSummary, PersonaBRDSummary } from '@/types/workspace'

interface ActorFlowStripsProps {
  actors: (PersonaBRDSummary & { canvas_role: 'primary' | 'secondary' })[]
  workflowPairs: WorkflowPair[]
  /** When true, strips fade out (VP step is selected) */
  dimmed?: boolean
}

// Boilerplate patterns to exclude from flow strips
const BOILERPLATE_PATTERNS = [
  /sign\s*up/i,
  /sign\s*in/i,
  /log\s*in/i,
  /log\s*out/i,
  /register/i,
  /registration/i,
  /password\s*reset/i,
  /forgot\s*password/i,
  /onboarding/i,
  /welcome/i,
  /getting\s*started/i,
  /basic\s*navigation/i,
  /homepage/i,
]

function isBoilerplate(label: string): boolean {
  return BOILERPLATE_PATTERNS.some((p) => p.test(label))
}

export function ActorFlowStrips({ actors, workflowPairs, dimmed }: ActorFlowStripsProps) {
  // Build a map: actorId → future-state steps across all workflows
  const actorSteps = useMemo(() => {
    const map: Record<string, WorkflowStepSummary[]> = {}
    for (const actor of actors) {
      const steps: WorkflowStepSummary[] = []
      for (const pair of workflowPairs) {
        for (const step of pair.future_steps) {
          if (step.actor_persona_id === actor.id && !isBoilerplate(step.label)) {
            steps.push(step)
          }
        }
      }
      steps.sort((a, b) => a.step_index - b.step_index)
      map[actor.id] = steps
    }
    return map
  }, [actors, workflowPairs])

  // Don't render if no actors have flows
  const hasAnyFlows = actors.some((a) => (actorSteps[a.id] || []).length > 0)
  if (!hasAnyFlows) return null

  return (
    <div
      className={`transition-all duration-300 ${
        dimmed ? 'opacity-30 pointer-events-none h-0 overflow-hidden' : 'opacity-100'
      }`}
    >
      <div className="space-y-2">
        {actors.map((actor) => {
          const steps = actorSteps[actor.id] || []
          if (steps.length === 0) return null
          return (
            <ActorFlowRow
              key={actor.id}
              actorName={actor.name}
              isPrimary={actor.canvas_role === 'primary'}
              steps={steps}
            />
          )
        })}
      </div>
    </div>
  )
}

function ActorFlowRow({
  actorName,
  isPrimary,
  steps,
}: {
  actorName: string
  isPrimary: boolean
  steps: WorkflowStepSummary[]
}) {
  return (
    <div className="flex items-center gap-2">
      {/* Actor label */}
      <span className={`shrink-0 text-[11px] font-medium w-[100px] text-right truncate ${
        isPrimary ? 'text-[#25785A]' : 'text-[#666666]'
      }`}>
        {actorName}
      </span>

      {/* Flow pills */}
      <div className="flex items-center gap-1 overflow-x-auto scrollbar-hide py-1 flex-1">
        {steps.map((step, idx) => (
          <div key={step.id} className="flex items-center shrink-0">
            <span className={`px-2.5 py-1 text-[11px] font-medium rounded-lg whitespace-nowrap ${
              isPrimary
                ? 'bg-[#E8F5E9] text-[#25785A]'
                : 'bg-[#F0F0F0] text-[#666666]'
            }`}>
              {step.label}
            </span>
            {idx < steps.length - 1 && (
              <ArrowRight className="w-3 h-3 text-[#E5E5E5] shrink-0 mx-0.5" />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
