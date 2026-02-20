'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import {
  Search,
  ArrowUpRight,
  CheckCircle2,
  ListTodo,
  Calendar,
  Inbox,
} from 'lucide-react'
import { formatDistanceToNow, isToday, isTomorrow, format } from 'date-fns'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { BuildingCardOverlay } from '@/app/projects/components/BuildingCardOverlay'
import { getCollaborationCurrent } from '@/lib/api'
import {
  useProfile,
  useProjects,
  useUpcomingMeetings,
  useCrossProjectTasks,
  useBatchDashboardData,
} from '@/lib/hooks/use-api'
import { useRealtimeDashboard } from '@/lib/realtime'
import type {
  ProjectDetailWithDashboard,
  Profile,
  Meeting,
} from '@/types/api'
import type { NextAction, Task, CollaborationCurrentResponse } from '@/lib/api'

// =============================================================================
// Constants
// =============================================================================

const STAGE_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  discovery:            { label: 'Discovery',  bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  validation:           { label: 'Validation', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  prototype:            { label: 'Prototype',  bg: 'bg-[#3FAF7A]', text: 'text-white' },
  prototype_refinement: { label: 'Refinement', bg: 'bg-[#3FAF7A]', text: 'text-white' },
  proposal:             { label: 'Proposal',   bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  build:                { label: 'Build',      bg: 'bg-[#0A1E2F]', text: 'text-white' },
  live:                 { label: 'Live',       bg: 'bg-[#0A1E2F]', text: 'text-white' },
}

const TASK_TYPE_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  proposal:      { label: 'Proposal',  bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  gap:           { label: 'Gap',       bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  manual:        { label: 'Manual',    bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  enrichment:    { label: 'Enrich',    bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  validation:    { label: 'Validate',  bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  research:      { label: 'Research',  bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  collaboration: { label: 'Client',    bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
}

const MAX_DASHBOARD_PROJECTS = 3
const SECTION_GAP = 16

// =============================================================================
// Greeting Header
// =============================================================================

function GreetingHeader({
  profile,
  projectCount,
  meetingsToday,
  taskCount,
}: {
  profile: Profile | null
  projectCount: number
  meetingsToday: number
  taskCount: number
}) {
  const firstName = profile?.first_name || 'there'
  const today = format(new Date(), 'EEEE, MMMM d')

  const stats: string[] = []
  stats.push(`${projectCount} project${projectCount !== 1 ? 's' : ''}`)
  stats.push(`${meetingsToday} meeting${meetingsToday !== 1 ? 's' : ''} today`)
  if (taskCount > 0) stats.push(`${taskCount} task${taskCount !== 1 ? 's' : ''} pending`)

  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h1 className="text-[22px] font-bold text-[#1D1D1F]">
          Daily Snapshot
        </h1>
        <p className="text-[14px] text-[#666] mt-1">
          Welcome back <span className="font-semibold text-[#333]">{firstName}</span>! Here&apos;s the latest for{' '}
          <span className="font-semibold text-[#333]">{today}</span>.
        </p>
        <p className="text-[12px] text-[#999] mt-1">{stats.join(' \u00B7 ')}</p>
      </div>
      <div className="flex items-center gap-2 mt-1">
        <button className="w-8 h-8 rounded-lg bg-white border border-[#E5E5E5] flex items-center justify-center text-[#999] hover:text-[#333] hover:border-[#ccc] transition-colors">
          <Search className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}

// =============================================================================
// Project Card (full-width, two-column body)
// =============================================================================

interface PortalInfo {
  pendingQuestions: number
  pendingDocuments: number
  lastActivity: string | null
  items: { text: string; dot: string; time: string }[]
}

function ProjectCard({
  project,
  nextActions,
  portal,
}: {
  project: ProjectDetailWithDashboard
  nextActions: NextAction[]
  portal: PortalInfo | null
}) {
  const router = useRouter()
  const isBuilding = project.launch_status === 'building'
  const stage = STAGE_CONFIG[project.stage] ?? { label: project.stage, bg: 'bg-[#F0F0F0]', text: 'text-[#666]' }
  const topActions = nextActions.slice(0, 2)

  // Compute readiness score
  const readiness = project.cached_readiness_data
  let score = 0
  if (readiness?.dimensions) {
    for (const key of Object.keys(readiness.dimensions)) {
      const d = readiness.dimensions[key]
      if (d && typeof d.score === 'number' && typeof d.weight === 'number') {
        score += d.score * d.weight
      }
    }
  } else {
    score = readiness?.gate_score ?? project.readiness_score ?? 0
  }

  return (
    <div
      onClick={() => router.push(`/projects/${project.id}`)}
      className={`bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.04)] border border-[#E5E5E5] hover:shadow-[0_4px_12px_rgba(0,0,0,0.08)] cursor-pointer transition-shadow relative overflow-hidden ${
        isBuilding ? 'border-[#3FAF7A]/30' : ''
      }`}
      style={{ padding: '20px' }}
    >
      {isBuilding && (
        <BuildingCardOverlay
          projectId={project.id}
          launchId={project.active_launch_id}
        />
      )}

      {/* Header: name + client + stage + readiness + arrow */}
      <div className={`flex items-start justify-between gap-3 ${isBuilding ? 'opacity-30 blur-sm' : ''}`}>
        <div className="flex-1 min-w-0">
          <p className="text-[16px] font-bold text-[#1D1D1F] truncate">{project.name}</p>
          {project.client_name && (
            <p className="text-[13px] text-[#666] truncate mt-0.5">{project.client_name}</p>
          )}
          <span className={`inline-block mt-2 text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${stage.bg} ${stage.text}`}>
            {isBuilding ? 'Building' : stage.label}
          </span>
        </div>

        {/* Readiness + arrow cluster */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {!isBuilding && (
            <div className="text-right">
              <p className="text-[12px] font-medium text-[#666]">Readiness: {Math.round(score)}%</p>
              <div className="w-24 h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden mt-1">
                <div
                  className="h-full bg-[#3FAF7A] rounded-full transition-all"
                  style={{ width: `${Math.min(score, 100)}%` }}
                />
              </div>
            </div>
          )}
          <div
            className="w-8 h-8 rounded-full bg-[#3FAF7A] flex items-center justify-center hover:scale-110 transition-transform"
            onClick={(e) => { e.stopPropagation(); router.push(`/projects/${project.id}`) }}
          >
            <ArrowUpRight className="w-4 h-4 text-white" />
          </div>
        </div>
      </div>

      {/* Two-column body: Next Steps | Client Updates */}
      {!isBuilding && (
        <div className="grid grid-cols-2 gap-4 mt-5">
          {/* Next Steps */}
          <div>
            <p className="text-[14px] font-bold text-[#1D1D1F] mb-3">
              Next Steps
            </p>
            {topActions.length > 0 ? (
              <div className="space-y-2.5">
                {topActions.map((a, i) => (
                  <div key={`${a.action_type}-${i}`} className="flex items-start gap-2.5">
                    <CheckCircle2 className="w-[18px] h-[18px] text-[#3FAF7A] flex-shrink-0 mt-px" />
                    <span className="text-[13px] text-[#333] leading-snug">{a.title}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-[#999]">All caught up</p>
            )}
          </div>

          {/* Client Updates */}
          <div className="border-l border-[#E5E5E5] pl-4">
            <p className="text-[14px] font-bold text-[#1D1D1F] mb-3">
              Client Updates
            </p>
            {portal && portal.items.length > 0 ? (
              <div className="space-y-2.5">
                {portal.items.map((item, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <div
                      className="w-[7px] h-[7px] rounded-full flex-shrink-0 mt-[6px]"
                      style={{ background: item.dot }}
                    />
                    <div className="min-w-0">
                      <p className="text-[13px] text-[#333] leading-snug">{item.text}</p>
                      {item.time && (
                        <p className="text-[11px] text-[#999] mt-0.5">{item.time}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-[#999]">No portal activity</p>
            )}
          </div>
        </div>
      )}

      {/* Updated timestamp */}
      {!isBuilding && project.updated_at && (
        <p className="text-[11px] text-[#999] mt-4">
          Updated {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
        </p>
      )}
    </div>
  )
}

// =============================================================================
// Global Tasks Panel (cross-project, right sidebar)
// =============================================================================

function GlobalTasksPanel({
  tasks,
  projectNameMap,
}: {
  tasks: Task[]
  projectNameMap: Record<string, string>
}) {
  const router = useRouter()

  function getPriorityColor(score: number): string {
    if (score >= 70) return '#25785A'  // dark green — high
    if (score >= 40) return '#3FAF7A'  // brand green — medium
    return '#E5E5E5'                    // light gray — low
  }

  return (
    <div className="bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.04)] border border-[#E5E5E5] p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[14px] font-bold text-[#1D1D1F] flex items-center gap-2">
          <ListTodo className="w-4 h-4 text-[#999]" />
          Tasks
        </h3>
        <span
          className="text-[12px] text-[#3FAF7A] font-medium cursor-pointer hover:underline"
          onClick={() => router.push('/tasks')}
        >
          View all
        </span>
      </div>

      {tasks.length === 0 ? (
        <div className="flex items-center gap-2 py-4 justify-center">
          <Inbox className="w-4 h-4 text-[#E5E5E5]" />
          <span className="text-[13px] text-[#999]">All caught up</span>
        </div>
      ) : (
        <div>
          {tasks.map((task) => {
            const typeConf = TASK_TYPE_CONFIG[task.task_type] ?? TASK_TYPE_CONFIG.manual
            const projectName = projectNameMap[task.project_id]
            const shortName = projectName
              ? projectName.length > 14 ? projectName.slice(0, 12) + '..' : projectName
              : ''

            return (
              <div
                key={task.id}
                className="flex items-center gap-2.5 py-2.5 border-b border-[#F0F0F0] last:border-b-0 cursor-pointer hover:bg-[#FAFAFA] -mx-1 px-1 rounded transition-colors"
                onClick={() => router.push('/tasks')}
              >
                <div
                  className="w-[3px] h-7 rounded-sm flex-shrink-0"
                  style={{ background: getPriorityColor(task.priority_score) }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-[13px] font-medium text-[#333] leading-snug truncate">
                    {task.title}
                  </p>
                  <div className="flex items-center gap-1.5 mt-1">
                    {shortName && (
                      <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-[#E8F5E9] text-[#25785A]">
                        {shortName}
                      </span>
                    )}
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${typeConf.bg} ${typeConf.text}`}>
                      {typeConf.label}
                    </span>
                    <span className="text-[10px] text-[#999]">
                      {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Schedule Panel (timeline dots)
// =============================================================================

function SchedulePanel({ meetings }: { meetings: Meeting[]; }) {
  const router = useRouter()
  const grouped = useMemo(() => {
    const groups: { label: string; items: Meeting[] }[] = []
    const buckets = new Map<string, Meeting[]>()

    for (const m of meetings) {
      const d = new Date(m.meeting_date)
      let label: string
      if (isToday(d)) label = 'TODAY'
      else if (isTomorrow(d)) label = 'TOMORROW'
      else label = format(d, 'EEE, MMM d').toUpperCase()

      if (!buckets.has(label)) buckets.set(label, [])
      buckets.get(label)!.push(m)
    }

    for (const [label, items] of buckets) {
      groups.push({ label, items })
    }
    return groups
  }, [meetings])

  return (
    <div className="bg-white rounded-2xl shadow-[0_1px_3px_rgba(0,0,0,0.04)] border border-[#E5E5E5] p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[14px] font-bold text-[#1D1D1F] flex items-center gap-2">
          <Calendar className="w-4 h-4 text-[#999]" />
          Schedule
        </h3>
        <span
          className="text-[12px] text-[#3FAF7A] font-medium cursor-pointer hover:underline"
          onClick={() => router.push('/meetings')}
        >
          View all
        </span>
      </div>

      {grouped.length === 0 ? (
        <div className="flex items-center gap-2 py-4 justify-center">
          <Calendar className="w-4 h-4 text-[#E5E5E5]" />
          <span className="text-[13px] text-[#999]">No upcoming meetings</span>
        </div>
      ) : (
        <div className="space-y-4">
          {grouped.map((group) => (
            <div key={group.label}>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-[#999] mb-2">
                {group.label}
              </p>
              <div className="space-y-0">
                {group.items.map((m, idx) => {
                  const isLast = idx === group.items.length - 1
                  return (
                    <div key={m.id} className="flex items-start gap-3 cursor-pointer hover:bg-[#FAFAFA] -mx-1 px-1 rounded transition-colors" onClick={() => router.push('/meetings')}>
                      {/* Timeline dot + line */}
                      <div className="flex flex-col items-center flex-shrink-0">
                        <div className="w-2 h-2 rounded-full bg-[#3FAF7A] mt-[5px]" />
                        {!isLast && <div className="w-px h-7 bg-[#E5E5E5]" />}
                      </div>
                      {/* Content */}
                      <div className={`flex-1 min-w-0 ${isLast ? '' : 'pb-2'}`}>
                        <div className="flex items-center gap-2">
                          <span className="text-[12px] font-semibold text-[#3FAF7A]">
                            {m.meeting_time
                              ? format(new Date(`2000-01-01T${m.meeting_time}`), 'h:mm a')
                              : '\u2014'}
                          </span>
                          <span className="text-[13px] text-[#333] truncate">{m.title}</span>
                        </div>
                        {m.project_name && (
                          <p className="text-[11px] text-[#999] mt-0.5 truncate">{m.project_name}</p>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Home Dashboard
// =============================================================================

export default function HomeDashboard() {
  const [portalSyncMap, setPortalSyncMap] = useState<Record<string, CollaborationCurrentResponse['portal_sync'] | null>>({})
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  useRealtimeDashboard()

  // Data hooks
  const { data: profile } = useProfile()
  const { data: projectsData, isLoading: projectsLoading, mutate: mutateProjects } = useProjects('active')
  const { data: meetingsData } = useUpcomingMeetings(8)

  const allProjects = projectsData?.projects ?? []
  const meetings = meetingsData ?? []

  // Sort projects by updated_at desc, take top 3
  const dashboardProjects = useMemo(() => {
    return [...allProjects]
      .sort((a, b) => {
        const aDate = a.updated_at ? new Date(a.updated_at).getTime() : 0
        const bDate = b.updated_at ? new Date(b.updated_at).getTime() : 0
        return bDate - aDate
      })
      .slice(0, MAX_DASHBOARD_PROJECTS)
  }, [allProjects])

  // Project name map for task pills
  const projectNameMap = useMemo(() => {
    const map: Record<string, string> = {}
    for (const p of allProjects) map[p.id] = p.name
    return map
  }, [allProjects])

  // Auto-poll when building
  const hasBuilding = useMemo(() => allProjects.some((p) => p.launch_status === 'building'), [allProjects])
  useEffect(() => {
    if (!hasBuilding) return
    const interval = setInterval(() => mutateProjects(), 8000)
    return () => clearInterval(interval)
  }, [hasBuilding, mutateProjects])

  // Per-project next best actions (batch endpoint — single POST instead of N calls)
  const projectIds = useMemo(() => allProjects.map((p) => p.id), [allProjects])
  const dashboardProjectIds = useMemo(
    () => dashboardProjects.map((p) => p.id),
    [dashboardProjects],
  )

  const { data: batchData } = useBatchDashboardData(
    dashboardProjectIds.length > 0 ? dashboardProjectIds : undefined,
  )
  const nextActionsMap = batchData?.next_actions ?? {}

  // Cross-project tasks
  const { data: globalTasks } = useCrossProjectTasks(
    projectIds.length > 0 ? projectIds : undefined,
    5,
  )

  // Portal sync per project
  useEffect(() => {
    const portalProjects = allProjects.filter((p) => p.portal_enabled)
    if (portalProjects.length === 0) return

    Promise.all(
      portalProjects.map((p) =>
        getCollaborationCurrent(p.id)
          .then((res) => ({ id: p.id, sync: res.portal_sync }))
          .catch(() => ({ id: p.id, sync: null }))
      )
    ).then((results) => {
      const syncMap: Record<string, CollaborationCurrentResponse['portal_sync'] | null> = {}
      for (const r of results) syncMap[r.id] = r.sync
      setPortalSyncMap(syncMap)
    })
  }, [allProjects])

  // Derive portal info per project
  const portalMap = useMemo(() => {
    const map: Record<string, PortalInfo> = {}
    for (const [projectId, sync] of Object.entries(portalSyncMap)) {
      if (!sync) {
        map[projectId] = { pendingQuestions: 0, pendingDocuments: 0, lastActivity: null, items: [{ text: 'No portal activity', dot: '#E5E5E5', time: '' }] }
        continue
      }
      const items: PortalInfo['items'] = []
      const pq = sync.questions?.pending ?? 0
      const pd = sync.documents?.pending ?? 0

      if (pq > 0) items.push({ text: `${pq} question${pq > 1 ? 's' : ''} pending`, dot: '#3FAF7A', time: '' })
      if (pd > 0) items.push({ text: `${pd} document${pd > 1 ? 's' : ''} pending`, dot: '#3FAF7A', time: '' })

      if (sync.last_client_activity) {
        const timeAgo = formatDistanceToNow(new Date(sync.last_client_activity), { addSuffix: true })
        if (items.length === 0) {
          items.push({ text: `Last active ${timeAgo}`, dot: '#E5E5E5', time: '' })
        } else {
          items[items.length - 1].time = timeAgo
        }
      }

      if (items.length === 0) {
        items.push({ text: 'No portal activity', dot: '#E5E5E5', time: '' })
      }

      map[projectId] = { pendingQuestions: pq, pendingDocuments: pd, lastActivity: sync.last_client_activity ?? null, items }
    }
    return map
  }, [portalSyncMap])

  // Stats
  const meetingsToday = useMemo(
    () => meetings.filter((m) => isToday(new Date(m.meeting_date))).length,
    [meetings]
  )

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  // Loading state
  if (projectsLoading) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#3FAF7A] mx-auto mb-3" />
            <p className="text-sm text-[#999]">Loading dashboard...</p>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <AppSidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div
        className="min-h-screen bg-[#F4F4F4] transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="max-w-[1400px] mx-auto px-6 py-5">
          <GreetingHeader
            profile={profile ?? null}
            projectCount={allProjects.length}
            meetingsToday={meetingsToday}
            taskCount={globalTasks?.length ?? 0}
          />

          {/* Main 2/3 + 1/3 grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 items-start" style={{ gap: `${SECTION_GAP}px` }}>

            {/* Left 2/3: Project Cards */}
            <div className="lg:col-span-2" style={{ display: 'flex', flexDirection: 'column', gap: `${SECTION_GAP}px` }}>
              <p className="text-[18px] font-bold text-[#1D1D1F]">
                Latest Projects
              </p>
              {dashboardProjects.length === 0 ? (
                <p className="text-[12px] text-[#999]">No active projects</p>
              ) : (
                dashboardProjects.map((p) => (
                  <ProjectCard
                    key={p.id}
                    project={p}
                    nextActions={nextActionsMap[p.id] ?? []}
                    portal={portalMap[p.id] ?? null}
                  />
                ))
              )}
            </div>

            {/* Right 1/3: Tasks + Schedule */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: `${SECTION_GAP}px` }}>
              {/* Spacer to match "Latest Projects" heading height */}
              <p className="text-[18px] font-bold text-[#1D1D1F]">
                Overview
              </p>
              <GlobalTasksPanel
                tasks={globalTasks ?? []}
                projectNameMap={projectNameMap}
              />
              <SchedulePanel meetings={meetings} />
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
