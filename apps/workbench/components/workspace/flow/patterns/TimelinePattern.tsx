'use client'

import type { PatternRendererProps } from './types'

export function TimelinePattern({ fields, detail }: PatternRendererProps) {
  const events = fields.slice(0, 6)
  const actors = detail.actors || ['System']
  return (
    <div className="relative pl-5">
      {/* Connecting line */}
      <div className="absolute left-[9px] top-2 bottom-2 w-[2px]" style={{ background: 'rgba(63,175,122,0.2)' }} />
      {events.map((f, i) => (
        <div key={i} className="relative flex items-start gap-3 pb-4">
          {/* Dot */}
          <div
            className="absolute left-[-14px] w-[10px] h-[10px] rounded-full flex-shrink-0 mt-1"
            style={{
              background: i === 0 ? '#3FAF7A' : i < 3 ? '#044159' : '#E2E8F0',
              border: i === 0 ? '2px solid rgba(63,175,122,0.3)' : 'none',
            }}
          />
          <div className="flex-1 rounded-[7px] p-2.5" style={{ background: '#EDF2F7' }}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] font-semibold" style={{ color: '#0A1E2F' }}>{f.name}</span>
              <span className="text-[8px]" style={{ color: '#A0AEC0' }}>{i === 0 ? 'Just now' : `${i * 2}h ago`}</span>
            </div>
            <div className="text-[9px] leading-snug" style={{ color: '#4A5568' }}>{f.mock_value}</div>
            <div className="text-[8px] mt-1" style={{ color: '#718096' }}>{actors[i % actors.length]}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
