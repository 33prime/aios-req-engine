'use client'

import { Plus } from 'lucide-react'
import type { SolutionFlowStepSummary } from '@/types/workspace'

const PHASE_ORDER = ['entry', 'core_experience', 'output', 'admin'] as const
const PHASE_LABELS: Record<string, string> = {
  entry: 'Entry',
  core_experience: 'Core Experience',
  output: 'Output',
  admin: 'Admin',
}

const CONFIDENCE_DOT: Record<string, string> = {
  known: 'bg-[#3FAF7A]',
  inferred: 'bg-[#0A1E2F]/40',
  guess: 'bg-[#BBBBBB]',
  unknown: 'bg-[#E5E5E5]',
}

const STATUS_BORDER: Record<string, string> = {
  confirmed_client: 'border-l-[#3FAF7A]',
  confirmed_consultant: 'border-l-[#0A1E2F]',
  needs_client: 'border-l-[#C4A97D]',
  ai_generated: 'border-l-[#E5E5E5]',
}

interface FlowStepListProps {
  steps: SolutionFlowStepSummary[]
  selectedStepId: string | null
  onSelectStep: (stepId: string) => void
  onAddStep?: (phase: string) => void
}

export function FlowStepList({ steps, selectedStepId, onSelectStep, onAddStep }: FlowStepListProps) {
  // Group steps by phase
  const byPhase: Record<string, SolutionFlowStepSummary[]> = {}
  for (const step of steps) {
    if (!byPhase[step.phase]) byPhase[step.phase] = []
    byPhase[step.phase].push(step)
  }

  return (
    <div className="h-full overflow-y-auto py-2">
      {PHASE_ORDER.map(phase => {
        const phaseSteps = byPhase[phase]
        if (!phaseSteps?.length && !onAddStep) return null
        return (
          <div key={phase} className="mb-3">
            {/* Phase header */}
            <div className="flex items-center justify-between px-4 py-2">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-[#999999]">
                {PHASE_LABELS[phase] || phase}
                {phaseSteps?.length ? ` (${phaseSteps.length})` : ''}
              </span>
            </div>

            {/* Steps */}
            {phaseSteps?.map(step => {
              const isSelected = step.id === selectedStepId
              const statusBorder = STATUS_BORDER[step.confirmation_status || 'ai_generated'] || STATUS_BORDER.ai_generated

              return (
                <button
                  key={step.id}
                  onClick={() => onSelectStep(step.id)}
                  className={`w-full text-left px-4 py-2.5 border-l-[3px] transition-colors ${statusBorder} ${
                    isSelected
                      ? 'bg-[#0A1E2F]/5 !border-l-[#0A1E2F]'
                      : 'hover:bg-[#F4F4F4]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      {/* Title — wraps instead of truncating */}
                      <div className={`text-[13px] font-medium leading-snug ${
                        isSelected ? 'text-[#0A1E2F]' : 'text-[#333333]'
                      }`}>
                        {step.title}
                      </div>
                      {step.actors.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {step.actors.slice(0, 2).map(actor => (
                            <span
                              key={actor}
                              className="text-[10px] px-1.5 py-0.5 rounded-full bg-[#F4F4F4] text-[#999999]"
                            >
                              {actor}
                            </span>
                          ))}
                          {step.actors.length > 2 && (
                            <span className="text-[10px] text-[#999999]">
                              +{step.actors.length - 2}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Confidence dots */}
                    {step.info_field_count > 0 && (
                      <div className="flex flex-wrap gap-0.5 mt-1 shrink-0 max-w-[40px] justify-end">
                        {Object.entries(step.confidence_breakdown || {}).map(([conf, count]) => (
                          Array.from({ length: Math.min(count, 4) }).map((_, i) => (
                            <div
                              key={`${conf}-${i}`}
                              className={`w-1.5 h-1.5 rounded-full ${CONFIDENCE_DOT[conf] || CONFIDENCE_DOT.unknown}`}
                            />
                          ))
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Open questions indicator */}
                  {step.open_question_count > 0 && (
                    <div className="mt-1 text-[10px] text-[#A08050]">
                      {step.open_question_count} question{step.open_question_count !== 1 ? 's' : ''}
                    </div>
                  )}
                </button>
              )
            })}

            {/* Add step button */}
            {onAddStep && (
              <button
                onClick={() => onAddStep(phase)}
                className="w-full flex items-center gap-1.5 px-4 py-2 text-xs text-[#999999] hover:text-[#3FAF7A] hover:bg-[#F4F4F4] transition-colors"
              >
                <Plus className="w-3 h-3" />
                Add step
              </button>
            )}
          </div>
        )
      })}
    </div>
  )
}
