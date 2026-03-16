'use client'

import { useEffect, useState } from 'react'
import type { SolutionFlowStepSummary, FlowHorizon } from '@/types/workspace'
import { apiRequest } from '@/lib/api/core'

interface FlowHorizonsPanelProps {
  projectId: string
  isOpen: boolean
  steps: SolutionFlowStepSummary[]
  onStepClick: (stepId: string) => void
}

interface HorizonData {
  id: string
  horizon_number: number
  title: string
  description: string
  vision: string
}

export function FlowHorizonsPanel({ projectId, isOpen, steps, onStepClick }: FlowHorizonsPanelProps) {
  const [horizons, setHorizons] = useState<HorizonData[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!isOpen || horizons.length > 0) return
    setLoading(true)
    apiRequest<HorizonData[]>(`/projects/${projectId}/workspace/horizons`)
      .then(data => setHorizons(data || []))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [isOpen, projectId, horizons.length])

  if (!isOpen) return null

  // Map steps to horizons (H1 = entry+core, H2 = output, H3 = admin)
  const horizonSteps: Record<number, SolutionFlowStepSummary[]> = { 1: [], 2: [], 3: [] }
  steps.forEach(s => {
    if (s.phase === 'entry' || s.phase === 'core_experience') horizonSteps[1].push(s)
    else if (s.phase === 'output') horizonSteps[2].push(s)
    else horizonSteps[3].push(s)
  })

  const horizonColors: Record<number, { bg: string; border: string; label: string }> = {
    1: { bg: 'rgba(63,175,122,0.06)', border: 'rgba(63,175,122,0.2)', label: 'H1 — Now' },
    2: { bg: 'rgba(4,65,89,0.04)', border: 'rgba(4,65,89,0.15)', label: 'H2 — Next' },
    3: { bg: 'rgba(10,30,47,0.03)', border: 'rgba(10,30,47,0.1)', label: 'H3 — Future' },
  }

  return (
    <div
      className="flex-shrink-0 overflow-hidden transition-all duration-300"
      style={{
        maxHeight: isOpen ? 240 : 0,
        borderBottom: isOpen ? '1px solid #E5E5E5' : 'none',
        background: '#FAFAFA',
      }}
    >
      <div className="px-8 py-5">
        <div className="flex gap-4">
          {[1, 2, 3].map(h => {
            const horizon = horizons.find(hz => hz.horizon_number === h)
            const hSteps = horizonSteps[h] || []
            const colors = horizonColors[h]

            return (
              <div
                key={h}
                className="flex-1 rounded-xl p-4"
                style={{ background: colors.bg, border: `1px solid ${colors.border}` }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <span
                    className="text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded"
                    style={{
                      background: h === 1 ? 'rgba(63,175,122,0.12)' : h === 2 ? 'rgba(4,65,89,0.08)' : 'rgba(10,30,47,0.06)',
                      color: h === 1 ? '#2A8F5F' : h === 2 ? '#044159' : '#0A1E2F',
                    }}
                  >
                    {colors.label}
                  </span>
                  <span className="text-[10px] font-medium" style={{ color: '#999' }}>
                    {hSteps.length} step{hSteps.length !== 1 ? 's' : ''}
                  </span>
                </div>

                <div className="text-[13px] font-semibold mb-1" style={{ color: '#1D1D1F' }}>
                  {horizon?.title || (h === 1 ? 'Core Capabilities' : h === 2 ? 'Enhanced Features' : 'Future Vision')}
                </div>

                {horizon?.description && (
                  <p className="text-[11px] leading-relaxed mb-2.5" style={{ color: '#7B7B7B' }}>
                    {horizon.description.slice(0, 120)}{horizon.description.length > 120 ? '...' : ''}
                  </p>
                )}

                {/* Step pills */}
                <div className="flex flex-wrap gap-1">
                  {hSteps.slice(0, 5).map(s => (
                    <button
                      key={s.id}
                      onClick={() => onStepClick(s.id)}
                      className="text-[10px] font-medium px-2 py-0.5 rounded transition-colors cursor-pointer"
                      style={{
                        background: 'rgba(255,255,255,0.7)',
                        color: '#4B4B4B',
                        border: '1px solid rgba(0,0,0,0.06)',
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.borderColor = '#3FAF7A'
                        e.currentTarget.style.color = '#2A8F5F'
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.borderColor = 'rgba(0,0,0,0.06)'
                        e.currentTarget.style.color = '#4B4B4B'
                      }}
                    >
                      {s.title}
                    </button>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
