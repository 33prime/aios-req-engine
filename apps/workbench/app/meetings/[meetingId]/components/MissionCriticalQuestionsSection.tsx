'use client'

import { MessageCircle } from 'lucide-react'
import type { MissionCriticalQuestion } from '@/types/call-intelligence'

export function MissionCriticalQuestionsSection({
  questions,
}: {
  questions: MissionCriticalQuestion[]
}) {
  if (!questions || questions.length === 0) return null

  return (
    <div className="mt-7">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5 mb-3">
        <MessageCircle className="w-3.5 h-3.5" /> Mission-Critical Questions
      </h3>
      <div className="space-y-2.5">
        {questions.map((q, i) => (
          <div key={i} className="p-3 bg-white rounded-lg border border-border">
            <p className="text-[13px] font-medium text-text-body leading-snug">{q.question}</p>
            <div className="flex items-center gap-2 mt-2">
              {q.target_stakeholder && (
                <span className="px-2 py-0.5 text-[11px] font-medium bg-blue-50 text-blue-700 rounded-full">
                  {q.target_stakeholder}
                </span>
              )}
            </div>
            {q.why_important && (
              <p className="mt-1.5 text-[11px] text-text-muted">{q.why_important}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
