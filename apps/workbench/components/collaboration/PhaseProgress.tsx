/**
 * PhaseProgress Component
 *
 * Compact linear phase progress bar showing:
 * - All phases in order with current highlighted
 * - Steps within current phase
 * - Readiness score
 */

'use client'

import React from 'react'
import {
  Check,
  Lock,
  Circle,
  ChevronRight,
} from 'lucide-react'
import type {
  CollaborationPhase,
  PhaseProgressConfig,
  PhaseStep,
  PhaseGate,
} from '@/types/api'

interface PhaseProgressProps {
  currentPhase: CollaborationPhase
  phases: Array<{
    phase: CollaborationPhase
    status: 'locked' | 'active' | 'completed'
    completed_at?: string
  }>
  phaseConfig: PhaseProgressConfig
  readinessScore: number
  onViewGates?: () => void
}

const PHASE_LABELS: Record<CollaborationPhase, string> = {
  pre_discovery: 'Pre-Discovery',
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  proposal: 'Proposal',
  build: 'Build',
  delivery: 'Delivery',
}

export function PhaseProgress({
  currentPhase,
  phases,
  phaseConfig,
  readinessScore,
  onViewGates,
}: PhaseProgressProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      {/* Header row: Phase name + Readiness */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-sm font-semibold text-gray-900">
            {PHASE_LABELS[currentPhase] || currentPhase}
          </h3>
          <span className="px-2 py-0.5 text-xs font-medium bg-[#009b87]/10 text-[#009b87] rounded-full">
            Active
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Readiness:</span>
          <span className="text-sm font-semibold text-gray-900">{readinessScore}%</span>
          <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#009b87] rounded-full transition-all"
              style={{ width: `${readinessScore}%` }}
            />
          </div>
          {onViewGates && (
            <button
              onClick={onViewGates}
              className="text-xs text-[#009b87] hover:underline ml-2"
            >
              View Gates
            </button>
          )}
        </div>
      </div>

      {/* Phase timeline */}
      <div className="flex items-center gap-1 mb-4">
        {phases.map((phase, index) => (
          <React.Fragment key={phase.phase}>
            <PhaseNode
              phase={phase}
              isFirst={index === 0}
              isLast={index === phases.length - 1}
            />
            {index < phases.length - 1 && (
              <div
                className={`flex-1 h-0.5 ${
                  phase.status === 'completed' ? 'bg-[#009b87]' : 'bg-gray-200'
                }`}
              />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Steps within current phase */}
      <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
        {phaseConfig.steps.map((step, index) => (
          <React.Fragment key={step.id}>
            <StepNode step={step} />
            {index < phaseConfig.steps.length - 1 && (
              <ChevronRight className="w-4 h-4 text-gray-300 flex-shrink-0" />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}

interface PhaseNodeProps {
  phase: {
    phase: CollaborationPhase
    status: 'locked' | 'active' | 'completed'
  }
  isFirst: boolean
  isLast: boolean
}

function PhaseNode({ phase }: PhaseNodeProps) {
  const displayName = PHASE_LABELS[phase.phase] || phase.phase

  const statusStyles = {
    completed: 'bg-[#009b87] text-white',
    active: 'bg-[#009b87]/20 text-[#009b87] ring-2 ring-[#009b87]',
    locked: 'bg-gray-100 text-gray-400',
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <div
        className={`w-6 h-6 rounded-full flex items-center justify-center ${
          statusStyles[phase.status]
        }`}
        title={displayName}
      >
        {phase.status === 'completed' ? (
          <Check className="w-3.5 h-3.5" />
        ) : phase.status === 'locked' ? (
          <Lock className="w-3 h-3" />
        ) : (
          <Circle className="w-2 h-2 fill-current" />
        )}
      </div>
      <span className="text-[10px] text-gray-500 hidden sm:block">
        {displayName.split(' ')[0]}
      </span>
    </div>
  )
}

interface StepNodeProps {
  step: PhaseStep
}

function StepNode({ step }: StepNodeProps) {
  // Completed steps get solid teal dot with checkmark
  // In-progress gets teal ring with pulse
  // Available gets gray outline
  // Locked gets gray fill

  return (
    <div className="flex items-center gap-2 group relative">
      {/* Step indicator */}
      <div className="relative">
        {step.status === 'completed' ? (
          <div className="w-5 h-5 rounded-full bg-[#009b87] flex items-center justify-center">
            <Check className="w-3 h-3 text-white" />
          </div>
        ) : step.status === 'in_progress' ? (
          <div className="w-5 h-5 rounded-full bg-[#009b87]/20 border-2 border-[#009b87] flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-[#009b87] animate-pulse" />
          </div>
        ) : step.status === 'available' ? (
          <div className="w-5 h-5 rounded-full bg-white border-2 border-gray-300 flex items-center justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-gray-300" />
          </div>
        ) : (
          <div className="w-5 h-5 rounded-full bg-gray-100 flex items-center justify-center">
            <Lock className="w-2.5 h-2.5 text-gray-400" />
          </div>
        )}
      </div>

      {/* Step label and progress */}
      <div className="flex items-center gap-1.5">
        <span
          className={`text-xs font-medium ${
            step.status === 'completed'
              ? 'text-[#009b87]'
              : step.status === 'in_progress'
              ? 'text-gray-900'
              : step.status === 'available'
              ? 'text-gray-600'
              : 'text-gray-400'
          }`}
        >
          {step.label}
        </span>
        {step.progress && (
          <span className="text-xs text-gray-400">
            ({step.progress.current}/{step.progress.total})
          </span>
        )}
      </div>

      {/* Tooltip for unlock message */}
      {step.unlock_message && step.status === 'locked' && (
        <div className="absolute bottom-full left-0 mb-2 px-2 py-1 bg-gray-900 text-white text-xs rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
          {step.unlock_message}
        </div>
      )}
    </div>
  )
}

// Compact version for smaller spaces
export function PhaseProgressCompact({
  currentPhase,
  phases,
  readinessScore,
}: Pick<PhaseProgressProps, 'currentPhase' | 'phases' | 'readinessScore'>) {
  const currentIndex = phases.findIndex((p) => p.phase === currentPhase)

  return (
    <div className="flex items-center gap-3">
      {/* Phase dots */}
      <div className="flex items-center gap-1">
        {phases.map((phase, index) => (
          <div
            key={phase.phase}
            className={`w-2 h-2 rounded-full ${
              index < currentIndex
                ? 'bg-[#009b87]'
                : index === currentIndex
                ? 'bg-[#009b87] ring-2 ring-[#009b87]/30'
                : 'bg-gray-200'
            }`}
            title={PHASE_LABELS[phase.phase] || phase.phase}
          />
        ))}
      </div>

      {/* Current phase label */}
      <span className="text-sm font-medium text-gray-900">
        {PHASE_LABELS[currentPhase]}
      </span>

      {/* Readiness */}
      <div className="flex items-center gap-1">
        <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#009b87] rounded-full"
            style={{ width: `${readinessScore}%` }}
          />
        </div>
        <span className="text-xs text-gray-500">{readinessScore}%</span>
      </div>
    </div>
  )
}

export default PhaseProgress
