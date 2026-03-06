'use client'

import { Palette } from 'lucide-react'

interface DesignInspiration {
  name: string
  url?: string | null
  what_like?: string | null
}

interface DesignStationProps {
  designLove: DesignInspiration[]
  designAvoid?: string | null
}

export function DesignStation({ designLove, designAvoid }: DesignStationProps) {
  if (designLove.length === 0 && !designAvoid) {
    return (
      <div className="text-center py-4">
        <Palette className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-xs text-text-muted">No design preferences added yet.</p>
        <p className="text-xs text-text-placeholder mt-1">Chat below to share apps you love and styles to avoid.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {designLove.map((d, i) => (
        <div key={i} className="bg-surface-subtle rounded-lg px-3 py-2">
          <p className="text-sm font-medium text-text-primary">{d.name}</p>
          {d.what_like && (
            <p className="text-xs text-text-muted mt-0.5">{d.what_like}</p>
          )}
        </div>
      ))}
      {designAvoid && (
        <div className="bg-red-50 rounded-lg px-3 py-2 border border-red-100">
          <p className="text-[10px] uppercase tracking-wide text-red-500 font-medium mb-0.5">Avoid</p>
          <p className="text-xs text-red-700">{designAvoid}</p>
        </div>
      )}
      <p className="text-[10px] text-text-placeholder text-center pt-1">Chat below to add more</p>
    </div>
  )
}
