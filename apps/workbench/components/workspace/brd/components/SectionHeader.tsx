'use client'

import { Check } from 'lucide-react'

interface SectionHeaderProps {
  title: string
  count: number
  onConfirmAll?: () => void
  confirmedCount?: number
}

export function SectionHeader({ title, count, onConfirmAll, confirmedCount = 0 }: SectionHeaderProps) {
  const allConfirmed = confirmedCount >= count && count > 0

  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        <h2 className="text-lg font-semibold text-[#37352f]">{title}</h2>
        <span className="text-[13px] text-[rgba(55,53,47,0.5)] font-medium">
          ({count})
        </span>
      </div>
      <div className="flex items-center gap-2">
        {onConfirmAll && count > 0 && !allConfirmed && (
          <button
            onClick={onConfirmAll}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"
          >
            <Check className="w-3.5 h-3.5" />
            Confirm All
          </button>
        )}
      </div>
    </div>
  )
}
