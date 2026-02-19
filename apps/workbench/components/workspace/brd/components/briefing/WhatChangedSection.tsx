'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { TemporalDiff } from '@/types/workspace'
import { CHANGE_TYPE_ICONS, CHANGE_TYPE_COLORS } from '@/lib/action-constants'

interface WhatChangedSectionProps {
  whatChanged: TemporalDiff
}

export function WhatChangedSection({ whatChanged }: WhatChangedSectionProps) {
  const [expanded, setExpanded] = useState(true)

  const hasChanges = whatChanged.changes.length > 0

  return (
    <div className="border-b border-[#E5E5E5]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2.5 flex items-center justify-between hover:bg-[#FAFAFA] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide">
            What Changed
          </span>
          {hasChanges && (
            <span className="text-[10px] text-[#999999]">
              since {whatChanged.since_label}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {hasChanges && (
            <span className="text-[10px] font-medium text-[#3FAF7A] bg-[#E8F5E9] px-1.5 py-0.5 rounded-full">
              {whatChanged.changes.length}
            </span>
          )}
          <ChevronDown
            className={`w-3.5 h-3.5 text-[#999999] transition-transform duration-200 ${
              expanded ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-3">
          {!hasChanges ? (
            <p className="text-[12px] text-[#999999] py-2">
              {whatChanged.since_timestamp
                ? `Nothing changed since ${whatChanged.since_label}`
                : "Welcome — we'll track changes after your first session"}
            </p>
          ) : (
            <div className="space-y-1.5">
              {/* Summary */}
              {whatChanged.change_summary && (
                <p className="text-[12px] text-[#333333] mb-2 leading-relaxed">
                  {whatChanged.change_summary}
                </p>
              )}

              {/* Change items */}
              {whatChanged.changes.slice(0, 8).map((change, i) => {
                const Icon = CHANGE_TYPE_ICONS[change.change_type]
                const color = CHANGE_TYPE_COLORS[change.change_type] || '#666666'

                return (
                  <div key={i} className="flex items-start gap-2 py-1">
                    {Icon && (
                      <Icon
                        className="w-3.5 h-3.5 flex-shrink-0 mt-0.5"
                        style={{ color }}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-[#333333] truncate">
                        {change.summary}
                      </p>
                      {change.confidence_delta != null && change.confidence_delta !== 0 && (
                        <span
                          className="text-[10px] font-medium"
                          style={{
                            color: change.confidence_delta > 0 ? '#3FAF7A' : '#999999',
                          }}
                        >
                          {change.confidence_delta > 0 ? '+' : ''}
                          {(change.confidence_delta * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}

              {/* Counts summary */}
              {Object.keys(whatChanged.counts).length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2 pt-2 border-t border-[#E5E5E5]">
                  {Object.entries(whatChanged.counts).map(([key, val]) => (
                    val > 0 && (
                      <span key={key} className="text-[10px] text-[#666666] bg-[#F0F0F0] px-2 py-0.5 rounded-full">
                        {val} {key.replace(/_/g, ' ')}
                      </span>
                    )
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
