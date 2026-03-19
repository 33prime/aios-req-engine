'use client'

import type { PatternRendererProps } from './types'

const COLUMNS = ['To Do', 'In Progress', 'Done', 'Blocked']
const COL_COLORS = ['#044159', '#3FAF7A', '#0A1E2F', '#D4A017']

export function KanbanPattern({ fields }: PatternRendererProps) {
  const items = fields.slice(0, 8)
  // Distribute items across columns
  const columns = COLUMNS.map((name, ci) => ({
    name,
    color: COL_COLORS[ci],
    cards: items.filter((_, i) => i % COLUMNS.length === ci),
  }))

  return (
    <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${Math.min(COLUMNS.length, 4)}, 1fr)` }}>
      {columns.map((col, ci) => (
        <div key={ci} className="rounded-[7px] p-2" style={{ background: '#EDF2F7', minHeight: 120 }}>
          <div className="flex items-center gap-1.5 mb-2">
            <div className="w-[6px] h-[6px] rounded-full" style={{ background: col.color }} />
            <span className="text-[8px] font-semibold uppercase tracking-wide" style={{ color: col.color }}>{col.name}</span>
            <span className="text-[8px] ml-auto" style={{ color: '#A0AEC0' }}>{col.cards.length}</span>
          </div>
          <div className="flex flex-col gap-1.5">
            {col.cards.map((f, i) => (
              <div key={i} className="rounded-[5px] p-2 bg-white" style={{ border: '1px solid #E2E8F0' }}>
                <div className="text-[9px] font-medium mb-0.5" style={{ color: '#0A1E2F' }}>{f.name}</div>
                <div className="text-[8px]" style={{ color: '#718096' }}>{f.mock_value}</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
