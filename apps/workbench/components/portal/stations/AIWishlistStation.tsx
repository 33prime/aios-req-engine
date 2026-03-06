'use client'

import { Sparkles } from 'lucide-react'

interface AIWishlistStationProps {
  tribalKnowledge: string[]
}

export function AIWishlistStation({ tribalKnowledge }: AIWishlistStationProps) {
  const wishes = tribalKnowledge
    .filter((t) => t.startsWith('[ai_wishlist]'))
    .map((t) => t.replace('[ai_wishlist] ', '').replace('[ai_wishlist]', ''))

  if (wishes.length === 0) {
    return (
      <div className="text-center py-4">
        <Sparkles className="w-6 h-6 text-text-placeholder mx-auto mb-2" />
        <p className="text-xs text-text-muted">No AI wishes added yet.</p>
        <p className="text-xs text-text-placeholder mt-1">Chat below to share what you'd love AI to automate.</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {wishes.map((w, i) => (
        <div key={i} className="bg-surface-subtle rounded-lg px-3 py-2 flex items-start gap-2">
          <Sparkles className="w-3.5 h-3.5 text-purple-500 flex-shrink-0 mt-0.5" />
          <p className="text-xs text-text-secondary">{w}</p>
        </div>
      ))}
      <p className="text-[10px] text-text-placeholder text-center pt-1">Chat below to add more</p>
    </div>
  )
}
