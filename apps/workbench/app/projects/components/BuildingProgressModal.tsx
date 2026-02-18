'use client'

import { useState, useEffect } from 'react'
import { X, Check, Loader2, Circle, AlertCircle } from 'lucide-react'
import { getLaunchProgress } from '@/lib/api'

interface BuildingProgressModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  launchId: string
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

export function BuildingProgressModal({
  isOpen,
  onClose,
  projectId,
  launchId,
}: BuildingProgressModalProps) {
  const [steps, setSteps] = useState<StepStatus[]>([])
  const [progressPct, setProgressPct] = useState(0)
  const [status, setStatus] = useState('pending')

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
  }, [isOpen, projectId, launchId])

  if (!isOpen) return null

  const isDone = ['completed', 'completed_with_errors', 'failed'].includes(status)

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

        <h3 className="text-lg font-semibold text-[#333333] mb-1">
          {isDone ? 'Build Complete' : 'Building Your Project'}
        </h3>

        {/* Progress bar */}
        <div className="w-full h-2 bg-[#E5E5E5] rounded-full overflow-hidden mt-4 mb-5">
          <div
            className="h-full bg-[#3FAF7A] rounded-full transition-all duration-500"
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

        <div className="mt-5 flex justify-center">
          <button
            onClick={onClose}
            className="text-sm text-[#666666] hover:text-[#333333] px-4 py-2"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
