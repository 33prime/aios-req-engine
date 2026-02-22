'use client'

import { useState } from 'react'
import { Zap, CheckCircle, Send, Calendar, ChevronDown, ChevronRight, ArrowRight, AlertCircle, FileQuestion, Upload } from 'lucide-react'
import { useCollaborationCurrent, useUpcomingMeetings, useClientPulse } from '@/lib/hooks/use-api'

interface ActionQueueSectionProps {
  projectId: string
  onScrollToSection?: (sectionId: string) => void
}

interface ActionItem {
  id: string
  label: string
  type: 'client' | 'consultant' | 'system'
  icon: typeof CheckCircle
  cta: string
  targetSection: string
}

export function ActionQueueSection({ projectId, onScrollToSection }: ActionQueueSectionProps) {
  const [isOpen, setIsOpen] = useState(true)
  const { data: collab } = useCollaborationCurrent(projectId)
  const { data: meetings } = useUpcomingMeetings(5)
  const { data: pulse } = useClientPulse(projectId)

  const actions: ActionItem[] = []

  // Entities marked "needs review" waiting to be packaged → scroll to Question Board
  const reviewCount = collab?.pending_review_count ?? 0
  if (reviewCount > 0) {
    actions.push({
      id: 'needs-review',
      label: `${reviewCount} item${reviewCount > 1 ? 's' : ''} marked for client review — ready to package`,
      type: 'consultant',
      icon: FileQuestion,
      cta: 'Package & Send',
      targetSection: 'collab-questions',
    })
  }

  // Client answers waiting for review → scroll to Question Board
  // Use pulse unread_count (answered package questions) OR portal_sync fallback
  const answeredCount = pulse?.unread_count ?? collab?.portal_sync?.questions?.completed ?? 0
  if (answeredCount > 0) {
    actions.push({
      id: 'client-answers',
      label: `${answeredCount} client answer${answeredCount > 1 ? 's' : ''} waiting for review`,
      type: 'client',
      icon: CheckCircle,
      cta: 'View Answers',
      targetSection: 'collab-questions',
    })
  }

  // Questions ready to push → scroll to Question Board
  const pendingQuestions = collab?.portal_sync?.questions?.pending ?? 0
  if (pendingQuestions > 0) {
    actions.push({
      id: 'push-questions',
      label: `${pendingQuestions} question${pendingQuestions > 1 ? 's' : ''} ready to push to portal`,
      type: 'consultant',
      icon: Send,
      cta: 'Review & Send',
      targetSection: 'collab-questions',
    })
  }

  // Upcoming meeting prep → scroll to Agenda Center
  const projectMeetings = meetings?.filter(m => m.project_id === projectId && m.status === 'scheduled') ?? []
  if (projectMeetings.length > 0) {
    const next = projectMeetings[0]
    actions.push({
      id: 'meeting-prep',
      label: `Prepare for "${next.title}" — ${formatMeetingDate(next.meeting_date)}`,
      type: 'system',
      icon: Calendar,
      cta: 'View Agenda',
      targetSection: 'collab-agenda',
    })
  }

  // Pending validation items → scroll to Activity
  const validationCount = collab?.pending_validation_count ?? 0
  if (validationCount > 0) {
    actions.push({
      id: 'validation',
      label: `${validationCount} item${validationCount > 1 ? 's' : ''} pending client validation`,
      type: 'consultant',
      icon: AlertCircle,
      cta: 'View Items',
      targetSection: 'collab-activity',
    })
  }

  const count = actions.length

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-[0_1px_2px_rgba(0,0,0,0.04)] overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-[#FAFAFA] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Zap className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[11px] uppercase tracking-wider text-[#999999] font-semibold">
            Action Queue
          </span>
          {count > 0 && (
            <span className="px-1.5 py-0.5 bg-[#3FAF7A]/10 text-[#25785A] text-[10px] font-bold rounded-full min-w-[18px] text-center">
              {count}
            </span>
          )}
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-[#999999]" /> : <ChevronRight className="w-4 h-4 text-[#999999]" />}
      </button>

      {isOpen && (
        <div className="px-5 pb-4 space-y-2">
          {actions.length === 0 ? (
            <p className="text-[12px] text-[#999999] py-2">All caught up — no pending actions.</p>
          ) : (
            actions.map(action => {
              const Icon = action.icon
              const borderColor = action.type === 'client'
                ? 'border-l-[#3FAF7A]'
                : action.type === 'consultant'
                  ? 'border-l-[#0A1E2F]'
                  : 'border-l-[#E5E5E5]'

              return (
                <div
                  key={action.id}
                  onClick={() => onScrollToSection?.(action.targetSection)}
                  className={`border-l-[3px] ${borderColor} rounded-lg p-3 bg-[#F9F9F9] hover:bg-[#F4F4F4] transition-colors cursor-pointer`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Icon className="w-4 h-4 text-[#666666] flex-shrink-0" />
                      <span className="text-sm text-[#333333] truncate">{action.label}</span>
                    </div>
                    <span className="text-[12px] font-medium text-[#3FAF7A] flex items-center gap-1 flex-shrink-0">
                      {action.cta}
                      <ArrowRight className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}

function formatMeetingDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)

  const isToday = date.toDateString() === now.toDateString()
  const isTomorrow = date.toDateString() === tomorrow.toDateString()

  if (isToday) return 'Today'
  if (isTomorrow) return 'Tomorrow'
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}
