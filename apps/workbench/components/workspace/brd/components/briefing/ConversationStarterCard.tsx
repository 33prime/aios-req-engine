'use client'

import { ChevronRight, FileText } from 'lucide-react'
import type { ConversationStarter } from '@/types/workspace'
import { STARTER_ACTION_ICONS, STARTER_ACTION_LABELS } from '@/lib/action-constants'

interface ConversationStarterCardProps {
  starter: ConversationStarter
  onStartConversation: (starter: ConversationStarter) => void
}

/**
 * Render hook text with **bold** and *italic* markdown fragments.
 * Only supports single-level bold/italic — no nesting.
 */
function renderHook(hook: string) {
  // Split on **bold** and *italic* markers
  const parts: Array<{ text: string; style: 'normal' | 'bold' | 'italic' }> = []
  let remaining = hook

  while (remaining.length > 0) {
    // Check for **bold** first
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/)
    const italicMatch = remaining.match(/\*(.+?)\*/)

    // Find earliest match
    const boldIdx = boldMatch?.index ?? Infinity
    const italicIdx = italicMatch?.index ?? Infinity

    if (boldIdx === Infinity && italicIdx === Infinity) {
      // No more markers
      parts.push({ text: remaining, style: 'normal' })
      break
    }

    if (boldIdx <= italicIdx) {
      // Bold comes first
      if (boldIdx > 0) {
        parts.push({ text: remaining.slice(0, boldIdx), style: 'normal' })
      }
      parts.push({ text: boldMatch![1], style: 'bold' })
      remaining = remaining.slice(boldIdx + boldMatch![0].length)
    } else {
      // Italic comes first
      if (italicIdx > 0) {
        parts.push({ text: remaining.slice(0, italicIdx), style: 'normal' })
      }
      parts.push({ text: italicMatch![1], style: 'italic' })
      remaining = remaining.slice(italicIdx + italicMatch![0].length)
    }
  }

  return (
    <>
      {parts.map((p, i) => {
        if (p.style === 'bold') return <strong key={i} className="font-semibold">{p.text}</strong>
        if (p.style === 'italic') return <em key={i} className="italic text-[#666666]">{p.text}</em>
        return <span key={i}>{p.text}</span>
      })}
    </>
  )
}

export function ConversationStarterCard({
  starter,
  onStartConversation,
}: ConversationStarterCardProps) {
  const ActionIcon = STARTER_ACTION_ICONS[starter.action_type]
  const actionLabel = STARTER_ACTION_LABELS[starter.action_type]
  const anchorLabel = starter.anchors[0]?.signal_label || starter.anchors[0]?.signal_type || ''

  return (
    <button
      onClick={() => onStartConversation(starter)}
      className="w-full text-left flex items-start gap-3 px-3 py-3 border-b border-[#F0F0F0] last:border-b-0 hover:bg-[#FAFAFA] transition-colors group"
    >
      {/* Action type icon */}
      <div className="w-7 h-7 rounded-lg bg-[#F4F4F4] group-hover:bg-[#E8F5E9] flex items-center justify-center flex-shrink-0 mt-0.5 transition-colors">
        <ActionIcon className="w-3.5 h-3.5 text-[#999999] group-hover:text-[#3FAF7A] transition-colors" />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-[13px] text-[#333333] leading-snug pr-4">
          {renderHook(starter.hook)}
        </p>

        {/* Bottom: source chip + action label + arrow */}
        <div className="flex items-center gap-2 mt-1.5">
          {anchorLabel && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F4F4F4] text-[10px] text-[#999999]">
              <FileText className="w-2.5 h-2.5" />
              {anchorLabel}
            </span>
          )}
          <span className="text-[10px] font-medium text-[#BBBBBB] uppercase tracking-wide">
            {actionLabel}
          </span>
          <div className="flex-1" />
          <ChevronRight className="w-3.5 h-3.5 text-[#E5E5E5] group-hover:text-[#3FAF7A] transition-colors flex-shrink-0" />
        </div>
      </div>
    </button>
  )
}
