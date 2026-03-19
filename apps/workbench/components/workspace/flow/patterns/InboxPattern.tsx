'use client'

import type { PatternRendererProps } from './types'

export function InboxPattern({ fields, detail }: PatternRendererProps) {
  const actors = detail.actors || ['System']
  const messages = fields.slice(0, 5)

  return (
    <div className="rounded-[7px] overflow-hidden" style={{ border: '1px solid #E2E8F0' }}>
      {/* Inbox toolbar */}
      <div className="flex items-center gap-2 px-3 py-2" style={{ background: '#EDF2F7', borderBottom: '1px solid #E2E8F0' }}>
        <span className="text-[9px] font-semibold" style={{ color: '#0A1E2F' }}>Inbox</span>
        <span className="text-[8px] px-1.5 py-0.5 rounded-full" style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}>
          {messages.length} new
        </span>
        <div className="ml-auto flex gap-1">
          <button className="text-[8px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.04)', color: '#718096' }}>Filter</button>
          <button className="text-[8px] px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.04)', color: '#718096' }}>Sort</button>
        </div>
      </div>
      {/* Message list */}
      {messages.map((f, i) => (
        <div
          key={i}
          className="flex items-start gap-2.5 px-3 py-2.5 cursor-pointer"
          style={{
            borderBottom: '1px solid rgba(0,0,0,0.04)',
            background: i < 2 ? 'rgba(63,175,122,0.02)' : 'transparent',
          }}
        >
          {/* Unread dot */}
          {i < 2 && (
            <div className="w-[6px] h-[6px] rounded-full mt-1.5 flex-shrink-0" style={{ background: '#3FAF7A' }} />
          )}
          {i >= 2 && <div className="w-[6px] flex-shrink-0" />}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-[10px] font-semibold truncate" style={{ color: '#0A1E2F' }}>{actors[i % actors.length]}</span>
              <span className="text-[8px] ml-auto flex-shrink-0" style={{ color: '#A0AEC0' }}>{i === 0 ? '2m ago' : `${i}h ago`}</span>
            </div>
            <div className="text-[9px] font-medium truncate" style={{ color: '#2D3748' }}>{f.name}</div>
            <div className="text-[8px] truncate" style={{ color: '#718096' }}>{f.mock_value}</div>
          </div>
        </div>
      ))}
    </div>
  )
}
