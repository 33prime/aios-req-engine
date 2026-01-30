/**
 * OverviewPanel - Dashboard view for project readiness and status
 *
 * Layout:
 *   Top row (2/3 + 1/3): Status Narrative | Readiness Score
 *   Second row (3 equal): Tasks | Next Actions | Meetings
 */

'use client'

import { useState, useEffect } from 'react'
import {
  Sparkles,
  Target,
  RefreshCw,
  CheckCircle,
  Clock,
  AlertCircle,
  Calendar,
  ListTodo,
  Lightbulb,
} from 'lucide-react'
import { TaskListCompact } from '@/components/tasks'
import {
  getTaskStats,
  listMeetings,
  getStatusNarrative,
} from '@/lib/api'
import type { Meeting, StatusNarrative } from '@/types/api'
import type { CanvasData } from '@/types/workspace'
import type { ReadinessScore, ReadinessRecommendation, TaskStatsResponse } from '@/lib/api'

interface OverviewPanelProps {
  projectId: string
  canvasData: CanvasData
  readinessData: ReadinessScore | null
  narrativeData: StatusNarrative | null
  onNavigateToPhase: (phase: 'discovery' | 'build') => void
}

const DIMENSION_CONFIG: Record<string, { label: string; weight: number }> = {
  value_path: { label: 'Value Path', weight: 35 },
  problem: { label: 'Problem', weight: 25 },
  solution: { label: 'Solution', weight: 25 },
  engagement: { label: 'Engagement', weight: 15 },
}

export function OverviewPanel({
  projectId,
  canvasData,
  readinessData,
  narrativeData,
  onNavigateToPhase,
}: OverviewPanelProps) {
  const [taskStats, setTaskStats] = useState<TaskStatsResponse | null>(null)
  const [taskRefreshKey, setTaskRefreshKey] = useState(0)
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [localNarrative, setLocalNarrative] = useState<StatusNarrative | null>(narrativeData)
  const [regenerating, setRegenerating] = useState(false)

  const score = readinessData?.score ?? canvasData.readiness_score ?? 0
  const roundedScore = Math.round(score)

  // Sync prop changes
  useEffect(() => {
    setLocalNarrative(narrativeData)
  }, [narrativeData])

  // Fetch tasks stats + meetings internally
  useEffect(() => {
    const load = async () => {
      const [stats, mtgs] = await Promise.all([
        getTaskStats(projectId).catch(() => null),
        listMeetings(projectId, 'scheduled', true).catch(() => []),
      ])
      setTaskStats(stats)
      setMeetings(Array.isArray(mtgs) ? mtgs : [])
    }
    load()
  }, [projectId])

  const handleRegenerateNarrative = async () => {
    setRegenerating(true)
    try {
      const fresh = await getStatusNarrative(projectId, true)
      if (fresh) setLocalNarrative(fresh)
    } catch {
      // ignore
    } finally {
      setRegenerating(false)
    }
  }

  const pendingCount = taskStats?.by_status?.pending ?? 0

  const barColor =
    roundedScore >= 80
      ? 'bg-[#009b87]'
      : roundedScore >= 50
        ? 'bg-emerald-400'
        : 'bg-emerald-200'

  return (
    <div className="space-y-4">
      {/* Row 1: Status Narrative (2/3) + Readiness (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Status Narrative */}
        <div className="lg:col-span-2 bg-white rounded-card border border-ui-cardBorder shadow-card p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-brand-teal" />
              <h2 className="text-xs font-semibold text-ui-headingDark">Status Overview</h2>
            </div>
            <button
              onClick={handleRegenerateNarrative}
              disabled={regenerating}
              className="p-1 rounded-md text-ui-supportText hover:bg-ui-background hover:text-ui-headingDark transition-colors disabled:opacity-50"
              title="Regenerate narrative"
            >
              <RefreshCw className={`w-3 h-3 ${regenerating ? 'animate-spin' : ''}`} />
            </button>
          </div>

          {localNarrative ? (
            <div className="space-y-3">
              <div className="bg-gray-50 rounded-lg p-3">
                <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wide mb-1.5">
                  Where we are today
                </p>
                <p className="text-xs text-gray-700 leading-relaxed">
                  {localNarrative.where_today}
                </p>
              </div>

              <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-100">
                <p className="text-[10px] font-medium text-emerald-600 uppercase tracking-wide mb-1.5">
                  Where we&apos;re going
                </p>
                <p className="text-xs text-gray-700 leading-relaxed">
                  {localNarrative.where_going}
                </p>
              </div>

              {localNarrative.updated_at && (
                <p className="text-[10px] text-gray-400 text-right">
                  Last updated {new Date(localNarrative.updated_at).toLocaleDateString()}
                </p>
              )}
            </div>
          ) : (
            <div className="text-center py-6">
              <Sparkles className="w-8 h-8 text-gray-300 mx-auto mb-2" />
              <p className="text-xs text-gray-500">
                No status narrative yet. Click refresh to generate one.
              </p>
            </div>
          )}
        </div>

        {/* Readiness Card */}
        <div className="bg-white rounded-card border border-ui-cardBorder shadow-card p-4">
          {/* Header row with inline progress bar */}
          <div className="flex items-center gap-2 mb-3">
            <Target className="w-3.5 h-3.5 text-brand-teal flex-shrink-0" />
            <h2 className="text-xs font-semibold text-ui-headingDark">Readiness</h2>
            {readinessData?.ready && (
              <span className="flex items-center gap-0.5 text-[10px] font-medium text-emerald-600 bg-emerald-50 px-1.5 py-px rounded-full">
                <CheckCircle className="w-2.5 h-2.5" />
                Ready
              </span>
            )}
            <div className="flex-1" />
            <div className="flex items-center gap-1.5">
              <div className="w-16 h-1 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${barColor}`}
                  style={{ width: `${Math.min(score, 100)}%` }}
                />
              </div>
              <span className="text-[11px] font-semibold text-gray-700 tabular-nums">
                {roundedScore}%
              </span>
            </div>
          </div>

          {/* Caps Applied warning — green-tinted */}
          {readinessData?.caps_applied && readinessData.caps_applied.length > 0 && (
            <div className="bg-emerald-50 border border-emerald-200 rounded-md px-2.5 py-1.5 mb-3">
              <div className="flex items-start gap-1.5">
                <AlertCircle className="w-3 h-3 text-emerald-600 mt-px flex-shrink-0" />
                <div>
                  <p className="text-[10px] font-medium text-emerald-800">Score Limited</p>
                  {readinessData.caps_applied.map((cap, i) => (
                    <p key={i} className="text-[10px] text-emerald-700 leading-snug">
                      Capped at {cap.limit}% — {cap.reason}
                    </p>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Dimension bars */}
          {readinessData?.dimensions && (
            <div className="space-y-2">
              {Object.entries(readinessData.dimensions).map(([key, dim]: [string, any]) => {
                const config = DIMENSION_CONFIG[key]
                if (!config) return null
                const dimScore = Math.round(dim.score ?? 0)
                return (
                  <DimensionBar
                    key={key}
                    label={config.label}
                    score={dimScore}
                    weight={config.weight}
                  />
                )
              })}
            </div>
          )}

          {/* Footer stats */}
          <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-gray-100">
            <span className="text-[10px] text-gray-500">
              Confirmed: {readinessData?.confirmed_entities ?? 0}/{readinessData?.total_entities ?? 0}
            </span>
            <span className="text-[10px] text-gray-500">
              Client signals: {readinessData?.client_signals_count ?? 0}
            </span>
          </div>
        </div>
      </div>

      {/* Row 2: Tasks | Next Actions | Meetings */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Tasks */}
        <div className="bg-white rounded-card border border-ui-cardBorder shadow-card p-4 overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5">
              <ListTodo className="w-3.5 h-3.5 text-brand-teal" />
              <h2 className="text-xs font-semibold text-ui-headingDark">Tasks</h2>
            </div>
            {pendingCount > 0 && (
              <span className="text-[10px] font-medium text-emerald-700 bg-emerald-50 px-1.5 py-px rounded-full">
                {pendingCount} pending
              </span>
            )}
          </div>
          <div className="overflow-hidden [&_label]:text-xs [&_span]:text-[11px] [&_p]:text-xs [&_.task-card]:p-2">
            <TaskListCompact
              projectId={projectId}
              maxItems={3}
              filter="pending"
              refreshKey={taskRefreshKey}
              onTasksChange={() => {
                setTaskRefreshKey((k) => k + 1)
                getTaskStats(projectId).then(setTaskStats).catch(() => {})
              }}
            />
          </div>
        </div>

        {/* Next Actions */}
        <div className="bg-white rounded-card border border-ui-cardBorder shadow-card p-4">
          <div className="flex items-center gap-1.5 mb-3">
            <Lightbulb className="w-3.5 h-3.5 text-brand-teal" />
            <h2 className="text-xs font-semibold text-ui-headingDark">Next Actions</h2>
          </div>
          {readinessData?.top_recommendations && readinessData.top_recommendations.length > 0 ? (
            <div className="space-y-2">
              {readinessData.top_recommendations.slice(0, 3).map((rec, idx) => (
                <RecommendationCard key={idx} recommendation={rec} />
              ))}
            </div>
          ) : (
            <div className="text-center py-5">
              <Lightbulb className="w-6 h-6 text-gray-300 mx-auto mb-1.5" />
              <p className="text-[10px] text-gray-500">No recommendations yet.</p>
            </div>
          )}
        </div>

        {/* Meetings */}
        <div className="bg-white rounded-card border border-ui-cardBorder shadow-card p-4">
          <div className="flex items-center gap-1.5 mb-3">
            <Calendar className="w-3.5 h-3.5 text-brand-teal" />
            <h2 className="text-xs font-semibold text-ui-headingDark">Upcoming Meetings</h2>
          </div>
          {meetings.length > 0 ? (
            <div className="space-y-2">
              {meetings.slice(0, 3).map((meeting) => (
                <MeetingItem key={meeting.id} meeting={meeting} />
              ))}
            </div>
          ) : (
            <div className="text-center py-5">
              <Calendar className="w-6 h-6 text-gray-300 mx-auto mb-1.5" />
              <p className="text-[10px] text-gray-500">No upcoming meetings.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function DimensionBar({
  label,
  score,
  weight,
}: {
  label: string
  score: number
  weight: number
}) {
  const getColor = (s: number) => {
    if (s >= 80) return 'bg-[#009b87]'
    if (s >= 50) return 'bg-emerald-400'
    return 'bg-emerald-200'
  }

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] text-gray-600 w-16 truncate">{label}</span>
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${getColor(score)}`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-[10px] font-medium text-gray-700 w-8 text-right">{score}%</span>
      <span className="text-[10px] text-gray-400 w-7">({weight}%)</span>
    </div>
  )
}

function RecommendationCard({ recommendation }: { recommendation: ReadinessRecommendation }) {
  const effortColors: Record<string, string> = {
    low: 'bg-emerald-100 text-emerald-700',
    medium: 'bg-emerald-50 text-emerald-600',
    high: 'bg-emerald-200 text-emerald-800',
  }

  const dimensionLabels: Record<string, string> = {
    value_path: 'Value Path',
    problem: 'Problem',
    solution: 'Solution',
    engagement: 'Engagement',
  }

  return (
    <div className="p-2 bg-gray-50 rounded-md border border-gray-100">
      <p className="text-[11px] text-gray-900 mb-1 leading-snug">{recommendation.action}</p>
      <div className="flex items-center gap-1.5 text-[10px]">
        <span className="text-emerald-600 font-medium">{recommendation.impact}</span>
        <span className={`px-1 py-px rounded ${effortColors[recommendation.effort] || effortColors.medium}`}>
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

function MeetingItem({ meeting }: { meeting: Meeting }) {
  const meetingTypeColors: Record<string, string> = {
    discovery: 'bg-emerald-100 text-emerald-700',
    validation: 'bg-emerald-50 text-emerald-600',
    review: 'bg-teal-50 text-teal-700',
    other: 'bg-gray-100 text-gray-600',
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
    <div className="flex items-center gap-2.5 p-2 bg-gray-50 rounded-md hover:bg-gray-100 transition-colors">
      <div className="flex flex-col items-center justify-center w-9 h-9 bg-white rounded-md border border-gray-200">
        <span className="text-[9px] text-gray-500 leading-tight">{date.split(' ')[0]}</span>
        <span className="text-sm font-bold text-gray-900 leading-tight">{date.split(' ')[1]}</span>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-medium text-gray-900 truncate">{meeting.title}</p>
        <div className="flex items-center gap-1.5 mt-0.5">
          <Clock className="w-2.5 h-2.5 text-gray-400" />
          <span className="text-[10px] text-gray-500">{time}</span>
          <span
            className={`px-1 py-px text-[10px] font-medium rounded ${
              meetingTypeColors[meeting.meeting_type] || meetingTypeColors.other
            }`}
          >
            {meeting.meeting_type}
          </span>
        </div>
      </div>
    </div>
  )
}

export default OverviewPanel
