'use client'

import { useState } from 'react'
import { updateReviewStatus } from '@/lib/api'
import type { ReviewStatusValue } from '@/lib/api/tasks'

interface ReviewStatusBarProps {
  status: ReviewStatusValue | string | null
  projectId: string
  taskId: string
  onUpdate: () => void
}

const steps: { value: ReviewStatusValue; label: string }[] = [
  { value: 'pending_review', label: 'Pending' },
  { value: 'in_review', label: 'In Review' },
  { value: 'approved', label: 'Approved' },
]

const stepIndex = (s: string | null): number => {
  if (!s) return -1
  const idx = steps.findIndex((st) => st.value === s)
  return idx >= 0 ? idx : s === 'changes_requested' ? 1 : -1
}

export function ReviewStatusBar({ status, projectId, taskId, onUpdate }: ReviewStatusBarProps) {
  const [updating, setUpdating] = useState(false)
  const currentIdx = stepIndex(status)

  const handleAdvance = async (nextStatus: ReviewStatusValue) => {
    setUpdating(true)
    try {
      await updateReviewStatus(projectId, taskId, nextStatus)
      onUpdate()
    } catch (e) {
      console.error('Failed to update review status:', e)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="mb-4">
      <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[#999] mb-2">
        Review Status
      </h3>
      <div className="flex items-center gap-1">
        {steps.map((step, idx) => {
          const isActive = idx <= currentIdx
          const isCurrent = idx === currentIdx
          return (
            <button
              key={step.value}
              disabled={updating || idx <= currentIdx}
              onClick={() => handleAdvance(step.value)}
              className={`flex-1 py-2 px-3 text-[13px] font-medium rounded-lg border transition-colors ${
                isCurrent
                  ? 'bg-brand-primary text-white border-brand-primary'
                  : isActive
                  ? 'bg-brand-primary-light text-[#25785A] border-brand-primary/20'
                  : 'bg-white text-[#999] border-border hover:border-brand-primary hover:text-[#333]'
              } disabled:cursor-default disabled:hover:border-current`}
            >
              {step.label}
            </button>
          )
        })}
      </div>
      {status === 'changes_requested' && (
        <div className="mt-2 text-[13px] text-amber-700 bg-amber-50 px-3 py-2 rounded-lg">
          Changes requested — review feedback and update before re-submitting.
        </div>
      )}
    </div>
  )
}
