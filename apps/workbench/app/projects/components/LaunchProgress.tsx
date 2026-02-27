'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  SkipForward,
  ArrowRight,
  X,
} from 'lucide-react'
import { getLaunchProgress } from '@/lib/api'
import type { LaunchProgressResponse, LaunchStepStatus } from '@/types/workspace'

interface LaunchProgressProps {
  projectId: string
  launchId: string
  projectName: string
  onDismiss: () => void
}

const STATUS_ICONS: Record<
  string,
  { icon: typeof Clock; className: string; spin?: boolean }
> = {
  pending: { icon: Clock, className: 'text-text-placeholder' },
  running: { icon: Loader2, className: 'text-brand-primary', spin: true },
  completed: { icon: CheckCircle2, className: 'text-brand-primary' },
  failed: { icon: XCircle, className: 'text-[#DC2626]' },
  skipped: { icon: SkipForward, className: 'text-text-placeholder' },
}

const TERMINAL_STATUSES = new Set(['completed', 'completed_with_errors', 'failed'])

export function LaunchProgress({
  projectId,
  launchId,
  projectName,
  onDismiss,
}: LaunchProgressProps) {
  const [progress, setProgress] = useState<LaunchProgressResponse | null>(null)
  const [error, setError] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const fetchProgress = useCallback(async () => {
    try {
      const data = await getLaunchProgress(projectId, launchId)
      setProgress(data)
      if (TERMINAL_STATUSES.has(data.status)) {
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
          intervalRef.current = null
        }
      }
    } catch {
      setError(true)
    }
  }, [projectId, launchId])

  useEffect(() => {
    fetchProgress()
    intervalRef.current = setInterval(fetchProgress, 3000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [fetchProgress])

  if (error && !progress) {
    return null
  }

  const isTerminal = progress ? TERMINAL_STATUSES.has(progress.status) : false
  const hasErrors = progress?.status === 'completed_with_errors' || progress?.status === 'failed'

  return (
    <div className="bg-white border border-border rounded-2xl shadow-md mx-4 mt-4 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          {!isTerminal && (
            <Loader2 className="w-4 h-4 text-brand-primary animate-spin" />
          )}
          {isTerminal && !hasErrors && (
            <CheckCircle2 className="w-4 h-4 text-brand-primary" />
          )}
          {isTerminal && hasErrors && (
            <XCircle className="w-4 h-4 text-[#DC2626]" />
          )}
          <span className="text-[14px] font-semibold text-text-body">
            {isTerminal ? `Setup complete for "${projectName}"` : `Setting up "${projectName}"`}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={onDismiss}
            className="flex items-center gap-1.5 text-[13px] font-medium text-brand-primary hover:text-[#25785A] transition-colors"
          >
            Go to Workspace
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onDismiss}
            className="text-text-placeholder hover:text-[#666666] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Progress bar */}
      <div className="px-5 pt-3">
        <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-primary rounded-full transition-all duration-500 ease-out"
            style={{ width: `${progress?.progress_pct || 0}%` }}
          />
        </div>
        <p className="text-[12px] text-text-placeholder mt-1 text-right">
          {progress?.progress_pct || 0}%
        </p>
      </div>

      {/* Steps */}
      <div className="px-5 pb-4 space-y-1.5">
        {(progress?.steps || []).map((step) => (
          <StepRow key={step.step_key} step={step} />
        ))}
      </div>

      {/* Error summary */}
      {hasErrors && isTerminal && (
        <div className="px-5 pb-4">
          <p className="text-[13px] text-text-placeholder">
            Some steps couldn&apos;t complete — you can run them manually from the workspace.
          </p>
        </div>
      )}
    </div>
  )
}

function StepRow({ step }: { step: LaunchStepStatus }) {
  const config = STATUS_ICONS[step.status] || STATUS_ICONS.pending
  const Icon = config.icon

  return (
    <div className="flex items-center gap-3 py-1">
      <Icon
        className={`w-4 h-4 flex-shrink-0 ${config.className} ${config.spin ? 'animate-spin' : ''}`}
      />
      <span
        className={`text-[13px] font-medium flex-shrink-0 ${
          step.status === 'completed'
            ? 'text-text-body'
            : step.status === 'failed'
              ? 'text-[#DC2626]'
              : step.status === 'running'
                ? 'text-text-body'
                : 'text-text-placeholder'
        }`}
      >
        {step.step_label}
      </span>
      <span className="text-[12px] text-text-placeholder truncate">
        {step.status === 'running' && 'Running...'}
        {step.status === 'completed' && step.result_summary}
        {step.status === 'failed' && step.error_message}
        {step.status === 'skipped' && step.result_summary}
        {step.status === 'pending' && 'Pending'}
      </span>
    </div>
  )
}
