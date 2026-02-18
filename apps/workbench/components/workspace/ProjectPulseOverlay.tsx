'use client'

import { useState } from 'react'
import { Activity, ArrowRight, X } from 'lucide-react'
import type { ProjectPulse } from '@/types/api'

interface ProjectPulseOverlayProps {
  pulse: ProjectPulse
  projectId: string
  onDismiss: () => void
}

const ENTITY_LABELS: Record<string, string> = {
  personas: 'Personas',
  workflows: 'Workflows',
  features: 'Requirements',
  drivers: 'Drivers',
  stakeholders: 'Stakeholders',
  vp_steps: 'VP Steps',
}

function ScoreCircle({ score }: { score: number }) {
  const radius = 42
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (score / 100) * circumference
  const color = score >= 60 ? '#3FAF7A' : '#F59E0B'

  return (
    <div className="relative w-28 h-28">
      <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r={radius} fill="none" stroke="#E5E5E5" strokeWidth="6" />
        <circle
          cx="50"
          cy="50"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold text-[#333333]">{score}</span>
        <span className="text-xs text-[#999999]">/100</span>
      </div>
    </div>
  )
}

export function ProjectPulseOverlay({
  pulse,
  projectId,
  onDismiss,
}: ProjectPulseOverlayProps) {
  const [showOnOpen, setShowOnOpen] = useState(() => {
    if (typeof window === 'undefined') return true
    const stored = localStorage.getItem(`pulse-show-on-open-${projectId}`)
    return stored !== 'false'
  })

  const handleToggle = () => {
    const next = !showOnOpen
    setShowOnOpen(next)
    localStorage.setItem(`pulse-show-on-open-${projectId}`, String(next))
  }

  // Filter to non-zero entity counts
  const entityEntries = Object.entries(pulse.entity_counts)
    .filter(([, v]) => v > 0)
    .slice(0, 6)

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center">
      {/* Blurred background */}
      <div className="absolute inset-0 bg-white/60 backdrop-blur-sm" />

      {/* Content card */}
      <div className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto bg-white rounded-2xl shadow-2xl border border-[#E5E5E5] p-8">
        <button
          onClick={onDismiss}
          className="absolute top-4 right-4 text-[#999999] hover:text-[#333333]"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="flex items-center gap-2 mb-6">
          <Activity className="w-5 h-5 text-[#3FAF7A]" />
          <h2 className="text-lg font-semibold text-[#333333]">Project Pulse</h2>
        </div>

        {/* Score */}
        <div className="flex justify-center mb-5">
          <ScoreCircle score={pulse.score} />
        </div>

        {/* Summary */}
        <p className="text-sm text-[#666666] text-center mb-6">{pulse.summary}</p>

        {/* Background + Vision */}
        {pulse.background && (
          <div className="mb-4">
            <h4 className="text-xs font-semibold text-[#999999] uppercase tracking-wide mb-1">Background</h4>
            <p className="text-sm text-[#333333] leading-relaxed">{pulse.background}</p>
          </div>
        )}
        {pulse.vision && (
          <div className="mb-5">
            <h4 className="text-xs font-semibold text-[#999999] uppercase tracking-wide mb-1">Vision</h4>
            <p className="text-sm text-[#333333] leading-relaxed">{pulse.vision}</p>
          </div>
        )}

        {/* Entity counts */}
        {entityEntries.length > 0 && (
          <div className="mb-5">
            <h4 className="text-xs font-semibold text-[#999999] uppercase tracking-wide mb-3">What We Found</h4>
            <div className="flex flex-wrap gap-2">
              {entityEntries.map(([key, count]) => (
                <div
                  key={key}
                  className="bg-[#F4F4F4] rounded-xl px-4 py-3 text-center min-w-[70px]"
                >
                  <p className="text-lg font-bold text-[#333333]">{count}</p>
                  <p className="text-[10px] text-[#999999] uppercase">{ENTITY_LABELS[key] || key}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Next actions */}
        {pulse.next_actions.length > 0 && (
          <div className="mb-5">
            <h4 className="text-xs font-semibold text-[#999999] uppercase tracking-wide mb-3">Next Steps</h4>
            <div className="space-y-2">
              {pulse.next_actions.map((action, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 bg-[#F4F4F4] rounded-xl px-4 py-3"
                >
                  <span className="text-xs font-bold text-[#3FAF7A] mt-0.5">{i + 1}.</span>
                  <div>
                    <p className="text-sm font-medium text-[#333333]">{action.title}</p>
                    <p className="text-xs text-[#999999] mt-0.5">{action.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Show on open toggle */}
        <label className="flex items-center gap-2 text-xs text-[#999999] mb-5 cursor-pointer">
          <input
            type="checkbox"
            checked={showOnOpen}
            onChange={handleToggle}
            className="rounded border-[#E5E5E5] text-[#3FAF7A] focus:ring-[#3FAF7A]/20"
          />
          Show this when I open the project
        </label>

        {/* Dismiss button */}
        <button
          onClick={onDismiss}
          className="w-full flex items-center justify-center gap-2 bg-[#3FAF7A] text-white font-medium py-3 rounded-xl hover:bg-[#25785A] transition-colors"
        >
          Let&apos;s Get Started <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
