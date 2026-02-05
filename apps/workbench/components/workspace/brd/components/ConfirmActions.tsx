'use client'

import { Check, AlertCircle } from 'lucide-react'

interface ConfirmActionsProps {
  status: string | null | undefined
  onConfirm: () => void
  onNeedsReview: () => void
  size?: 'sm' | 'md'
}

export function ConfirmActions({ status, onConfirm, onNeedsReview, size = 'sm' }: ConfirmActionsProps) {
  const isConfirmed = status === 'confirmed_consultant' || status === 'confirmed_client'
  const isNeedsReview = status === 'needs_client' || status === 'needs_confirmation'

  const btnBase = size === 'sm'
    ? 'px-2.5 py-1 text-[11px] rounded-md'
    : 'px-3 py-1.5 text-xs rounded-md'

  return (
    <div className="flex items-center gap-1.5">
      <button
        onClick={(e) => { e.stopPropagation(); onConfirm() }}
        disabled={isConfirmed}
        className={`${btnBase} font-medium inline-flex items-center gap-1 transition-colors ${
          isConfirmed
            ? 'bg-teal-50 text-teal-700 cursor-default'
            : 'bg-white border border-gray-200 text-gray-600 hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200'
        }`}
      >
        <Check className="w-3 h-3" />
        {isConfirmed ? 'Confirmed' : 'Confirm'}
      </button>
      {!isConfirmed && (
        <button
          onClick={(e) => { e.stopPropagation(); onNeedsReview() }}
          disabled={isNeedsReview}
          className={`${btnBase} font-medium inline-flex items-center gap-1 transition-colors ${
            isNeedsReview
              ? 'bg-yellow-50 text-yellow-700 cursor-default'
              : 'bg-white border border-gray-200 text-gray-600 hover:bg-yellow-50 hover:text-yellow-700 hover:border-yellow-200'
          }`}
        >
          <AlertCircle className="w-3 h-3" />
          Review
        </button>
      )}
    </div>
  )
}
