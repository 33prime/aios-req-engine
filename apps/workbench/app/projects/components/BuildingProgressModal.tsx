'use client'

import { useState, useEffect, useRef } from 'react'
import { X, Check, Loader2, Circle, AlertCircle, CheckCircle2 } from 'lucide-react'
import { getLaunchProgress } from '@/lib/api'

interface BuildingProgressModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  launchId: string
  projectName?: string
  onBuildComplete?: () => void
}

interface StepStatus {
  step_key: string
  step_label: string
  status: string
  result_summary?: string | null
  error_message?: string | null
}

const STEP_ICON = {
  completed: <Check className="w-4 h-4 text-[#3FAF7A]" />,
  running: <Loader2 className="w-4 h-4 text-[#3FAF7A] animate-spin" />,
  pending: <Circle className="w-4 h-4 text-[#E5E5E5]" />,
  skipped: <Check className="w-4 h-4 text-[#999999]" />,
  failed: <AlertCircle className="w-4 h-4 text-red-500" />,
} as const

// Rich cycling sub-labels for each step when running
const STEP_SUB_LABELS: Record<string, string[]> = {
  company_research: [
    'Researching company background...',
    'Analyzing industry context...',
    'Identifying competitive landscape...',
    'Building company profile...',
  ],
  entity_generation: [
    'Analyzing business goals...',
    'Mapping current & future workflows...',
    'Identifying key personas...',
    'Generating requirements...',
    'Building feature roadmap...',
    'Connecting workflows to features...',
  ],
  stakeholder_enrichment: [
    'Enriching stakeholder profiles...',
    'Mapping organizational roles...',
    'Identifying decision-makers...',
  ],
  quality_check: [
    'Validating entity relationships...',
    'Checking for completeness...',
    'Running final quality checks...',
  ],
}

function CyclingLabel({ stepKey }: { stepKey: string }) {
  const labels = STEP_SUB_LABELS[stepKey]
  const [index, setIndex] = useState(0)
  const [fade, setFade] = useState(true)

  useEffect(() => {
    if (!labels || labels.length <= 1) return
    const interval = setInterval(() => {
      setFade(false)
      setTimeout(() => {
        setIndex((prev) => (prev + 1) % labels.length)
        setFade(true)
      }, 200)
    }, 3000)
    return () => clearInterval(interval)
  }, [labels])

  if (!labels) return null

  return (
    <p
      className={`text-xs text-[#999999] mt-0.5 transition-opacity duration-200 ${
        fade ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {labels[index]}
    </p>
  )
}

export function BuildingProgressModal({
  isOpen,
  onClose,
  projectId,
  launchId,
  projectName,
  onBuildComplete,
}: BuildingProgressModalProps) {
  const [steps, setSteps] = useState<StepStatus[]>([])
  const [progressPct, setProgressPct] = useState(0)
  const [status, setStatus] = useState('pending')
  const completedRef = useRef(false)

  useEffect(() => {
    if (!isOpen || !projectId || !launchId) return

    let active = true

    const poll = async () => {
      try {
        const data = await getLaunchProgress(projectId, launchId)
        if (!active) return
        setSteps(data.steps || [])
        setProgressPct(data.progress_pct || 0)
        setStatus(data.status)

        // Fire onBuildComplete once when terminal
        const terminal = ['completed', 'completed_with_errors', 'failed']
        if (terminal.includes(data.status) && !completedRef.current) {
          completedRef.current = true
          onBuildComplete?.()
        }
      } catch (err) {
        console.error('Failed to poll launch progress:', err)
      }
    }

    poll()
    const interval = setInterval(poll, 3000)

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [isOpen, projectId, launchId, onBuildComplete])

  // Reset completedRef when modal reopens with new launch
  useEffect(() => {
    completedRef.current = false
  }, [launchId])

  if (!isOpen) return null

  const isDone = ['completed', 'completed_with_errors', 'failed'].includes(status)
  const isFailed = status === 'failed'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-md" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[#999999] hover:text-[#333333]"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Header */}
        <div className="mb-1">
          {isDone && !isFailed ? (
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-[#3FAF7A]" />
              <h3 className="text-lg font-semibold text-[#333333]">Build Complete</h3>
            </div>
          ) : isFailed ? (
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 text-red-500" />
              <h3 className="text-lg font-semibold text-[#333333]">Build Failed</h3>
            </div>
          ) : (
            <h3 className="text-lg font-semibold text-[#333333]">Building Your Project</h3>
          )}
          {projectName && (
            <p className="text-sm text-[#666666] mt-0.5">{projectName}</p>
          )}
        </div>

        {/* Progress bar */}
        <div className="w-full h-2 bg-[#E5E5E5] rounded-full overflow-hidden mt-4 mb-5">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isFailed ? 'bg-red-500' : 'bg-[#3FAF7A]'
            }`}
            style={{ width: `${progressPct}%` }}
          />
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {steps.map((step) => (
            <div key={step.step_key} className="flex items-start gap-3">
              <div className="mt-0.5">
                {STEP_ICON[step.status as keyof typeof STEP_ICON] || STEP_ICON.pending}
              </div>
              <div className="flex-1 min-w-0">
                <p className={`text-sm ${
                  step.status === 'running' ? 'text-[#333333] font-medium' :
                  step.status === 'completed' ? 'text-[#333333]' :
                  step.status === 'failed' ? 'text-red-600' :
                  'text-[#999999]'
                }`}>
                  {step.step_label}
                  {step.status === 'running' && '...'}
                </p>
                {step.status === 'running' && (
                  <CyclingLabel stepKey={step.step_key} />
                )}
                {step.result_summary && step.status === 'completed' && (
                  <p className="text-xs text-[#999999] mt-0.5">{step.result_summary}</p>
                )}
                {step.error_message && (
                  <p className="text-xs text-red-500 mt-0.5">{step.error_message}</p>
                )}
              </div>
            </div>
          ))}
        </div>

        {!isDone && (
          <p className="text-xs text-[#999999] mt-5 text-center">
            We&apos;ll notify you when it&apos;s ready.
          </p>
        )}

        {isDone && !isFailed && (
          <p className="text-xs text-[#3FAF7A] mt-5 text-center font-medium">
            Your project is ready — click in to explore.
          </p>
        )}

        <div className="mt-5 flex justify-center">
          <button
            onClick={onClose}
            className="text-sm text-[#666666] hover:text-[#333333] px-4 py-2"
          >
            {isDone ? 'Done' : 'Close'}
          </button>
        </div>
      </div>
    </div>
  )
}
