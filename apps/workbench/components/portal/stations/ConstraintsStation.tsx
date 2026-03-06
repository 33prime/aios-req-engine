'use client'

import { ShieldAlert } from 'lucide-react'

interface ConstraintsStationProps {
  tribalKnowledge: string[]
}

export function ConstraintsStation({ tribalKnowledge }: ConstraintsStationProps) {
  const constraints = tribalKnowledge
    .filter((t) => t.startsWith('[constraint]'))
    .map((t) => t.replace('[constraint] ', '').replace('[constraint]', ''))

  if (constraints.length === 0) {
    return (
      <div className="text-center py-4">
        <ShieldAlert className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-xs text-text-muted">No constraints documented yet.</p>
        <p className="text-xs text-text-placeholder mt-1">Chat below to add compliance, budget, or technical constraints.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {constraints.map((c, i) => (
        <div key={i} className="bg-surface-subtle rounded-lg px-3 py-2 flex items-start gap-2">
          <ShieldAlert className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-text-secondary">{c}</p>
        </div>
      ))}
      <p className="text-[10px] text-text-placeholder text-center pt-1">Chat below to add more</p>
    </div>
  )
}
