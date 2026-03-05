'use client'

import { Zap } from 'lucide-react'
import type { FocusArea } from '@/types/call-intelligence'

export function FocusAreasCompact({
  areas,
}: {
  areas: FocusArea[]
}) {
  if (!areas || areas.length === 0) return null

  return (
    <div className="mt-7">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5 mb-3">
        <Zap className="w-3.5 h-3.5" /> Focus Areas
      </h3>
      <div className="space-y-2">
        {areas.map((fa, i) => (
          <div key={i} className="flex items-start gap-2.5 px-3 py-2 bg-white rounded-lg border border-border">
            <span className={`shrink-0 px-2 py-0.5 text-[10px] font-semibold rounded-full mt-0.5 ${
              fa.priority === 'high' ? 'bg-red-100 text-red-700' :
              fa.priority === 'medium' ? 'bg-amber-100 text-amber-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              {fa.priority}
            </span>
            <div className="min-w-0">
              <p className="text-[13px] font-medium text-text-body leading-snug">{fa.area}</p>
              <p className="text-[11px] text-text-muted mt-0.5 truncate">{fa.context}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
