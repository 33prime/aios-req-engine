'use client'

import type { PatternRendererProps } from './types'
import { KpiCards } from './shared'

export function CardPattern({ fields }: PatternRendererProps) {
  const items = fields.filter(f => f.type === 'computed' || f.type === 'displayed').slice(0, 4)
  const colors = ['#D4A017', '#3FAF7A', '#D4A017', '#3FAF7A']
  return (
    <>
      <KpiCards fields={fields} limit={3} />
      <div className="grid gap-2 mb-2.5" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))' }}>
        {items.map((f, i) => (
          <div key={i} className="rounded-[7px] p-3" style={{ background: '#fff', border: '1px solid #E2E8F0' }}>
            <div className="flex items-center justify-between mb-1.5">
              <div className="text-[10px] font-semibold" style={{ color: '#0A1E2F' }}>{f.name}</div>
              <span
                className="text-[7px] font-semibold uppercase px-[5px] py-[2px] rounded"
                style={{
                  background: i % 2 === 0 ? 'rgba(212,160,23,0.08)' : 'rgba(63,175,122,0.08)',
                  color: i % 2 === 0 ? '#8B6914' : '#2A8F5F',
                }}
              >
                {i % 2 === 0 ? 'Flag' : 'OK'}
              </span>
            </div>
            <div className="text-[18px] font-extrabold mb-[2px]" style={{ color: '#0A1E2F' }}>{f.mock_value}</div>
            <div className="text-[8px] mb-[5px]" style={{ color: '#718096' }}>{f.type}</div>
            <div className="h-[3px] rounded-full overflow-hidden" style={{ background: '#EDF2F7' }}>
              <div className="h-full rounded-full" style={{ width: `${60 + i * 10}%`, background: colors[i % colors.length] }} />
            </div>
            <div className="flex gap-[3px] mt-1.5">
              <span className="text-[8px] font-medium px-[7px] py-[2px] rounded cursor-pointer" style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}>Approve</span>
              <span className="text-[8px] font-medium px-[7px] py-[2px] rounded cursor-pointer" style={{ background: 'rgba(212,160,23,0.08)', color: '#8B6914' }}>Adjust</span>
            </div>
          </div>
        ))}
      </div>
      <div className="flex gap-1.5">
        <button className="px-3.5 py-1.5 rounded-[5px] text-[10px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Approve All</button>
        <button className="px-3.5 py-1.5 rounded-[5px] text-[10px] font-semibold" style={{ background: '#EDF2F7', color: '#4A5568', border: '1px solid #E2E8F0' }}>Generate POs</button>
      </div>
    </>
  )
}
