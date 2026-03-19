'use client'

import type { PatternRendererProps } from './types'

export function SplitviewPattern({ fields }: PatternRendererProps) {
  const items = fields.slice(0, 5)
  const selectedIdx = 0
  const selected = items[selectedIdx]

  return (
    <div className="flex gap-px rounded-[7px] overflow-hidden" style={{ border: '1px solid #E2E8F0', minHeight: 220 }}>
      {/* Master list */}
      <div className="w-[40%] flex flex-col" style={{ background: '#EDF2F7' }}>
        <div className="px-2.5 py-2 text-[8px] font-semibold uppercase tracking-wide" style={{ color: '#718096', borderBottom: '1px solid #E2E8F0' }}>
          Items ({items.length})
        </div>
        {items.map((f, i) => (
          <div
            key={i}
            className="px-2.5 py-2 cursor-pointer"
            style={{
              background: i === selectedIdx ? '#fff' : 'transparent',
              borderBottom: '1px solid rgba(0,0,0,0.04)',
              borderLeft: i === selectedIdx ? '3px solid #3FAF7A' : '3px solid transparent',
            }}
          >
            <div className="text-[10px] font-medium truncate" style={{ color: i === selectedIdx ? '#0A1E2F' : '#4A5568' }}>
              {f.name}
            </div>
            <div className="text-[8px] truncate" style={{ color: '#718096' }}>
              {f.mock_value}
            </div>
          </div>
        ))}
      </div>

      {/* Detail pane */}
      <div className="flex-1 bg-white p-3">
        {selected ? (
          <>
            <div className="text-[12px] font-bold mb-1" style={{ color: '#0A1E2F' }}>{selected.name}</div>
            <div className="text-[10px] leading-relaxed mb-3" style={{ color: '#4A5568' }}>{selected.mock_value}</div>
            {/* Detail fields */}
            {items.slice(1, 4).map((f, i) => (
              <div key={i} className="flex justify-between py-1.5" style={{ borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
                <span className="text-[9px]" style={{ color: '#718096' }}>{f.name}</span>
                <span className="text-[9px] font-medium" style={{ color: '#0A1E2F' }}>{f.mock_value}</span>
              </div>
            ))}
            <div className="flex gap-1.5 mt-3">
              <button className="px-3 py-1 rounded-[5px] text-[9px] font-semibold text-white" style={{ background: '#3FAF7A' }}>Edit</button>
              <button className="px-3 py-1 rounded-[5px] text-[9px] font-semibold" style={{ background: '#EDF2F7', color: '#4A5568', border: '1px solid #E2E8F0' }}>Archive</button>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-full text-[10px]" style={{ color: '#A0AEC0' }}>
            Select an item
          </div>
        )}
      </div>
    </div>
  )
}
