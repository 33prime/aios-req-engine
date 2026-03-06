'use client'

import { Swords } from 'lucide-react'

interface Competitor {
  name: string
  worked?: string | null
  didnt_work?: string | null
  why_left?: string | null
}

interface CompetitorStationProps {
  competitors: Competitor[]
}

export function CompetitorStation({ competitors }: CompetitorStationProps) {
  if (competitors.length === 0) {
    return (
      <div className="text-center py-4">
        <Swords className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-xs text-text-muted">No competitors added yet.</p>
        <p className="text-xs text-text-placeholder mt-1">Chat below to add competitors and past tools.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {competitors.map((c, i) => (
        <div key={i} className="bg-surface-subtle rounded-lg px-3 py-2">
          <p className="text-sm font-medium text-text-primary">{c.name}</p>
          {c.worked && (
            <p className="text-xs text-text-muted mt-0.5">
              <span className="text-green-600">+</span> {c.worked}
            </p>
          )}
          {c.didnt_work && (
            <p className="text-xs text-text-muted mt-0.5">
              <span className="text-red-500">-</span> {c.didnt_work}
            </p>
          )}
          {c.why_left && (
            <p className="text-xs text-text-placeholder mt-0.5 italic">Left: {c.why_left}</p>
          )}
        </div>
      ))}
      <p className="text-[10px] text-text-placeholder text-center pt-1">Chat below to add more</p>
    </div>
  )
}
