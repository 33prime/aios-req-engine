'use client'

import { Target } from 'lucide-react'
import type { CallGoal, GoalResult } from '@/types/call-intelligence'
import { GoalStatusBadge } from '@/components/call-intelligence'

export function CallGoalsSection({
  goals,
  results,
}: {
  goals: CallGoal[]
  results?: GoalResult[] | null
}) {
  if (!goals || goals.length === 0) return null

  return (
    <div className="mt-7">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5 mb-3">
        <Target className="w-3.5 h-3.5" /> Call Goals
      </h3>
      <div className="space-y-2.5">
        {goals.map((goal, i) => {
          const result = results?.find((r) => r.goal === goal.goal)
          return (
            <div key={i} className="p-3 bg-white rounded-lg border border-border">
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-start gap-2.5">
                  <span className="shrink-0 w-6 h-6 rounded-full bg-brand-primary-light text-brand-primary text-xs font-bold flex items-center justify-center mt-0.5">
                    {i + 1}
                  </span>
                  <div>
                    <p className="text-[13px] font-medium text-text-body leading-snug">{goal.goal}</p>
                    <p className="text-[11px] text-text-muted mt-1">Success: {goal.success_criteria}</p>
                  </div>
                </div>
                <GoalStatusBadge achieved={result?.achieved} />
              </div>
              {result?.evidence && (
                <p className="text-[11px] text-text-muted mt-2 pl-8 italic border-t border-border/50 pt-2">
                  {result.evidence}
                </p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
