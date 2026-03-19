'use client'

import type { PatternRendererProps } from './types'

const PLACEHOLDER_COLORS = ['rgba(63,175,122,0.12)', 'rgba(4,65,89,0.10)', 'rgba(212,160,23,0.10)', 'rgba(10,30,47,0.08)', 'rgba(63,175,122,0.08)', 'rgba(4,65,89,0.06)']

export function GalleryPattern({ fields }: PatternRendererProps) {
  const items = fields.slice(0, 6)
  return (
    <>
      {/* Filter bar */}
      <div className="flex items-center gap-1.5 mb-3">
        {['All', 'Recent', 'Approved', 'Pending'].map((label, i) => (
          <button
            key={label}
            className="px-2 py-[3px] rounded text-[9px] font-medium"
            style={{
              background: i === 0 ? 'rgba(63,175,122,0.08)' : 'transparent',
              color: i === 0 ? '#2A8F5F' : '#718096',
              border: i > 0 ? '1px solid #E2E8F0' : 'none',
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {/* Card grid */}
      <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))' }}>
        {items.map((f, i) => (
          <div key={i} className="rounded-[7px] overflow-hidden" style={{ border: '1px solid #E2E8F0' }}>
            {/* Colored placeholder image */}
            <div
              className="flex items-center justify-center"
              style={{ height: 70, background: PLACEHOLDER_COLORS[i % PLACEHOLDER_COLORS.length] }}
            >
              <span className="text-[18px] opacity-30">&#9724;</span>
            </div>
            <div className="p-2">
              <div className="text-[9px] font-medium truncate" style={{ color: '#0A1E2F' }}>{f.name}</div>
              <div className="text-[8px]" style={{ color: '#718096' }}>{f.mock_value}</div>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}
