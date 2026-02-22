'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  X,
  CheckCircle,
  ArrowUpRight,
  FileText,
  Bell,
  Calendar,
  Send,
  Eye,
  Package,
  Pen,
  Flag,
} from 'lucide-react'
import type { Task } from '@/lib/api'

interface QuickActionTaskModalProps {
  task: Task | null
  projectId: string
  onClose: () => void
  onComplete: (taskId: string) => Promise<void>
  onDismiss: (taskId: string) => Promise<void>
  onChanged?: () => void
}

const typeConfig: Record<string, { icon: typeof FileText; label: string; bg: string; text: string }> = {
  signal_review:  { icon: FileText, label: 'Signal Review',  bg: 'bg-[#3FAF7A]/10', text: 'text-[#25785A]' },
  action_item:    { icon: Send,     label: 'Action Item',    bg: 'bg-[#0A1E2F]/5',  text: 'text-[#0A1E2F]' },
  meeting_prep:   { icon: Calendar, label: 'Meeting Prep',   bg: 'bg-[#3FAF7A]/10', text: 'text-[#25785A]' },
  book_meeting:   { icon: Calendar, label: 'Book Meeting',   bg: 'bg-[#3FAF7A]/10', text: 'text-[#25785A]' },
  reminder:       { icon: Bell,     label: 'Reminder',       bg: 'bg-[#F4F4F4]',    text: 'text-[#666]' },
  review_request: { icon: Eye,      label: 'Review Request', bg: 'bg-[#3FAF7A]/10', text: 'text-[#25785A]' },
  deliverable:    { icon: Package,  label: 'Deliverable',    bg: 'bg-[#0A1E2F]/5',  text: 'text-[#0A1E2F]' },
  custom:         { icon: Pen,      label: 'Task',           bg: 'bg-[#F4F4F4]',    text: 'text-[#666]' },
}

const priorityColors: Record<string, string> = {
  high: '#25785A',
  medium: '#3FAF7A',
  low: '#E5E5E5',
  none: '#E5E5E5',
}

export function QuickActionTaskModal({
  task,
  projectId,
  onClose,
  onComplete,
  onDismiss,
  onChanged,
}: QuickActionTaskModalProps) {
  const router = useRouter()
  const [completing, setCompleting] = useState(false)
  const [dismissing, setDismissing] = useState(false)

  if (!task) return null

  const type = typeConfig[task.task_type] || typeConfig.custom
  const TypeIcon = type.icon
  let patchCount = 0
  if (task.patches_snapshot) {
    const snap = task.patches_snapshot as Record<string, unknown>
    const applied = snap.applied as unknown[] | undefined
    patchCount = applied?.length ?? (typeof snap.total === 'number' ? snap.total : 0)
  }

  const handleComplete = async () => {
    setCompleting(true)
    try {
      await onComplete(task.id)
      onChanged?.()
      onClose()
    } catch {
      setCompleting(false)
    }
  }

  const handleDismiss = async () => {
    setDismissing(true)
    try {
      await onDismiss(task.id)
      onChanged?.()
      onClose()
    } catch {
      setDismissing(false)
    }
  }

  const handleOpenDetail = () => {
    onClose()
    router.push(`/tasks/${task.id}`)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-start justify-between px-5 pt-5 pb-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[12px] font-medium rounded-md ${type.bg} ${type.text}`}>
              <TypeIcon className="w-3.5 h-3.5" />
              {type.label}
            </span>
            <div
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ backgroundColor: priorityColors[task.priority || 'none'] }}
              title={`${task.priority || 'none'} priority`}
            />
          </div>
          <button onClick={onClose} className="text-[#999] hover:text-[#333] transition-colors -mt-0.5">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 pb-4">
          <h3 className="text-[16px] font-semibold text-[#0A1E2F] leading-snug mb-1">
            {task.title}
          </h3>
          {task.description && (
            <p className="text-[13px] text-[#666] line-clamp-3 mb-3">
              {task.description}
            </p>
          )}

          {/* Type-specific info */}
          <div className="flex flex-wrap items-center gap-2 text-[12px] text-[#999] mb-4">
            {task.priority && task.priority !== 'none' && (
              <span className="flex items-center gap-1">
                <Flag className="w-3 h-3" style={{ color: priorityColors[task.priority] }} />
                <span className="capitalize">{task.priority}</span>
              </span>
            )}
            {task.meeting_date && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {new Date(task.meeting_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
              </span>
            )}
            {task.remind_at && (
              <span className="flex items-center gap-1">
                <Bell className="w-3 h-3" />
                {new Date(task.remind_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
              </span>
            )}
            {task.action_verb && (
              <span className="capitalize">{task.action_verb.replace(/_/g, ' ')}</span>
            )}
            {task.due_date && (
              <span>Due {new Date(task.due_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
            )}
          </div>

          {/* Signal review: patch summary */}
          {task.task_type === 'signal_review' && patchCount > 0 && (
            <div className="bg-[#F4F4F4] rounded-lg px-3 py-2 mb-4 flex items-center justify-between">
              <span className="text-[13px] text-[#333]">
                <span className="font-medium">{patchCount}</span> entities extracted
              </span>
              <button
                onClick={handleOpenDetail}
                className="text-[12px] font-medium text-[#3FAF7A] hover:text-[#25785A] transition-colors"
              >
                Review All
              </button>
            </div>
          )}

          {/* Review request: status */}
          {task.task_type === 'review_request' && task.review_status && (
            <div className="bg-[#F4F4F4] rounded-lg px-3 py-2 mb-4">
              <span className="text-[13px] text-[#333]">
                Status: <span className="font-medium capitalize">{task.review_status.replace(/_/g, ' ')}</span>
              </span>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-[#E5E5E5]">
          <button
            onClick={handleOpenDetail}
            className="flex items-center gap-1.5 text-[13px] font-medium text-[#3FAF7A] hover:text-[#25785A] transition-colors"
          >
            Open Full Detail
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={handleDismiss}
              disabled={dismissing}
              className="px-3 py-1.5 text-[13px] text-[#666] hover:text-[#333] hover:bg-[#F4F4F4] rounded-lg transition-colors disabled:opacity-40"
            >
              {dismissing ? 'Dismissing...' : 'Dismiss'}
            </button>
            <button
              onClick={handleComplete}
              disabled={completing}
              className="px-3 py-1.5 text-[13px] font-medium rounded-lg bg-[#3FAF7A] text-white hover:bg-[#25785A] disabled:opacity-40 transition-colors"
            >
              {completing ? (
                <span className="flex items-center gap-1.5">
                  <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Completing...
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <CheckCircle className="w-3.5 h-3.5" />
                  Complete
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
