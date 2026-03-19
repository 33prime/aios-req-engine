'use client'

import type { PatternRendererProps } from './types'

export function MetricsPattern({ fields }: PatternRendererProps) {
  const kpis = fields.filter(f => f.type === 'displayed' || f.type === 'computed').slice(0, 4)
  const sparkData = [40, 55, 48, 62, 58, 72, 68, 78, 82, 88, 85, 92]
  const colors = ['#3FAF7A', '#044159', '#D4A017', '#2D6B4A']

  return (
    <div className="space-y-3">
      {/* Large KPI blocks */}
      <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        {kpis.map((f, i) => (
          <div key={i} className="rounded-[7px] p-3" style={{ background: '#EDF2F7', border: '1px solid #E2E8F0' }}>
            <div className="text-[7px] uppercase tracking-wide font-medium mb-1" style={{ color: '#718096' }}>{f.name}</div>
            <div className="text-[24px] font-extrabold leading-none mb-1.5" style={{ color: colors[i % colors.length] }}>
              {f.mock_value}
            </div>
            {/* Sparkline */}
            <div className="flex items-end gap-[2px]" style={{ height: 24 }}>
              {sparkData.map((h, j) => (
                <div
                  key={j}
                  className="flex-1 rounded-t-sm"
                  style={{ height: `${h}%`, background: `${colors[i % colors.length]}40` }}
                />
              ))}
            </div>
            {/* Period comparison */}
            <div className="flex items-center gap-1 mt-1.5">
              <span className="text-[8px] font-semibold" style={{ color: '#2A8F5F' }}>+12%</span>
              <span className="text-[8px]" style={{ color: '#A0AEC0' }}>vs last period</span>
            </div>
          </div>
        ))}
      </div>

      {/* Summary row */}
      {kpis.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-[7px]" style={{ background: 'rgba(63,175,122,0.04)', border: '1px solid rgba(63,175,122,0.12)' }}>
          <div className="w-5 h-5 rounded-full flex items-center justify-center text-[10px]" style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}>
            &#x2713;
          </div>
          <span className="text-[10px]" style={{ color: '#2D3748' }}>All KPIs trending positive this period</span>
        </div>
      )}
    </div>
  )
}
