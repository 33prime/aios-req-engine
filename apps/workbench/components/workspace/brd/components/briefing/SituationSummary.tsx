'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import type { BriefingSituation, WhatYouShouldKnow } from '@/types/workspace'

interface SituationSummaryProps {
  situation: BriefingSituation
  whatYouShouldKnow: WhatYouShouldKnow
}

export function SituationSummary({ situation, whatYouShouldKnow }: SituationSummaryProps) {
  const [expanded, setExpanded] = useState(true)

  if (!situation.narrative && !whatYouShouldKnow.narrative) {
    return null
  }

  return (
    <div className="border-b border-[#E5E5E5]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2.5 flex items-center justify-between hover:bg-[#FAFAFA] transition-colors"
      >
        <span className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide">
          Situation
        </span>
        <ChevronDown
          className={`w-3.5 h-3.5 text-[#999999] transition-transform duration-200 ${
            expanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {expanded && (
        <div className="px-4 pb-3 space-y-3">
          {/* Narrative */}
          {situation.narrative && (
            <p className="text-[13px] text-[#333333] leading-relaxed">
              {situation.narrative}
            </p>
          )}

          {/* What you should know */}
          {whatYouShouldKnow.narrative && (
            <div className="bg-[#F4F4F4] rounded-xl p-3">
              <p className="text-[12px] font-medium text-[#333333] mb-1.5">
                {whatYouShouldKnow.narrative}
              </p>
              {whatYouShouldKnow.bullets.length > 0 && (
                <ul className="space-y-1">
                  {whatYouShouldKnow.bullets.map((bullet, i) => (
                    <li key={i} className="text-[12px] text-[#666666] flex items-start gap-1.5">
                      <span className="text-[#3FAF7A] mt-1 flex-shrink-0">&#8226;</span>
                      {bullet}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
