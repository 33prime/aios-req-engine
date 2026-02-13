'use client'

import { useMemo } from 'react'
import { Key } from 'lucide-react'
import type { FeatureBRDSummary } from '@/types/workspace'

interface KeyFeaturesBarProps {
  mustHaveFeatures: FeatureBRDSummary[]
}

export function KeyFeaturesBar({ mustHaveFeatures }: KeyFeaturesBarProps) {
  const { confirmed, total, pct } = useMemo(() => {
    const total = mustHaveFeatures.length
    const confirmed = mustHaveFeatures.filter(
      (f) =>
        f.confirmation_status === 'confirmed_consultant' ||
        f.confirmation_status === 'confirmed_client'
    ).length
    const pct = total > 0 ? Math.round((confirmed / total) * 100) : 0
    return { confirmed, total, pct }
  }, [mustHaveFeatures])

  if (total === 0) return null

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5 mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Key className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[14px] font-semibold text-[#333333]">Key Features</span>
        </div>
        <span className="text-[12px] text-[#666666]">
          {total} must-have
        </span>
      </div>

      {/* Feature pills */}
      <div className="flex flex-wrap gap-2 mb-4">
        {mustHaveFeatures.map((f) => {
          const isConfirmed =
            f.confirmation_status === 'confirmed_consultant' ||
            f.confirmation_status === 'confirmed_client'
          return (
            <span
              key={f.id}
              className={`px-3 py-1.5 rounded-lg text-[12px] font-medium ${
                isConfirmed
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'bg-[#F0F0F0] text-[#666666]'
              }`}
            >
              {f.name}
            </span>
          )
        })}
      </div>

      {/* Progress bar */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#3FAF7A] rounded-full transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-[12px] font-medium text-[#666666] whitespace-nowrap">
          {confirmed}/{total} confirmed
        </span>
        <span className="text-[12px] font-bold text-[#333333]">{pct}%</span>
      </div>
    </div>
  )
}
