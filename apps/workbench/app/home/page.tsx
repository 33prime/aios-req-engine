'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import {
  Search,
  Calendar,
  ArrowRight,
  ListTodo,
  Globe,
  Inbox,
} from 'lucide-react'
import { formatDistanceToNow, isToday, isTomorrow, format } from 'date-fns'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { TaskListCompact } from '@/components/tasks'
import { ProjectAvatar } from '@/app/projects/components/ProjectAvatar'
import {
  listProjects,
  getMyProfile,
  listUpcomingMeetings,
  getNextActions,
  getCollaborationCurrent,
} from '@/lib/api'
import type {
  ProjectDetailWithDashboard,
  Profile,
  Meeting,
} from '@/types/api'
import type { NextAction, CollaborationCurrentResponse } from '@/lib/api'

// =============================================================================
// GreetingHeader
// =============================================================================

function GreetingHeader({
  profile,
  searchQuery,
  onSearchChange,
}: {
  profile: Profile | null
  searchQuery: string
  onSearchChange: (q: string) => void
}) {
  const hour = new Date().getHours()
  const timeOfDay = hour < 12 ? 'morning' : hour < 18 ? 'afternoon' : 'evening'
  const firstName = profile?.first_name || 'there'
  const today = format(new Date(), 'EEEE, MMM d')

  return (
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-lg font-semibold text-[#333]">
          Good {timeOfDay}, {firstName}
        </h1>
        <p className="text-xs text-[#999] mt-0.5">{today}</p>
      </div>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#999]" />
        <input
          type="text"
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="pl-9 pr-4 py-2 text-sm bg-white border border-[#E5E5E5] rounded-xl w-64 focus:outline-none focus:border-[#3FAF7A] transition-colors"
        />
      </div>
    </div>
  )
}

// =============================================================================
// QuickStats
// =============================================================================

function QuickStats({
  projectCount,
  meetingsToday,
  portalPending,
}: {
  projectCount: number
  meetingsToday: number
  portalPending: number
}) {
  const parts: string[] = []
  parts.push(`${projectCount} active project${projectCount !== 1 ? 's' : ''}`)
  parts.push(`${meetingsToday} meeting${meetingsToday !== 1 ? 's' : ''} today`)
  if (portalPending > 0) {
    parts.push(`${portalPending} portal item${portalPending !== 1 ? 's' : ''} pending`)
  }

  return (
    <p className="text-xs text-[#999] mt-1">{parts.join(' · ')}</p>
  )
}

// =============================================================================
// ProjectCard
// =============================================================================

const STAGE_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  prototype_refinement: 'Refinement',
  proposal: 'Proposal',
  build: 'Build',
  live: 'Live',
}

function ProjectCard({
  project,
  nextAction,
}: {
  project: ProjectDetailWithDashboard
  nextAction: NextAction | null
}) {
  const router = useRouter()
  const readiness = project.cached_readiness_data
  // Compute dimensional score (actual progress) instead of gate-capped score
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
  const stageLabel = STAGE_LABELS[project.stage] || project.stage

  return (
    <div
      onClick={() => router.push(`/projects/${project.id}`)}
      className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5 hover:shadow-lg cursor-pointer transition-shadow"
    >
      {/* Top row: avatar + name + stage */}
      <div className="flex items-start gap-3">
        <ProjectAvatar name={project.name} clientName={project.client_name} />
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-semibold text-[#333] truncate">
            {project.name}
          </p>
          {project.client_name && (
            <p className="text-[11px] text-[#999] truncate">{project.client_name}</p>
          )}
        </div>
        <span className="flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full bg-[#F0F0F0] text-[#666]">
          {stageLabel}
        </span>
      </div>

      {/* Readiness bar */}
      <div className="mt-3 flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
          <div
            className="h-full bg-[#3FAF7A] rounded-full transition-all"
            style={{ width: `${Math.min(score, 100)}%` }}
          />
        </div>
        <span className="text-[11px] text-[#666] tabular-nums">{Math.round(score)}%</span>
      </div>

      {/* Next action */}
      <div className="mt-3">
        {nextAction ? (
          <div className="flex items-center gap-1.5 text-[12px] text-[#3FAF7A]">
            <ArrowRight className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">{nextAction.title}</span>
          </div>
        ) : (
          <p className="text-[12px] text-[#999]">All caught up</p>
        )}
      </div>

      {/* Footer */}
      {project.updated_at && (
        <p className="text-[10px] text-[#999] mt-3">
          Updated {formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })}
        </p>
      )}
    </div>
  )
}

// =============================================================================
// PendingTasksSection
// =============================================================================

function PendingTasksSection({
  projects,
  activeProjectId,
  onTabChange,
}: {
  projects: ProjectDetailWithDashboard[]
  activeProjectId: string | null
  onTabChange: (id: string) => void
}) {
  if (projects.length === 0) return null

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
      <div className="flex items-center gap-2 mb-4">
        <ListTodo className="w-4 h-4 text-[#666]" />
        <h2 className="text-sm font-semibold text-[#333]">Pending Tasks</h2>
      </div>

      {/* Tab pills */}
      <div className="flex flex-wrap gap-1.5 mb-4">
        {projects.map((p) => (
          <button
            key={p.id}
            onClick={() => onTabChange(p.id)}
            className={`text-[11px] px-3 py-1 rounded-full transition-colors ${
              activeProjectId === p.id
                ? 'bg-[#E8F5E9] text-[#25785A] font-medium'
                : 'bg-[#F0F0F0] text-[#666] hover:bg-[#E5E5E5]'
            }`}
          >
            {p.name}
          </button>
        ))}
      </div>

      {/* Task list for active tab */}
      {activeProjectId && (
        <TaskListCompact
          projectId={activeProjectId}
          maxItems={5}
          filter="pending"
        />
      )}
    </div>
  )
}

// =============================================================================
// SchedulePanel
// =============================================================================

function SchedulePanel({ meetings }: { meetings: Meeting[] }) {
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

  const MEETING_TYPE_LABELS: Record<string, string> = {
    discovery: 'Discovery',
    validation: 'Validation',
    review: 'Review',
    other: 'Meeting',
  }

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
      <div className="flex items-center gap-2 mb-4">
        <Calendar className="w-4 h-4 text-[#666]" />
        <h2 className="text-sm font-semibold text-[#333]">Schedule</h2>
      </div>

      {grouped.length === 0 ? (
        <p className="text-xs text-[#999]">No upcoming meetings</p>
      ) : (
        <div className="space-y-4">
          {grouped.map((group) => (
            <div key={group.label}>
              <p className="text-[10px] text-[#999] font-medium uppercase tracking-wider mb-2">
                {group.label}
              </p>
              <div className="space-y-2">
                {group.items.map((m) => (
                  <div key={m.id} className="flex items-start gap-3">
                    <span className="text-[12px] font-medium text-[#333] w-16 flex-shrink-0">
                      {m.meeting_time ? format(new Date(`2000-01-01T${m.meeting_time}`), 'h:mm a') : '—'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-[#333] truncate">{m.title}</p>
                      {m.project_name && (
                        <p className="text-[11px] text-[#999] truncate">{m.project_name}</p>
                      )}
                    </div>
                    <span className="flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full bg-[#F0F0F0] text-[#666]">
                      {MEETING_TYPE_LABELS[m.meeting_type] || m.meeting_type}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// PortalNotificationsPanel
// =============================================================================

interface PortalInfo {
  projectId: string
  projectName: string
  pendingQuestions: number
  pendingDocuments: number
  lastActivity: string | null
}

function PortalNotificationsPanel({ portals }: { portals: PortalInfo[] }) {
  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
      <div className="flex items-center gap-2 mb-4">
        <Globe className="w-4 h-4 text-[#666]" />
        <h2 className="text-sm font-semibold text-[#333]">Client Portal</h2>
      </div>

      {portals.length === 0 ? (
        <div className="flex items-center gap-2 text-xs text-[#999]">
          <Inbox className="w-3.5 h-3.5" />
          <span>No client portals active</span>
        </div>
      ) : (
        <div className="space-y-3">
          {portals.map((p) => {
            const totalPending = p.pendingQuestions + p.pendingDocuments
            return (
              <div key={p.projectId} className="border-b border-[#F0F0F0] last:border-0 pb-2 last:pb-0">
                <p className="text-[12px] font-medium text-[#333]">{p.projectName}</p>
                {totalPending > 0 ? (
                  <p className="text-[11px] text-[#3FAF7A] mt-0.5">
                    {p.pendingQuestions > 0 && `${p.pendingQuestions} question${p.pendingQuestions !== 1 ? 's' : ''} pending`}
                    {p.pendingQuestions > 0 && p.pendingDocuments > 0 && ' · '}
                    {p.pendingDocuments > 0 && `${p.pendingDocuments} document${p.pendingDocuments !== 1 ? 's' : ''} pending`}
                  </p>
                ) : (
                  <p className="text-[11px] text-[#999] mt-0.5">Portal enabled, no pending items</p>
                )}
                {p.lastActivity && (
                  <p className="text-[10px] text-[#999] mt-0.5">
                    Active {formatDistanceToNow(new Date(p.lastActivity), { addSuffix: true })}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// HomeDashboard (main page)
// =============================================================================

export default function HomeDashboard() {
  const [projects, setProjects] = useState<ProjectDetailWithDashboard[]>([])
  const [profile, setProfile] = useState<Profile | null>(null)
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [nextActionsMap, setNextActionsMap] = useState<Record<string, NextAction | null>>({})
  const [portalSyncMap, setPortalSyncMap] = useState<Record<string, CollaborationCurrentResponse['portal_sync'] | null>>({})
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeTaskProject, setActiveTaskProject] = useState<string | null>(null)

  // Phase 1: load projects, profile, meetings in parallel
  useEffect(() => {
    async function load() {
      try {
        const [projectsRes, profileRes, meetingsRes] = await Promise.allSettled([
          listProjects('active'),
          getMyProfile(),
          listUpcomingMeetings(8),
        ])

        const loadedProjects =
          projectsRes.status === 'fulfilled' ? projectsRes.value.projects : []
        const loadedProfile =
          profileRes.status === 'fulfilled' ? profileRes.value : null
        const loadedMeetings =
          meetingsRes.status === 'fulfilled' ? meetingsRes.value : []

        setProjects(loadedProjects)
        setProfile(loadedProfile)
        setMeetings(loadedMeetings)

        if (loadedProjects.length > 0) {
          setActiveTaskProject(loadedProjects[0].id)
        }

        // Phase 2: per-project data (next actions + portal sync)
        const actionPromises = loadedProjects.map((p) =>
          getNextActions(p.id)
            .then((res) => ({ id: p.id, action: res.actions[0] ?? null }))
            .catch(() => ({ id: p.id, action: null }))
        )

        const portalProjects = loadedProjects.filter((p) => p.portal_enabled)
        const portalPromises = portalProjects.map((p) =>
          getCollaborationCurrent(p.id)
            .then((res) => ({ id: p.id, sync: res.portal_sync }))
            .catch(() => ({ id: p.id, sync: null }))
        )

        const [actionResults, portalResults] = await Promise.all([
          Promise.all(actionPromises),
          Promise.all(portalPromises),
        ])

        const actionsMap: Record<string, NextAction | null> = {}
        for (const r of actionResults) actionsMap[r.id] = r.action

        const syncMap: Record<string, CollaborationCurrentResponse['portal_sync'] | null> = {}
        for (const r of portalResults) syncMap[r.id] = r.sync

        setNextActionsMap(actionsMap)
        setPortalSyncMap(syncMap)
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  // Derived data
  const filteredProjects = useMemo(() => {
    if (!searchQuery.trim()) return projects
    const q = searchQuery.toLowerCase()
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        (p.client_name && p.client_name.toLowerCase().includes(q))
    )
  }, [projects, searchQuery])

  const meetingsToday = useMemo(
    () => meetings.filter((m) => isToday(new Date(m.meeting_date))).length,
    [meetings]
  )

  const portalInfos: PortalInfo[] = useMemo(() => {
    return Object.entries(portalSyncMap)
      .filter(([, sync]) => sync?.portal_enabled)
      .map(([projectId, sync]) => {
        const proj = projects.find((p) => p.id === projectId)
        return {
          projectId,
          projectName: proj?.name ?? 'Unknown',
          pendingQuestions: sync?.questions.pending ?? 0,
          pendingDocuments: sync?.documents.pending ?? 0,
          lastActivity: sync?.last_client_activity ?? null,
        }
      })
  }, [portalSyncMap, projects])

  const totalPortalPending = useMemo(
    () => portalInfos.reduce((sum, p) => sum + p.pendingQuestions + p.pendingDocuments, 0),
    [portalInfos]
  )

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (loading) {
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
            profile={profile}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
          <QuickStats
            projectCount={projects.length}
            meetingsToday={meetingsToday}
            portalPending={totalPortalPending}
          />

          <h2 className="text-sm font-semibold text-[#333] mt-5 mb-3">Your Projects</h2>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-start">
            {/* Left 2/3: Projects + Tasks */}
            <div className="lg:col-span-2 space-y-5">
              {/* Project cards */}
              <div>
                {filteredProjects.length === 0 ? (
                  <p className="text-xs text-[#999]">
                    {searchQuery ? 'No projects match your search' : 'No active projects'}
                  </p>
                ) : (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {filteredProjects.map((p) => (
                      <ProjectCard
                        key={p.id}
                        project={p}
                        nextAction={nextActionsMap[p.id] ?? null}
                      />
                    ))}
                  </div>
                )}
              </div>

              <PendingTasksSection
                projects={projects}
                activeProjectId={activeTaskProject}
                onTabChange={setActiveTaskProject}
              />
            </div>

            {/* Right 1/3: Schedule + Portal */}
            <div className="space-y-5">
              <SchedulePanel meetings={meetings} />
              <PortalNotificationsPanel portals={portalInfos} />
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
