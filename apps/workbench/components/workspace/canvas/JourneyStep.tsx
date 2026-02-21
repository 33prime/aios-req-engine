/**
 * JourneyStep - Single step in the value path journey
 *
 * Drop target for features. Shows step title, actor persona, and features.
 */

'use client'

import { useDroppable } from '@dnd-kit/core'
import { ArrowRight, CheckCircle, AlertCircle, User } from 'lucide-react'
import { FeatureChip } from './FeatureChip'
import type { VpStepSummary } from '@/types/workspace'

interface JourneyStepProps {
  step: VpStepSummary
  isLast: boolean
  isSaving: boolean
  onStepClick?: (stepId: string) => void
}

export function JourneyStep({ step, isLast, isSaving, onStepClick }: JourneyStepProps) {
  const { isOver, setNodeRef } = useDroppable({
    id: `step-${step.id}`,
  })

  const getStatusIndicator = (status?: string | null) => {
    switch (status) {
      case 'confirmed_client':
        return { icon: CheckCircle, color: 'text-green-500' }
      case 'confirmed_consultant':
        return { icon: CheckCircle, color: 'text-blue-500' }
      case 'needs_client':
      case 'needs_confirmation':
        return { icon: AlertCircle, color: 'text-amber-500' }
      default:
        return null
    }
  }

  const status = getStatusIndicator(step.confirmation_status)
  const StatusIcon = status?.icon

  return (
    <div className="flex items-start gap-4">
      {/* Step Card */}
      <div
        ref={setNodeRef}
        className={`
          flex-1 min-w-[280px] max-w-[320px] bg-white rounded-card border-2 shadow-card
          transition-all duration-200
          ${isOver
            ? 'border-brand-teal bg-emerald-50/50 shadow-card-hover'
            : 'border-ui-cardBorder hover:border-gray-300'
          }
          ${isSaving ? 'opacity-70' : ''}
        `}
      >
        {/* Header */}
        <div
          className="px-4 py-3 border-b border-gray-100 cursor-pointer hover:bg-ui-background/50 transition-colors"
          onClick={() => onStepClick?.(step.id)}
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="flex items-center justify-center w-6 h-6 rounded-full bg-brand-teal text-white text-xs font-bold">
                {step.step_index + 1}
              </span>
              <h3 className="font-semibold text-ui-headingDark text-sm">{step.title}</h3>
              {(() => {
                if (step.confirmation_status && step.confirmation_status !== 'ai_generated') return null
                if (!step.created_at) return null
                const age = Date.now() - new Date(step.created_at).getTime()
                if (age >= 24 * 60 * 60 * 1000) return null
                const isNew = step.version === 1 || step.version == null
                return (
                  <span className={`px-1 py-px text-[9px] font-bold text-white rounded leading-tight ${isNew ? 'bg-emerald-500' : 'bg-indigo-500'}`}>
                    {isNew ? 'NEW' : 'UPDATED'}
                  </span>
                )
              })()}
            </div>
            {StatusIcon && (
              <StatusIcon className={`w-4 h-4 ${status.color} flex-shrink-0 mt-0.5`} />
            )}
          </div>

          {/* Actor persona */}
          {step.actor_persona_name && (
            <div className="flex items-center gap-1 mt-1.5">
              <User className="w-3 h-3 text-ui-supportText" />
              <span className="text-support text-ui-supportText">{step.actor_persona_name}</span>
            </div>
          )}

          {/* Description */}
          {step.description && (
            <p className="text-support text-ui-supportText mt-2 line-clamp-2">
              {step.description}
            </p>
          )}
        </div>

        {/* Features */}
        <div className="p-3 min-h-[80px]">
          {step.features.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {step.features.map((feature) => (
                <FeatureChip key={feature.id} feature={feature} />
              ))}
            </div>
          ) : (
            <div className={`
              h-full min-h-[60px] rounded-lg border-2 border-dashed
              flex items-center justify-center text-center
              ${isOver ? 'border-brand-teal bg-emerald-50' : 'border-ui-cardBorder'}
            `}>
              <span className="text-support text-ui-supportText">
                Drop features here
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Connector Arrow */}
      {!isLast && (
        <div className="flex items-center h-[120px]">
          <ArrowRight className="w-6 h-6 text-gray-300" />
        </div>
      )}
    </div>
  )
}

export default JourneyStep
