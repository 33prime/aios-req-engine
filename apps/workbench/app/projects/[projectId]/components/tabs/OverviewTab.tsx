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
  Users,
  Route,
  FileText,
  ChevronRight,
  AlertCircle
} from 'lucide-react'
import {
  getStatusNarrative,
  getProjectTasks,
  listMeetings,
  listUpcomingMeetings,
  getFeatures,
  getVpSteps,
  getPersonas
} from '@/lib/api'
import type { StatusNarrative, ProjectTask, Meeting } from '@/types/api'

interface OverviewTabProps {
  projectId: string
  isActive?: boolean
}

export function OverviewTab({ projectId, isActive = true }: OverviewTabProps) {
  const [statusNarrative, setStatusNarrative] = useState<StatusNarrative | null>(null)
  const [tasks, setTasks] = useState<ProjectTask[]>([])
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [stats, setStats] = useState({
    features: 0,
    personas: 0,
    vpSteps: 0,
  })
  const [loading, setLoading] = useState(true)
  const [regeneratingNarrative, setRegeneratingNarrative] = useState(false)

  useEffect(() => {
    if (isActive) {
      loadOverviewData()
    }
  }, [projectId, isActive])

  const loadOverviewData = async () => {
    try {
      setLoading(true)

      const [
        narrativeData,
        tasksData,
        meetingsData,
        featuresData,
        vpData,
        personasData,
      ] = await Promise.all([
        getStatusNarrative(projectId).catch(() => null),
        getProjectTasks(projectId).catch(() => ({ tasks: [] })),
        listMeetings(projectId, 'scheduled', true).catch(() => []),
        getFeatures(projectId).catch(() => []),
        getVpSteps(projectId).catch(() => []),
        getPersonas(projectId).catch(() => []),
      ])

      setStatusNarrative(narrativeData)
      setTasks(tasksData.tasks || [])
      setMeetings(Array.isArray(meetingsData) ? meetingsData : [])
      setStats({
        features: Array.isArray(featuresData) ? featuresData.length : 0,
        personas: Array.isArray(personasData) ? personasData.length : 0,
        vpSteps: Array.isArray(vpData) ? vpData.length : 0,
      })
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

  // Calculate readiness score
  const calculateReadiness = () => {
    let score = 0
    if (stats.features >= 3) score += 30
    else if (stats.features >= 1) score += 15
    if (stats.personas >= 2) score += 25
    else if (stats.personas >= 1) score += 12
    if (stats.vpSteps >= 3) score += 25
    else if (stats.vpSteps >= 1) score += 12
    // Base score for having a project
    score += 20
    return Math.min(score, 100)
  }

  const readinessScore = calculateReadiness()

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
          </div>

          {/* Score Circle */}
          <div className="flex justify-center mb-6">
            <div className="relative w-32 h-32">
              <svg className="w-full h-full transform -rotate-90">
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  fill="none"
                  stroke="#e5e7eb"
                  strokeWidth="12"
                />
                <circle
                  cx="64"
                  cy="64"
                  r="56"
                  fill="none"
                  stroke={readinessScore >= 75 ? '#10b981' : readinessScore >= 50 ? '#f59e0b' : '#ef4444'}
                  strokeWidth="12"
                  strokeLinecap="round"
                  strokeDasharray={`${(readinessScore / 100) * 352} 352`}
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-gray-900">{readinessScore}%</span>
                <span className="text-xs text-gray-500">complete</span>
              </div>
            </div>
          </div>

          {/* Breakdown */}
          <div className="space-y-3">
            <ReadinessItem
              icon={<FileText className="w-4 h-4" />}
              label="Features"
              count={stats.features}
              target={3}
            />
            <ReadinessItem
              icon={<Users className="w-4 h-4" />}
              label="Personas"
              count={stats.personas}
              target={2}
            />
            <ReadinessItem
              icon={<Route className="w-4 h-4" />}
              label="Value Path"
              count={stats.vpSteps}
              target={3}
            />
          </div>
        </div>
      </div>

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

function ReadinessItem({
  icon,
  label,
  count,
  target,
}: {
  icon: React.ReactNode
  label: string
  count: number
  target: number
}) {
  const isComplete = count >= target

  return (
    <div className="flex items-center gap-3">
      <div className={`p-1.5 rounded ${isComplete ? 'bg-emerald-100 text-emerald-600' : 'bg-gray-100 text-gray-400'}`}>
        {icon}
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-700">{label}</span>
          <span className={`text-sm font-medium ${isComplete ? 'text-emerald-600' : 'text-gray-500'}`}>
            {count}/{target}
          </span>
        </div>
        <div className="w-full h-1.5 bg-gray-200 rounded-full mt-1 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${isComplete ? 'bg-emerald-500' : 'bg-amber-500'}`}
            style={{ width: `${Math.min((count / target) * 100, 100)}%` }}
          />
        </div>
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
