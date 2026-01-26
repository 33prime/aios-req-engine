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
  AlertCircle,
  Sparkles,
  FileText,
  Target,
  Search,
  MessageSquare,
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
  proposal: { icon: FileText, label: 'Proposal', color: 'bg-blue-100 text-blue-700' },
  gap: { icon: AlertCircle, label: 'Gap', color: 'bg-amber-100 text-amber-700' },
  manual: { icon: CheckCircle, label: 'Manual', color: 'bg-gray-100 text-gray-700' },
  enrichment: { icon: Sparkles, label: 'Enrichment', color: 'bg-purple-100 text-purple-700' },
  validation: { icon: Target, label: 'Validation', color: 'bg-emerald-100 text-emerald-700' },
  research: { icon: Search, label: 'Research', color: 'bg-cyan-100 text-cyan-700' },
  collaboration: { icon: MessageSquare, label: 'Client', color: 'bg-pink-100 text-pink-700' },
}

const priorityConfig: Record<string, { color: string; label: string }> = {
  high: { color: 'text-red-600', label: 'High' },
  medium: { color: 'text-amber-600', label: 'Medium' },
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

  const typeConfig = taskTypeConfig[task.task_type] || taskTypeConfig.manual
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
        className={`flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group ${onViewDetails ? 'cursor-pointer' : ''}`}
        onClick={() => onViewDetails?.(task)}
      >
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleComplete()
          }}
          disabled={isCompleting}
          className="flex-shrink-0 w-5 h-5 rounded border-2 border-gray-300 hover:border-[#009b87] hover:bg-[#009b87]/10 transition-colors disabled:opacity-50"
          title="Complete task"
        >
          {isCompleting && (
            <span className="block w-full h-full animate-pulse bg-gray-200 rounded" />
          )}
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">{task.title}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={`text-xs px-1.5 py-0.5 rounded ${typeConfig.color}`}>
              {typeConfig.label}
            </span>
            {task.requires_client_input && (
              <span className="text-xs px-1.5 py-0.5 bg-pink-100 text-pink-700 rounded flex items-center gap-1">
                <User className="w-3 h-3" />
                Client
              </span>
            )}
          </div>
        </div>
        <span className={`text-xs font-medium ${priority.color}`}>
          {priority.label}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleDismiss()
          }}
          disabled={isDismissing}
          className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-gray-600 transition-all disabled:opacity-50"
          title="Dismiss task"
        >
          <X className="w-4 h-4" />
        </button>
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
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 bg-pink-100 text-pink-700 rounded">
                <User className="w-3 h-3" />
                Client Input
              </span>
            )}
            {task.gate_stage && (
              <span className="text-xs text-gray-500">
                Gate: {task.gate_stage.replace(/_/g, ' ')}
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
