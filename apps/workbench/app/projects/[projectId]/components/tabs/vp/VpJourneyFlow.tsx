/**
 * VpJourneyFlow Component
 *
 * Horizontal scrolling flow of connected cards showing the golden path.
 * Each card shows: circular step number, title, checkmark status, value rating.
 * Cards are connected with arrow connectors to show flow direction.
 */

'use client'

import React from 'react'
import { ChevronRight } from 'lucide-react'
import type { VpStep } from '@/types/api'

interface VpJourneyFlowProps {
  steps: VpStep[]
  selectedId: string | null
  onSelect: (step: VpStep) => void
}

// Value rating display (stars)
function ValueStars({ step }: { step: VpStep }) {
  const hasHighValue = step.value_created && step.value_created.length > 100
  const hasEvidence = step.evidence && step.evidence.length > 0
  const hasFeatures = step.features_used && step.features_used.length >= 2

  let stars = 1
  if (hasHighValue) stars++
  if (hasEvidence) stars++
  if (hasFeatures && stars < 3) stars++

  return (
    <div className="text-yellow-500 text-xs">
      {[1, 2, 3].map((i) => (
        <span key={i} className={i <= stars ? '' : 'opacity-30'}>
          ★
        </span>
      ))}
    </div>
  )
}

// Individual step card
function StepCard({
  step,
  isSelected,
  onClick,
}: {
  step: VpStep
  isSelected: boolean
  onClick: () => void
}) {
  const status = step.confirmation_status || step.status
  const isConfirmed = status === 'confirmed_consultant' || status === 'confirmed_client'

  return (
    <button
      onClick={onClick}
      className={`
        flex-shrink-0 w-48 bg-white rounded-lg border-2 p-4 transition-all group
        ${isSelected
          ? 'border-[#009b87] bg-emerald-50 shadow-md'
          : 'border-gray-200 hover:border-[#009b87] hover:shadow-md'
        }
      `}
    >
      {/* Top row: step number + checkmark */}
      <div className="flex items-center justify-between mb-3">
        {/* Circular step number */}
        <div
          className={`
            h-8 w-8 rounded-full flex items-center justify-center text-sm font-semibold transition-colors
            ${isSelected
              ? 'bg-[#009b87] text-white'
              : 'bg-gray-100 text-gray-600 group-hover:bg-[#009b87] group-hover:text-white'
            }
          `}
        >
          {step.step_index}
        </div>

        {/* Checkmark if confirmed */}
        {isConfirmed && (
          <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        )}
      </div>

      {/* Title */}
      <h3 className="text-sm font-semibold text-gray-900 mb-1 line-clamp-2 text-left min-h-[2.5rem]">
        {step.label}
      </h3>

      {/* Value stars */}
      <div className="flex items-center justify-center gap-1 mt-2">
        <ValueStars step={step} />
      </div>
    </button>
  )
}

// Arrow connector between steps
function ArrowConnector() {
  return (
    <div className="flex-shrink-0 flex items-center justify-center w-8">
      <ChevronRight className="w-5 h-5 text-[#009b87]" />
    </div>
  )
}

export function VpJourneyFlow({ steps, selectedId, onSelect }: VpJourneyFlowProps) {
  const sortedSteps = [...steps].sort((a, b) => a.step_index - b.step_index)

  if (steps.length === 0) {
    return (
      <div className="bg-gray-50 rounded-xl border-2 border-dashed border-gray-200 p-8 text-center">
        <p className="text-gray-500">No steps in the Value Path yet.</p>
        <p className="text-sm text-gray-400 mt-1">Ask the AI assistant to generate the value path.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
      <h2 className="text-xl font-semibold text-gray-900 mb-6">Journey Flow</h2>

      {/* Horizontal scrolling container */}
      <div className="overflow-x-auto pb-2">
        <div className="flex items-center gap-0 min-w-max">
          {sortedSteps.map((step, index) => (
            <React.Fragment key={step.id}>
              <StepCard
                step={step}
                isSelected={step.id === selectedId}
                onClick={() => onSelect(step)}
              />
              {index < sortedSteps.length - 1 && <ArrowConnector />}
            </React.Fragment>
          ))}
        </div>
      </div>
    </div>
  )
}

export default VpJourneyFlow
