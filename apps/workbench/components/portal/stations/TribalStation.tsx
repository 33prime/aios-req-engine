'use client'

import { BookOpen } from 'lucide-react'

interface TribalStationProps {
  tribalKnowledge: string[]
}

export function TribalStation({ tribalKnowledge }: TribalStationProps) {
  const items = tribalKnowledge.filter(
    (t) => !t.startsWith('[constraint]') && !t.startsWith('[ai_wishlist]')
  )

  if (items.length === 0) {
    return (
      <div className="text-center py-4">
        <BookOpen className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-xs text-text-muted">No tribal knowledge captured yet.</p>
        <p className="text-xs text-text-placeholder mt-1">Chat below to share edge cases, gotchas, and insider knowledge.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="bg-surface-subtle rounded-lg px-3 py-2">
          <p className="text-xs text-text-secondary">{item}</p>
        </div>
      ))}
      <p className="text-[10px] text-text-placeholder text-center pt-1">Chat below to add more</p>
    </div>
  )
}
