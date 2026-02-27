/**
 * TaskCard Component
 *
 * Displays a single task with inline actions for completion/dismissal.
 * Shows task type, priority, anchored entity, and source information.
 */

'use client'

import { useState } from 'react'
import {
  CheckCircle,
  X,
  Clock,
  Link2,
  ChevronRight,
  User,
  FileText,
  Bell,
  Calendar,
  Send,
  Eye,
  Package,
  Pen,
} from 'lucide-react'
import type { Task } from '@/lib/api'

interface TaskCardProps {
  task: Task
  onComplete: (taskId: string, notes?: string) => Promise<void>
  onDismiss: (taskId: string, reason?: string) => Promise<void>
  onNavigate?: (entityType: string, entityId: string) => void
  onViewDetails?: (task: Task) => void
  compact?: boolean
}

const taskTypeConfig: Record<string, { icon: typeof CheckCircle; label: string; color: string }> = {
  signal_review: { icon: FileText, label: 'Review', color: 'bg-emerald-50 text-emerald-700' },
  action_item: { icon: Send, label: 'Action', color: 'bg-brand-primary-light text-[#25785A]' },
  meeting_prep: { icon: Calendar, label: 'Prep', color: 'bg-[#0A1E2F]/5 text-[#0A1E2F]' },
  reminder: { icon: Bell, label: 'Reminder', color: 'bg-gray-100 text-gray-700' },
  review_request: { icon: Eye, label: 'Review', color: 'bg-emerald-100 text-emerald-700' },
  book_meeting: { icon: Calendar, label: 'Meeting', color: 'bg-[#0A1E2F]/5 text-[#0A1E2F]' },
  deliverable: { icon: Package, label: 'Deliverable', color: 'bg-brand-primary-light text-[#25785A]' },
  custom: { icon: Pen, label: 'Task', color: 'bg-gray-100 text-gray-700' },
}

const priorityConfig: Record<string, { color: string; label: string }> = {
  high: { color: 'text-emerald-800', label: 'High' },
  medium: { color: 'text-emerald-600', label: 'Medium' },
  low: { color: 'text-gray-500', label: 'Low' },
}

function getPriorityLevel(score: number): 'high' | 'medium' | 'low' {
  if (score >= 70) return 'high'
  if (score >= 40) return 'medium'
  return 'low'
}

export function TaskCard({
  task,
  onComplete,
  onDismiss,
  onNavigate,
  onViewDetails,
  compact = false,
}: TaskCardProps) {
  const [isCompleting, setIsCompleting] = useState(false)
  const [isDismissing, setIsDismissing] = useState(false)

  const typeConfig = taskTypeConfig[task.task_type] || taskTypeConfig.custom
  const TypeIcon = typeConfig.icon
  const priorityLevel = getPriorityLevel(task.priority_score)
  const priority = priorityConfig[priorityLevel]

  const handleComplete = async () => {
    setIsCompleting(true)
    try {
      await onComplete(task.id)
    } finally {
      setIsCompleting(false)
    }
  }

  const handleDismiss = async () => {
    setIsDismissing(true)
    try {
      await onDismiss(task.id)
    } finally {
      setIsDismissing(false)
    }
  }

  const handleNavigate = () => {
    if (task.anchored_entity_type && task.anchored_entity_id && onNavigate) {
      onNavigate(task.anchored_entity_type, task.anchored_entity_id)
    }
  }

  if (compact) {
    return (
      <div
        className={`p-2 bg-gray-50 rounded-md border border-gray-100 hover:bg-gray-100 transition-colors ${onViewDetails ? 'cursor-pointer' : ''}`}
        onClick={() => onViewDetails?.(task)}
      >
        <p className="text-[11px] font-medium text-gray-900 mb-1 leading-snug truncate">{task.title}</p>
        <div className="flex items-center gap-1.5 text-[10px]">
          <span className={`px-1 py-px rounded ${typeConfig.color}`}>
            {typeConfig.label}
          </span>
          <span className={`font-medium ${priority.color}`}>
            {priority.label}
          </span>
          {task.requires_client_input && (
            <span className="px-1 py-px bg-teal-100 text-teal-700 rounded">
              Client
            </span>
          )}
        </div>
      </div>
    )
  }

  const handleCardClick = () => {
    if (onViewDetails) {
      onViewDetails(task)
    }
  }

  return (
    <div
      className={`border border-gray-200 rounded-lg p-4 bg-white hover:shadow-sm transition-shadow ${onViewDetails ? 'cursor-pointer' : ''}`}
      onClick={handleCardClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Type badge and priority */}
          <div className="flex items-center gap-2 mb-2">
            <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded ${typeConfig.color}`}>
              <TypeIcon className="w-3 h-3" />
              {typeConfig.label}
            </span>
            {task.requires_client_input && (
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-teal-100 text-teal-700 rounded">
                <User className="w-3 h-3" />
                Client Input
              </span>
            )}
            {task.action_verb && (
              <span className="text-xs text-gray-500 capitalize">
                {task.action_verb.replace(/_/g, ' ')}
              </span>
            )}
          </div>

          {/* Title */}
          <h4 className="font-medium text-gray-900">{task.title}</h4>

          {/* Description */}
          {task.description && (
            <p className="text-sm text-gray-600 mt-1 line-clamp-2">{task.description}</p>
          )}

          {/* Anchored entity link */}
          {task.anchored_entity_type && task.anchored_entity_id && onNavigate && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                handleNavigate()
              }}
              className="mt-2 inline-flex items-center gap-1 text-sm text-[#009b87] hover:text-[#007a6a] transition-colors"
            >
              <Link2 className="w-3.5 h-3.5" />
              View {task.anchored_entity_type}
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Meta info */}
          <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
            <span className={`font-medium ${priority.color}`}>
              {priority.label} Priority
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {new Date(task.created_at).toLocaleDateString()}
            </span>
            {task.source_type && task.source_type !== 'manual' && (
              <span className="capitalize">
                Source: {task.source_type.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={handleComplete}
            disabled={isCompleting}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-[#009b87] hover:bg-[#007a6a] rounded-lg transition-colors disabled:opacity-50"
          >
            {isCompleting ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <CheckCircle className="w-4 h-4" />
            )}
            Complete
          </button>
          <button
            onClick={handleDismiss}
            disabled={isDismissing}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            {isDismissing ? (
              <span className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
            ) : (
              <X className="w-4 h-4" />
            )}
            Dismiss
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * TaskCardSkeleton - Loading placeholder
 */
export function TaskCardSkeleton({ compact = false }: { compact?: boolean }) {
  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg animate-pulse">
        <div className="w-5 h-5 bg-gray-200 rounded" />
        <div className="flex-1">
          <div className="h-4 bg-gray-200 rounded w-3/4" />
          <div className="h-3 bg-gray-200 rounded w-1/4 mt-1" />
        </div>
      </div>
    )
  }

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white animate-pulse">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <div className="h-5 bg-gray-200 rounded w-20" />
          </div>
          <div className="h-5 bg-gray-200 rounded w-3/4" />
          <div className="h-4 bg-gray-200 rounded w-1/2 mt-2" />
          <div className="flex items-center gap-4 mt-3">
            <div className="h-3 bg-gray-200 rounded w-16" />
            <div className="h-3 bg-gray-200 rounded w-24" />
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <div className="h-8 bg-gray-200 rounded w-24" />
          <div className="h-8 bg-gray-200 rounded w-24" />
        </div>
      </div>
    </div>
  )
}
