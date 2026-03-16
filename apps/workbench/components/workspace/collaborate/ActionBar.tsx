'use client'

import { CheckCircle, Send, Calendar, AlertCircle, FileQuestion, ArrowRight } from 'lucide-react'
import { useCollaborationCurrent, useUpcomingMeetings, useClientPulse, usePendingItems } from '@/lib/hooks/use-api'

interface ActionBarProps {
  projectId: string
  onTriggerSynthesize?: () => void
}

interface AlertItem {
  id: string
  label: string
  urgent: boolean
  icon: typeof CheckCircle
  cta: string
  priority: number
  action?: () => void
}

export function ActionBar({ projectId, onTriggerSynthesize }: ActionBarProps) {
  const { data: collab } = useCollaborationCurrent(projectId)
  const { data: meetings } = useUpcomingMeetings(5)
  const { data: pulse } = useClientPulse(projectId)
  const { data: pending } = usePendingItems(projectId)

  const alerts: AlertItem[] = []

  // Priority 1: Client answers waiting (they took action — respond fast)
  const answeredCount = pulse?.unread_count ?? collab?.portal_sync?.questions?.completed ?? 0
  if (answeredCount > 0) {
    alerts.push({
      id: 'client-answers',
      label: `${answeredCount} client answer${answeredCount > 1 ? 's' : ''} waiting for review`,
      urgent: true,
      icon: CheckCircle,
      cta: 'Review',
      priority: 1,
    })
  }

  // Priority 2: Items ready to package
  const reviewCount = pending?.count ?? collab?.pending_review_count ?? 0
  if (reviewCount > 0) {
    alerts.push({
      id: 'needs-review',
      label: `${reviewCount} item${reviewCount > 1 ? 's' : ''} ready to package for client`,
      urgent: false,
      icon: FileQuestion,
      cta: 'Package',
      priority: 2,
      action: onTriggerSynthesize,
    })
  }

  // Priority 3: Meeting within 24h
  const projectMeetings = meetings?.filter(m => m.project_id === projectId && m.status === 'scheduled') ?? []
  if (projectMeetings.length > 0) {
    const next = projectMeetings[0]
    const meetingDate = new Date(next.meeting_date)
    const hoursUntil = (meetingDate.getTime() - Date.now()) / (1000 * 60 * 60)
    if (hoursUntil <= 24 && hoursUntil > 0) {
      alerts.push({
        id: 'meeting-prep',
        label: `"${next.title}" — ${formatMeetingDate(next.meeting_date)}`,
        urgent: false,
        icon: Calendar,
        cta: 'Prepare',
        priority: 3,
      })
    }
  }

  // Priority 4: Pending validation items
  const validationCount = collab?.pending_validation_count ?? 0
  if (validationCount > 0) {
    alerts.push({
      id: 'validation',
      label: `${validationCount} item${validationCount > 1 ? 's' : ''} pending client validation`,
      urgent: false,
      icon: AlertCircle,
      cta: 'View',
      priority: 4,
    })
  }

  // Priority 5: Questions ready to push
  const pendingQuestions = collab?.portal_sync?.questions?.pending ?? 0
  if (pendingQuestions > 0) {
    alerts.push({
      id: 'push-questions',
      label: `${pendingQuestions} question${pendingQuestions > 1 ? 's' : ''} ready to push to portal`,
      urgent: false,
      icon: Send,
      cta: 'Send',
      priority: 5,
    })
  }

  // Sort by priority, take max 2
  const topAlerts = alerts.sort((a, b) => a.priority - b.priority).slice(0, 2)

  if (topAlerts.length === 0) return null

  return (
    <div className="flex flex-col gap-2">
      {topAlerts.map(alert => {
        const Icon = alert.icon
        return (
          <div
            key={alert.id}
            onClick={alert.action}
            className={`flex items-center justify-between gap-3 rounded-xl px-4 py-2.5 border-l-[3px] ${
              alert.urgent
                ? 'border-l-brand-primary bg-brand-primary-light'
                : 'border-l-border bg-surface-muted'
            } ${alert.action ? 'cursor-pointer hover:bg-[#F4F4F4] transition-colors' : ''}`}
          >
            <div className="flex items-center gap-2.5 min-w-0">
              <Icon className={`w-4 h-4 flex-shrink-0 ${alert.urgent ? 'text-brand-primary' : 'text-[#666666]'}`} />
              <span className="text-[13px] text-text-body truncate">{alert.label}</span>
            </div>
            <span className="text-[12px] font-medium text-brand-primary flex items-center gap-1 flex-shrink-0">
              {alert.cta}
              <ArrowRight className="w-3 h-3" />
            </span>
          </div>
        )
      })}
    </div>
  )
}

function formatMeetingDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const tomorrow = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)

  if (date.toDateString() === now.toDateString()) return 'Today'
  if (date.toDateString() === tomorrow.toDateString()) return 'Tomorrow'
  return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })
}
