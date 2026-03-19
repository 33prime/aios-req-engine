'use client'

import type { PatternRendererProps } from './types'

export function MapPattern({ fields }: PatternRendererProps) {
  const locations = fields.slice(0, 5)
  return (
    <div className="flex gap-3">
      {/* Map placeholder */}
      <div className="flex-1 rounded-[7px] relative overflow-hidden" style={{ background: '#EDF2F7', border: '1px solid #E2E8F0', minHeight: 200 }}>
        {/* Grid lines */}
        {[20, 40, 60, 80].map(pct => (
          <div key={`h${pct}`} className="absolute left-0 right-0 h-px" style={{ top: `${pct}%`, background: 'rgba(0,0,0,0.04)' }} />
        ))}
        {[20, 40, 60, 80].map(pct => (
          <div key={`v${pct}`} className="absolute top-0 bottom-0 w-px" style={{ left: `${pct}%`, background: 'rgba(0,0,0,0.04)' }} />
        ))}
        {/* Marker dots */}
        {locations.map((_, i) => (
          <div
            key={i}
            className="absolute w-3 h-3 rounded-full"
            style={{
              background: i === 0 ? '#3FAF7A' : '#044159',
              border: '2px solid white',
              boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
              top: `${20 + (i * 15) % 60}%`,
              left: `${15 + (i * 18) % 65}%`,
            }}
          />
        ))}
        <div className="absolute bottom-2 right-2 text-[8px] px-1.5 py-0.5 rounded bg-white" style={{ color: '#718096', border: '1px solid #E2E8F0' }}>
          Geographic View
        </div>
      </div>
      {/* Location list */}
      <div className="w-[160px] flex flex-col gap-1.5">
        {locations.map((f, i) => (
          <div key={i} className="rounded-[5px] p-2" style={{ background: '#EDF2F7', border: '1px solid #E2E8F0' }}>
            <div className="flex items-center gap-1.5 mb-0.5">
              <div className="w-[6px] h-[6px] rounded-full" style={{ background: i === 0 ? '#3FAF7A' : '#044159' }} />
              <span className="text-[9px] font-medium" style={{ color: '#0A1E2F' }}>{f.name}</span>
            </div>
            <div className="text-[8px]" style={{ color: '#718096' }}>{f.mock_value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
