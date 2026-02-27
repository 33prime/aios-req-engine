/**
 * BuildingCardOverlay — Live progress overlay for project cards that are building.
 *
 * Polls launch progress every 3s and shows current step + progress bar.
 * Used by ProjectsCards, home page ProjectCard, and ProjectRow.
 */

'use client'

import { useState, useEffect, useRef } from 'react'
import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { getLaunchProgress } from '@/lib/api'
import type { LaunchStepStatus } from '@/types/workspace'

// Step labels that are more descriptive for the card overlay
const STEP_DISPLAY: Record<string, string> = {
  company_research: 'Researching company...',
  entity_generation: 'Generating entities...',
  stakeholder_enrichment: 'Enriching stakeholders...',
  quality_check: 'Running quality check...',
}

interface BuildingCardOverlayProps {
  projectId: string
  launchId: string | null | undefined
  /** Compact mode for table rows — single line */
  compact?: boolean
}

export function BuildingCardOverlay({ projectId, launchId, compact }: BuildingCardOverlayProps) {
  const [steps, setSteps] = useState<LaunchStepStatus[]>([])
  const [progressPct, setProgressPct] = useState(0)
  const pollRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (!launchId) return

    const poll = async () => {
      try {
        const data = await getLaunchProgress(projectId, launchId)
        setSteps(data.steps)
        setProgressPct(data.progress_pct)
      } catch {
        // Non-fatal
      }
    }

    poll()
    pollRef.current = setInterval(poll, 3000)

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [projectId, launchId])

  const activeStep = steps.find(s => s.status === 'running')
  const completedCount = steps.filter(s => s.status === 'completed' || s.status === 'skipped').length
  const activeLabel = activeStep
    ? STEP_DISPLAY[activeStep.step_key] || activeStep.step_label
    : completedCount === steps.length && steps.length > 0
      ? 'Finishing up...'
      : 'Starting build...'

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="w-3.5 h-3.5 text-brand-primary animate-spin flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <span className="text-xs text-[#333] truncate block">{activeLabel}</span>
        </div>
        <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden flex-shrink-0">
          <div
            className="h-full bg-brand-primary rounded-full transition-all duration-500"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>
    )
  }

  return (
    <div className="absolute inset-0 z-10 bg-white/85 backdrop-blur-[2px] flex flex-col items-center justify-center gap-2.5 rounded-2xl px-5">
      {/* Animated spinner */}
      <Loader2 className="w-7 h-7 text-brand-primary animate-spin" />

      {/* Active step label */}
      <p className="text-[13px] font-medium text-text-body">{activeLabel}</p>

      {/* Progress bar */}
      <div className="w-full max-w-[180px]">
        <div className="h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-primary rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      {/* Step checklist */}
      {steps.length > 0 && (
        <div className="flex flex-col gap-1 mt-1 w-full max-w-[200px]">
          {steps.map((step) => {
            const Icon = step.status === 'completed' ? CheckCircle2
              : step.status === 'running' ? Loader2
              : step.status === 'failed' ? XCircle
              : null

            if (!Icon && step.status === 'pending') {
              return (
                <div key={step.step_key} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full border border-border flex-shrink-0" />
                  <span className="text-[11px] text-[#999]">{step.step_label}</span>
                </div>
              )
            }

            const iconClass = step.status === 'completed' ? 'text-brand-primary'
              : step.status === 'running' ? 'text-brand-primary animate-spin'
              : step.status === 'failed' ? 'text-red-500'
              : 'text-[#999]'

            return (
              <div key={step.step_key} className="flex items-center gap-2">
                {Icon && <Icon className={`w-3 h-3 flex-shrink-0 ${iconClass}`} />}
                <span className={`text-[11px] ${
                  step.status === 'completed' || step.status === 'running' ? 'text-[#333]' : 'text-[#999]'
                }`}>
                  {step.step_label}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
