/**
 * TaskActivityFeed Component
 *
 * Displays recent task activity (completions, dismissals, creations).
 * Used in the Overview tab to show task history.
 */

'use client'

import { useState, useEffect } from 'react'
import {
  CheckCircle,
  XCircle,
  PlusCircle,
  RefreshCw,
  Clock,
  Bot,
  User,
} from 'lucide-react'
import { getProjectTaskActivity } from '@/lib/api'
import { formatRelativeTime } from '@/lib/date-utils'
import type { TaskActivity } from '@/lib/api'

interface TaskActivityFeedProps {
  projectId: string
  maxItems?: number
  refreshKey?: number
}

const actionConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string; bgColor: string }> = {
  created: { icon: PlusCircle, label: 'Created', color: 'text-blue-600', bgColor: 'bg-blue-50' },
  completed: { icon: CheckCircle, label: 'Completed', color: 'text-green-600', bgColor: 'bg-green-50' },
  dismissed: { icon: XCircle, label: 'Dismissed', color: 'text-gray-500', bgColor: 'bg-gray-50' },
  updated: { icon: RefreshCw, label: 'Updated', color: 'text-amber-600', bgColor: 'bg-amber-50' },
  reopened: { icon: RefreshCw, label: 'Reopened', color: 'text-purple-600', bgColor: 'bg-purple-50' },
}

const actorLabels: Record<string, { label: string; icon: typeof User }> = {
  user: { label: 'You', icon: User },
  system: { label: 'System', icon: Bot },
  ai: { label: 'AI Assistant', icon: Bot },
}

export function TaskActivityFeed({
  projectId,
  maxItems = 10,
  refreshKey,
}: TaskActivityFeedProps) {
  const [activities, setActivities] = useState<TaskActivity[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadActivity()
  }, [projectId, refreshKey])

  const loadActivity = async () => {
    try {
      setLoading(true)
      const result = await getProjectTaskActivity(projectId, { limit: maxItems })
      setActivities(result.activities)
    } catch (error) {
      console.error('Failed to load task activity:', error)
      setActivities([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map(i => (
          <div key={i} className="flex items-start gap-3 animate-pulse">
            <div className="w-8 h-8 bg-gray-200 rounded-full" />
            <div className="flex-1">
              <div className="h-4 bg-gray-200 rounded w-3/4" />
              <div className="h-3 bg-gray-200 rounded w-1/4 mt-1" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (activities.length === 0) {
    return (
      <div className="text-center py-6">
        <Clock className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-sm text-gray-500">No recent task activity</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {activities.map(activity => {
        const config = actionConfig[activity.action] || actionConfig.updated
        const Icon = config.icon
        const actorConfig = actorLabels[activity.actor_type] || actorLabels.system
        const ActorIcon = actorConfig.icon

        return (
          <div key={activity.id} className="flex items-start gap-3 group">
            <div className={`w-8 h-8 rounded-full flex items-center justify-center ${config.bgColor} ${config.color}`}>
              <Icon className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-gray-900">
                <span className="font-medium">{config.label}</span>
                {activity.note && (
                  <span className="text-gray-600"> — {activity.note}</span>
                )}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="flex items-center gap-1 text-xs text-gray-500">
                  <ActorIcon className="w-3 h-3" />
                  {actorConfig.label}
                </span>
                <span className="text-gray-300">·</span>
                <span className="text-xs text-gray-400">
                  {formatRelativeTime(activity.created_at)}
                </span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
