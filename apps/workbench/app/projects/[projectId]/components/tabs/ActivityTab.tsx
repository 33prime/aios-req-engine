/**
 * ActivityTab Component
 *
 * Timeline view of all project activity from the activity_feed API
 */

'use client'

import { useState, useEffect } from 'react'
import { Card, CardHeader } from '@/components/ui'
import { Clock, CheckCircle, Sparkles, Zap, AlertCircle, RefreshCw, FileText, Users, GitBranch } from 'lucide-react'

interface Activity {
  id?: string
  aggregation_key?: string
  activity_type: string
  entity_type?: string
  entity_name?: string
  entity_names?: string[]
  count?: number
  summary?: string
  change_summary?: string
  latest_created_at?: string
  created_at?: string
  requires_action?: boolean
  change_details?: Record<string, any>
}

interface ActivityTabProps {
  projectId: string
}

export function ActivityTab({ projectId }: ActivityTabProps) {
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const [hours, setHours] = useState(72) // Default to 72 hours

  useEffect(() => {
    loadActivities()
  }, [projectId, hours])

  const loadActivities = async () => {
    try {
      setLoading(true)
      // Use the new activity feed API
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/projects/${projectId}/activity?hours=${hours}&aggregate=false&limit=100`
      )

      if (!response.ok) {
        throw new Error(`Failed to fetch activity: ${response.status}`)
      }

      const data = await response.json()
      setActivities(data.activities || [])
    } catch (error) {
      console.error('Failed to load activity:', error)
      setActivities([])
    } finally {
      setLoading(false)
    }
  }

  const getActivityIcon = (activity: Activity) => {
    // Icon based on activity_type from activity_feed table
    switch (activity.activity_type) {
      case 'auto_applied':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'user_applied':
        return <CheckCircle className="h-4 w-4 text-blue-600" />
      case 'needs_review':
        return <AlertCircle className="h-4 w-4 text-yellow-600" />
      case 'cascade_triggered':
        return <GitBranch className="h-4 w-4 text-purple-600" />
      case 'research_ingested':
        return <Sparkles className="h-4 w-4 text-blue-600" />
      case 'insight_created':
        return <Zap className="h-4 w-4 text-orange-600" />
      case 'entity_refreshed':
        return <RefreshCw className="h-4 w-4 text-gray-600" />
      case 'proposal_applied':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      default:
        return <Clock className="h-4 w-4 text-gray-500" />
    }
  }

  const getEntityIcon = (entityType: string | undefined) => {
    switch (entityType) {
      case 'feature':
        return <Zap className="h-3 w-3 text-blue-500" />
      case 'persona':
        return <Users className="h-3 w-3 text-purple-500" />
      case 'vp_step':
        return <GitBranch className="h-3 w-3 text-orange-500" />
      case 'business_driver':
        return <FileText className="h-3 w-3 text-green-500" />
      default:
        return null
    }
  }

  const getActivityDescription = (activity: Activity) => {
    // Use summary if aggregated, otherwise use change_summary
    if (activity.summary) {
      return activity.summary
    }
    if (activity.change_summary) {
      return activity.change_summary
    }

    // Fallback based on activity_type
    const entityLabel = activity.entity_name || activity.entity_type || 'item'
    switch (activity.activity_type) {
      case 'auto_applied':
        return `Auto-applied: ${entityLabel}`
      case 'user_applied':
        return `Applied: ${entityLabel}`
      case 'needs_review':
        return `Needs review: ${entityLabel}`
      case 'cascade_triggered':
        return `Cascade updated: ${entityLabel}`
      case 'research_ingested':
        return 'Research ingested'
      case 'insight_created':
        return `New insight: ${entityLabel}`
      case 'proposal_applied':
        return `Proposal applied: ${entityLabel}`
      default:
        return activity.activity_type || 'Activity'
    }
  }

  const getTimeAgo = (timestamp: string) => {
    const now = new Date()
    const past = new Date(timestamp)
    const diffMs = now.getTime() - past.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  const getActivityTimestamp = (activity: Activity): string => {
    return activity.created_at || activity.latest_created_at || new Date().toISOString()
  }

  const groupByDate = (activities: Activity[]) => {
    const groups: Record<string, Activity[]> = {}
    activities.forEach((activity) => {
      const timestamp = getActivityTimestamp(activity)
      const date = new Date(timestamp)
      const key = date.toDateString()
      if (!groups[key]) groups[key] = []
      groups[key].push(activity)
    })
    return groups
  }

  const grouped = groupByDate(activities)

  return (
    <div className="p-6">
      <Card>
        <CardHeader
          title={
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-brand-accent" />
                <span>Activity Feed</span>
              </div>
              <select
                value={hours}
                onChange={(e) => setHours(Number(e.target.value))}
                className="text-xs border border-ui-cardBorder rounded px-2 py-1"
              >
                <option value={24}>Last 24 hours</option>
                <option value={72}>Last 3 days</option>
                <option value={168}>Last week</option>
              </select>
            </div>
          }
          subtitle="Timeline of changes: features, personas, VP steps, PRD sections"
        />

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary mx-auto mb-3"></div>
            <p className="text-sm text-ui-supportText">Loading activity...</p>
          </div>
        ) : activities.length === 0 ? (
          <div className="text-center py-12 bg-ui-background rounded-lg border border-ui-cardBorder">
            <Clock className="h-12 w-12 text-ui-supportText mx-auto mb-3" />
            <p className="text-sm text-ui-bodyText mb-1">No activity yet</p>
            <p className="text-xs text-ui-supportText">
              Activity will appear here as you run agents and apply patches
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(grouped).map(([date, items]) => (
              <div key={date}>
                {/* Date header */}
                <div className="text-sm font-semibold text-ui-bodyText mb-3 sticky top-0 bg-white py-2">
                  {new Date(date).toDateString() === new Date().toDateString() ? 'Today' :
                   new Date(date).toDateString() === new Date(Date.now() - 86400000).toDateString() ? 'Yesterday' :
                   new Date(date).toLocaleDateString()}
                </div>

                {/* Timeline */}
                <div className="relative">
                  <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

                  <div className="space-y-4">
                    {items.map((activity, index) => (
                      <div key={activity.id || `${activity.aggregation_key}-${index}`} className="relative pl-10">
                        {/* Timeline dot */}
                        <div className={`absolute left-0 top-1 h-8 w-8 rounded-full border-4 border-white flex items-center justify-center ${
                          activity.requires_action ? 'bg-yellow-100' :
                          index === 0 && date === new Date().toDateString() ? 'bg-blue-100' : 'bg-gray-100'
                        }`}>
                          {getActivityIcon(activity)}
                        </div>

                        {/* Activity card */}
                        <div className={`bg-ui-background border rounded-lg p-3 ${
                          activity.requires_action ? 'border-yellow-300 bg-yellow-50' : 'border-ui-cardBorder'
                        }`}>
                          <div className="flex items-start justify-between mb-1">
                            <div className="flex items-center gap-2">
                              {getEntityIcon(activity.entity_type)}
                              <span className="text-sm font-medium text-ui-bodyText">
                                {getActivityDescription(activity)}
                              </span>
                              {activity.requires_action && (
                                <span className="text-xs bg-yellow-200 text-yellow-800 px-1.5 py-0.5 rounded">
                                  Needs Review
                                </span>
                              )}
                            </div>
                            <span className="text-xs text-ui-supportText whitespace-nowrap ml-2">
                              {getTimeAgo(getActivityTimestamp(activity))}
                            </span>
                          </div>

                          {/* Entity name if different from summary */}
                          {activity.entity_name && !activity.change_summary?.includes(activity.entity_name) && (
                            <div className="text-xs text-ui-supportText mt-1">
                              {activity.entity_type}: <span className="font-medium">{activity.entity_name}</span>
                            </div>
                          )}

                          {/* Show change details if available */}
                          {activity.change_details && Object.keys(activity.change_details).length > 0 && (
                            <div className="text-xs text-ui-supportText mt-1">
                              {activity.change_details.review_reason && (
                                <span>Reason: {activity.change_details.review_reason}</span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
