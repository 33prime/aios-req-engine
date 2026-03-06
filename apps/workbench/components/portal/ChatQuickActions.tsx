'use client'

import { CheckCircle, Pencil, Phone } from 'lucide-react'

interface ChatQuickActionsProps {
  consultantName?: string
  onClearedUp: () => void
  onAlmost: () => void
  onTalkTo: () => void
}

export function ChatQuickActions({
  consultantName,
  onClearedUp,
  onAlmost,
  onTalkTo,
}: ChatQuickActionsProps) {
  return (
    <div className="flex gap-2 px-4 py-2">
      <button
        onClick={onClearedUp}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-brand-primary-light text-brand-primary border border-brand-primary/20 hover:border-brand-primary/40 transition-colors"
      >
        <CheckCircle className="w-3.5 h-3.5" />
        Cleared up
      </button>
      <button
        onClick={onAlmost}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-surface-subtle text-text-primary border border-border hover:border-text-muted/30 transition-colors"
      >
        <Pencil className="w-3.5 h-3.5" />
        Almost
      </button>
      <button
        onClick={onTalkTo}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-accent/10 text-accent border border-accent/20 hover:border-accent/40 transition-colors"
      >
        <Phone className="w-3.5 h-3.5" />
        Talk to {consultantName || 'consultant'}
      </button>
    </div>
  )
}

const ESCALATION_PHRASE = "saved it for your discovery call"

export function isEscalationMessage(content: string): boolean {
  return content.toLowerCase().includes(ESCALATION_PHRASE) ||
    content.toLowerCase().includes("saved it for your call")
}
