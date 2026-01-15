/**
 * Overview Tab Component
 *
 * Clean dashboard showing:
 * - Status narrative (AI-generated "where we are" / "where we're going")
 * - Readiness score with breakdown
 * - System-generated tasks
 * - Activity feed
 * - Upcoming meetings
 */

'use client'

import { useState, useEffect } from 'react'
import {
  CheckCircle,
  Clock,
  Calendar,
  ArrowRight,
  RefreshCw,
  Sparkles,
  Target,
  ChevronRight,
  AlertCircle
} from 'lucide-react'
import {
  getStatusNarrative,
  getProjectTasks,
  listMeetings,
  getReadinessScore,
} from '@/lib/api'
import type { StatusNarrative, ProjectTask, Meeting } from '@/types/api'
import type { ReadinessScore, ReadinessRecommendation } from '@/lib/api'

interface OverviewTabProps {
  projectId: string
  isActive?: boolean
  /** Cached status narrative from project details */
  cachedNarrative?: StatusNarrative | null
  /** Full cached readiness data from project details */
  cachedReadinessData?: ReadinessScore | null
}

export function OverviewTab({
  projectId,
  isActive = true,
  cachedNarrative,
  cachedReadinessData,
}: OverviewTabProps) {
  // Use cached data for immediate display
  const [statusNarrative, setStatusNarrative] = useState<StatusNarrative | null>(cachedNarrative || null)
  const [tasks, setTasks] = useState<ProjectTask[]>([])
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [readiness, setReadiness] = useState<ReadinessScore | null>(cachedReadinessData || null)
  // Don't show loading spinner if we have cached data
  const [loading, setLoading] = useState(!cachedNarrative && !cachedReadinessData)
  const [regeneratingNarrative, setRegeneratingNarrative] = useState(false)

  useEffect(() => {
    if (isActive) {
      loadOverviewData()
    }
  }, [projectId, isActive])

  const loadOverviewData = async () => {
    try {
      // Only show loading if we have no cached data
      if (!cachedNarrative && !cachedReadinessData) {
        setLoading(true)
      }

      // Fetch tasks and meetings (always needed)
      const [tasksData, meetingsData] = await Promise.all([
        getProjectTasks(projectId).catch(() => ({ tasks: [] })),
        listMeetings(projectId, 'scheduled', true).catch(() => []),
      ])

      setTasks(tasksData?.tasks || [])
      setMeetings(Array.isArray(meetingsData) ? meetingsData : [])

      // Only fetch readiness if we don't have cached data
      if (!cachedReadinessData) {
        const readinessData = await getReadinessScore(projectId).catch(() => null)
        if (readinessData) setReadiness(readinessData)
      }

      // Only fetch narrative if we don't have it cached
      if (!cachedNarrative) {
        const narrativeData = await getStatusNarrative(projectId).catch(() => null)
        if (narrativeData) setStatusNarrative(narrativeData)
      }
    } catch (error) {
      console.error('Failed to load overview data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRegenerateNarrative = async () => {
    try {
      setRegeneratingNarrative(true)
      const data = await getStatusNarrative(projectId, true)
      setStatusNarrative(data)
    } catch (error) {
      console.error('Failed to regenerate narrative:', error)
    } finally {
      setRegeneratingNarrative(false)
    }
  }

  const readinessScore = readiness?.score ?? 0

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#009b87] mx-auto mb-3"></div>
          <p className="text-sm text-gray-500">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Top Row: Status + Readiness */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Status Narrative - Takes 2 columns */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#009b87]" />
              <h2 className="text-lg font-semibold text-gray-900">Status Overview</h2>
            </div>
            <button
              onClick={handleRegenerateNarrative}
              disabled={regeneratingNarrative}
              className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${regeneratingNarrative ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>

          {statusNarrative ? (
            <div className="space-y-4">
              <div className="bg-gray-50 rounded-lg p-4">
                <p className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                  Where we are today
                </p>
                <p className="text-gray-700 leading-relaxed">
                  {statusNarrative.where_today}
                </p>
              </div>

              <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-100">
                <p className="text-xs font-medium text-emerald-600 uppercase tracking-wide mb-2">
                  Where we're going
                </p>
                <p className="text-gray-700 leading-relaxed">
                  {statusNarrative.where_going}
                </p>
              </div>

              {statusNarrative.updated_at && (
                <p className="text-xs text-gray-400 text-right">
                  Last updated {new Date(statusNarrative.updated_at).toLocaleDateString()}
                </p>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <Sparkles className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">
                No status narrative yet. Click refresh to generate one.
              </p>
            </div>
          )}
        </div>

        {/* Readiness Score Card */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Target className="w-5 h-5 text-[#009b87]" />
            <h2 className="text-lg font-semibold text-gray-900">Readiness</h2>
            {readiness?.ready && (
              <span className="px-2 py-0.5 text-xs font-medium bg-emerald-100 text-emerald-700 rounded-full">
                Ready
              </span>
            )}
          </div>

          {/* Score Circle */}
          <div className="flex justify-center mb-4">
            <div className="relative w-28 h-28">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="56"
                  cy="56"
                  r="48"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="10"
                />
                <circle
                  cx="56"
                  cy="56"
                  r="48"
                  fill="none"
                  stroke={readinessScore >= 80 ? '#009b87' : readinessScore >= 50 ? '#34d399' : '#a7f3d0'}
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={`${(readinessScore / 100) * 301.6} 301.6`}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-2xl font-bold text-gray-900">{Math.round(readinessScore)}%</span>
                <span className="text-xs text-gray-500">{readiness?.threshold ?? 80}% needed</span>
              </div>
            </div>
          </div>

          {/* Caps Applied */}
          {readiness?.caps_applied && readiness.caps_applied.length > 0 && (
            <div className="mb-4 p-2 bg-gray-50 border border-gray-200 rounded-lg">
              <div className="flex items-center gap-1.5 text-gray-700 text-xs font-medium mb-1">
                <AlertCircle className="w-3.5 h-3.5" />
                Score Limited
              </div>
              {readiness.caps_applied.map((cap) => (
                <p key={cap.cap_id} className="text-xs text-gray-600">
                  {cap.reason} (max {cap.limit}%)
                </p>
              ))}
            </div>
          )}

          {/* Dimension Breakdown */}
          {readiness?.dimensions && (
            <div className="space-y-2 mb-4">
              <DimensionBar
                label="Value Path"
                score={readiness.dimensions.value_path?.score ?? 0}
                weight={35}
              />
              <DimensionBar
                label="Problem"
                score={readiness.dimensions.problem?.score ?? 0}
                weight={25}
              />
              <DimensionBar
                label="Solution"
                score={readiness.dimensions.solution?.score ?? 0}
                weight={25}
              />
              <DimensionBar
                label="Engagement"
                score={readiness.dimensions.engagement?.score ?? 0}
                weight={15}
              />
            </div>
          )}

          {/* Quick Stats - only show when full data loaded */}
          {readiness?.dimensions && (
            <div className="pt-3 border-t border-gray-100 grid grid-cols-2 gap-2 text-xs">
              <div className="text-gray-500">
                Confirmed: <span className="font-medium text-gray-700">{readiness.confirmed_entities ?? 0}/{readiness.total_entities ?? 0}</span>
              </div>
              <div className="text-gray-500">
                Client signals: <span className="font-medium text-gray-700">{readiness.client_signals_count ?? 0}</span>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recommendations Row */}
      {readiness?.top_recommendations && readiness.top_recommendations.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <ArrowRight className="w-5 h-5 text-[#009b87]" />
            <h2 className="text-lg font-semibold text-gray-900">Next Actions</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {readiness.top_recommendations.slice(0, 3).map((rec, idx) => (
              <RecommendationCard key={idx} recommendation={rec} />
            ))}
          </div>
        </div>
      )}

      {/* Bottom Row: Tasks + Meetings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tasks */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-[#009b87]" />
              <h2 className="text-lg font-semibold text-gray-900">Tasks</h2>
              {tasks.length > 0 && (
                <span className="px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded-full">
                  {tasks.length}
                </span>
              )}
            </div>
          </div>

          {tasks.length > 0 ? (
            <div className="space-y-3">
              {tasks.slice(0, 5).map((task) => (
                <TaskItem key={task.id} task={task} />
              ))}
              {tasks.length > 5 && (
                <button className="w-full py-2 text-sm text-gray-500 hover:text-gray-700 text-center">
                  +{tasks.length - 5} more tasks
                </button>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <CheckCircle className="w-10 h-10 text-green-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">All caught up! No pending tasks.</p>
            </div>
          )}
        </div>

        {/* Upcoming Meetings */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-[#009b87]" />
              <h2 className="text-lg font-semibold text-gray-900">Upcoming Meetings</h2>
            </div>
          </div>

          {meetings.length > 0 ? (
            <div className="space-y-3">
              {meetings.slice(0, 4).map((meeting) => (
                <MeetingItem key={meeting.id} meeting={meeting} />
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <Calendar className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 text-sm">No upcoming meetings scheduled.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Helper Components

function DimensionBar({
  label,
  score,
  weight,
}: {
  label: string
  score: number
  weight: number
}) {
  // Green gradient: darker teal for high scores, lighter for lower
  const getColor = (s: number) => {
    if (s >= 80) return 'bg-[#009b87]'
    if (s >= 50) return 'bg-emerald-400'
    return 'bg-emerald-200'
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-600 w-20 truncate">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${getColor(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs font-medium text-gray-700 w-10 text-right">{Math.round(score)}%</span>
      <span className="text-xs text-gray-400 w-8">({weight}%)</span>
    </div>
  )
}

function RecommendationCard({ recommendation }: { recommendation: ReadinessRecommendation }) {
  const effortColors = {
    low: 'bg-emerald-100 text-emerald-700',
    medium: 'bg-gray-100 text-gray-700',
    high: 'bg-gray-200 text-gray-700',
  }

  const dimensionLabels: Record<string, string> = {
    value_path: 'Value Path',
    problem: 'Problem',
    solution: 'Solution',
    engagement: 'Engagement',
  }

  return (
    <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
      <p className="text-sm text-gray-900 mb-2">{recommendation.action}</p>
      <div className="flex items-center gap-2 text-xs">
        <span className="text-emerald-600 font-medium">{recommendation.impact}</span>
        <span className={`px-1.5 py-0.5 rounded ${effortColors[recommendation.effort]}`}>
          {recommendation.effort}
        </span>
        {recommendation.dimension && (
          <span className="text-gray-400">
            {dimensionLabels[recommendation.dimension] || recommendation.dimension}
          </span>
        )}
      </div>
    </div>
  )
}

function TaskItem({ task }: { task: ProjectTask }) {
  const priorityColors = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-gray-100 text-gray-600',
  }

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
      <div className="mt-0.5">
        <div className="w-5 h-5 rounded border-2 border-gray-300" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{task.title}</p>
        {task.description && (
          <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{task.description}</p>
        )}
      </div>
      <span className={`px-2 py-0.5 text-xs font-medium rounded ${priorityColors[task.priority]}`}>
        {task.priority}
      </span>
    </div>
  )
}

function MeetingItem({ meeting }: { meeting: Meeting }) {
  const meetingTypeColors: Record<string, string> = {
    discovery: 'bg-emerald-100 text-emerald-700',
    validation: 'bg-blue-100 text-blue-700',
    review: 'bg-purple-100 text-purple-700',
    other: 'bg-gray-100 text-gray-700',
  }

  const formatMeetingDate = (dateStr: string, timeStr: string) => {
    try {
      const date = new Date(dateStr)
      const [hours, minutes] = timeStr.split(':')
      let hour = parseInt(hours, 10)
      const ampm = hour >= 12 ? 'PM' : 'AM'
      hour = hour % 12 || 12
      return {
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        time: `${hour}:${minutes} ${ampm}`,
      }
    } catch {
      return { date: dateStr, time: timeStr }
    }
  }

  const { date, time } = formatMeetingDate(meeting.meeting_date, meeting.meeting_time)

  return (
    <div className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
      <div className="flex flex-col items-center justify-center w-12 h-12 bg-white rounded-lg border border-gray-200">
        <span className="text-xs text-gray-500">{date.split(' ')[0]}</span>
        <span className="text-lg font-bold text-gray-900">{date.split(' ')[1]}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{meeting.title}</p>
        <div className="flex items-center gap-2 mt-1">
          <Clock className="w-3 h-3 text-gray-400" />
          <span className="text-xs text-gray-500">{time}</span>
          <span className={`px-1.5 py-0.5 text-xs font-medium rounded ${meetingTypeColors[meeting.meeting_type] || meetingTypeColors.other}`}>
            {meeting.meeting_type}
          </span>
        </div>
      </div>
      <ChevronRight className="w-4 h-4 text-gray-400" />
    </div>
  )
}
