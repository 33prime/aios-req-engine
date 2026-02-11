/**
 * PhaseSwitcher - Toggle between Overview/Discovery/Build/Live phases
 *
 * Non-destructive navigation - all phases remain accessible.
 * Visual indicator shows which phase is currently active.
 */

'use client'

import { LayoutDashboard, FileText, Rocket, Wrench } from 'lucide-react'

export type WorkspacePhase = 'overview' | 'discovery' | 'build' | 'live'

interface PhaseSwitcherProps {
  currentPhase: WorkspacePhase
  onPhaseChange: (phase: WorkspacePhase) => void
  disabled?: boolean
}

const PHASES = [
  {
    id: 'overview' as const,
    label: 'Overview',
    icon: LayoutDashboard,
    description: 'Project Dashboard',
  },
  {
    id: 'discovery' as const,
    label: 'Discovery',
    icon: FileText,
    description: 'Requirements Canvas',
  },
  {
    id: 'build' as const,
    label: 'Build',
    icon: Wrench,
    description: 'Prototype',
  },
  {
    id: 'live' as const,
    label: 'Live',
    icon: Rocket,
    description: 'Product',
  },
]

export function PhaseSwitcher({ currentPhase, onPhaseChange, disabled }: PhaseSwitcherProps) {
  return (
    <div className="inline-flex items-center bg-[#F4F4F4] rounded-xl p-1 border border-[#E5E5E5]">
      {PHASES.map((phase) => {
        const isActive = currentPhase === phase.id
        const Icon = phase.icon

        return (
          <button
            key={phase.id}
            onClick={() => onPhaseChange(phase.id)}
            disabled={disabled}
            className={`
              flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium
              transition-all duration-200
              ${isActive
                ? 'bg-white text-[#3FAF7A] shadow-sm'
                : 'text-[#666666] hover:text-[#333333]'
              }
              ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
            `}
            title={phase.description}
          >
            <Icon className="w-4 h-4" />
            <span>{phase.label}</span>
          </button>
        )
      })}
    </div>
  )
}

export default PhaseSwitcher
