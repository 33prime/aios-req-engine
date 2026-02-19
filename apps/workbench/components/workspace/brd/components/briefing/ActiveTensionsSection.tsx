'use client'

import { useState } from 'react'
import { ChevronDown, Swords } from 'lucide-react'
import type { Tension } from '@/types/workspace'

interface ActiveTensionsSectionProps {
  tensions: Tension[]
}

export function ActiveTensionsSection({ tensions }: ActiveTensionsSectionProps) {
  const [expanded, setExpanded] = useState(true)

  if (tensions.length === 0) return null

  return (
    <div className="border-b border-[#E5E5E5]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2.5 flex items-center justify-between hover:bg-[#FAFAFA] transition-colors"
      >
        <div className="flex items-center gap-2">
          <Swords className="w-3.5 h-3.5 text-[#666666]" />
          <span className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide">
            Active Tensions
          </span>
          <span className="text-[10px] font-medium text-[#666666] bg-[#F0F0F0] px-1.5 py-0.5 rounded-full">
            {tensions.length}
          </span>
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 text-[#999999] transition-transform duration-200 ${
            expanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {tensions.map((tension) => (
            <div
              key={tension.tension_id}
              className="border border-[#E5E5E5] rounded-xl p-3 bg-white"
            >
              <p className="text-[12px] text-[#333333] font-medium mb-2">
                {tension.summary}
              </p>

              <div className="flex gap-2">
                {/* Side A */}
                <div className="flex-1 bg-[#F4F4F4] rounded-lg p-2">
                  <p className="text-[11px] text-[#666666] leading-relaxed">
                    {tension.side_a}
                  </p>
                </div>

                {/* VS divider */}
                <div className="flex items-center">
                  <span className="text-[9px] font-bold text-[#999999]">vs</span>
                </div>

                {/* Side B */}
                <div className="flex-1 bg-[#F4F4F4] rounded-lg p-2">
                  <p className="text-[11px] text-[#666666] leading-relaxed">
                    {tension.side_b}
                  </p>
                </div>
              </div>

              {/* Confidence */}
              <div className="mt-2 flex items-center gap-2">
                <div className="flex-1 h-1 bg-[#E5E5E5] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#999999] rounded-full"
                    style={{ width: `${tension.confidence * 100}%` }}
                  />
                </div>
                <span className="text-[10px] text-[#999999]">
                  {Math.round(tension.confidence * 100)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
