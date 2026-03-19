'use client'

import type { PatternRendererProps } from './types'

export function TreePattern({ fields }: PatternRendererProps) {
  const items = fields.slice(0, 6)
  // Create a tree-like structure from flat fields
  const tree = [
    { name: items[0]?.name || 'Root', depth: 0, expanded: true },
    { name: items[1]?.name || 'Category A', depth: 1, expanded: true },
    { name: items[2]?.name || 'Item 1', depth: 2, expanded: false },
    { name: items[3]?.name || 'Item 2', depth: 2, expanded: false },
    { name: items[4]?.name || 'Category B', depth: 1, expanded: false },
    { name: items[5]?.name || 'Item 3', depth: 2, expanded: false },
  ]

  return (
    <div className="rounded-[7px] p-3" style={{ background: '#EDF2F7', border: '1px solid #E2E8F0' }}>
      {tree.map((node, i) => {
        const field = items[i]
        return (
          <div
            key={i}
            className="flex items-center gap-1.5 py-1.5"
            style={{ paddingLeft: node.depth * 20 }}
          >
            {/* Expand/collapse indicator */}
            <span
              className="w-4 h-4 rounded flex items-center justify-center text-[10px] flex-shrink-0 cursor-pointer"
              style={{
                background: node.expanded ? 'rgba(63,175,122,0.08)' : 'rgba(0,0,0,0.04)',
                color: node.expanded ? '#3FAF7A' : '#A0AEC0',
              }}
            >
              {node.depth < 2 ? (node.expanded ? '\u25BE' : '\u25B8') : '\u2022'}
            </span>
            <span className="text-[10px] font-medium flex-1" style={{ color: '#0A1E2F' }}>{node.name}</span>
            {field && (
              <span className="text-[8px] flex-shrink-0" style={{ color: '#718096' }}>{field.mock_value}</span>
            )}
          </div>
        )
      })}
    </div>
  )
}
