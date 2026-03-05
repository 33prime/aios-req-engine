'use client'

import type { ConsultantPerformance } from '@/types/call-intelligence'

export function TalkRatioBar({ data }: { data: ConsultantPerformance['consultant_talk_ratio'] }) {
  if (!data || typeof data.consultant_share !== 'number') return null
  const consultantPct = Math.round(data.consultant_share * 100)
  const clientPct = 100 - consultantPct

  return (
    <div className="space-y-2">
      <h5 className="text-xs font-semibold text-text-muted uppercase tracking-wide">Talk Ratio</h5>
      <div className="h-6 rounded-full overflow-hidden flex">
        <div className="bg-brand-primary flex items-center justify-center" style={{ width: `${consultantPct}%` }}>
          <span className="text-[10px] font-bold text-white">{consultantPct}%</span>
        </div>
        <div className="bg-[#E0EFF3] flex items-center justify-center" style={{ width: `${clientPct}%` }}>
          <span className="text-[10px] font-bold text-[#044159]">{clientPct}%</span>
        </div>
      </div>
      <div className="flex justify-between text-xs text-text-muted">
        <span>Consultant</span>
        <span>Client</span>
      </div>
      <div className="relative h-1 bg-gray-100 rounded-full">
        <div className="absolute h-full bg-[#3FAF7A]/30 rounded-full" style={{ left: '30%', width: '10%' }} />
        <div className="absolute w-0.5 h-3 bg-brand-primary rounded-full -top-1" style={{ left: `${consultantPct}%` }} />
      </div>
      <p className="text-xs text-text-muted">Ideal: {data.ideal_range || '30-40%'} consultant share</p>
      {data.assessment && <p className="text-xs text-text-body italic">{data.assessment}</p>}
    </div>
  )
}
