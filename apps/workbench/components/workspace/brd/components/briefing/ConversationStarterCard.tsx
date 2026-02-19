'use client'

import { MessageSquare, FileText } from 'lucide-react'
import type { ConversationStarter } from '@/types/workspace'

interface ConversationStarterCardProps {
  starter: ConversationStarter
  onStartConversation: (starter: ConversationStarter) => void
}

export function ConversationStarterCard({
  starter,
  onStartConversation,
}: ConversationStarterCardProps) {
  return (
    <div className="px-4 py-3">
      <div
        className="bg-white rounded-2xl border border-[#E5E5E5] p-5 shadow-sm"
        style={{ borderLeft: '3px solid #3FAF7A' }}
      >
        {/* Hook — the "I noticed..." part */}
        <p className="text-[13px] font-semibold text-[#333333] leading-snug">
          {starter.hook}
        </p>

        {/* Body — why this matters */}
        <p className="text-[12px] text-[#666666] mt-2 leading-relaxed">
          {starter.body}
        </p>

        {/* Anchor chips — signal source labels */}
        {starter.anchors.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {starter.anchors.map((anchor, i) => (
              <span
                key={i}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F4F4F4] text-[10px] text-[#666666]"
                title={anchor.excerpt}
              >
                <FileText className="w-2.5 h-2.5" />
                {anchor.signal_label || anchor.signal_type}
              </span>
            ))}
          </div>
        )}

        {/* CTA — "Let's discuss" */}
        <button
          onClick={() => onStartConversation(starter)}
          className="w-full mt-4 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-[#3FAF7A] hover:bg-[#25785A] text-white text-[12px] font-medium transition-colors"
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Let&apos;s discuss
        </button>
      </div>
    </div>
  )
}
