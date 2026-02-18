import React, { useMemo } from 'react'
import { formatDistanceToNow, isToday, isTomorrow } from 'date-fns'
import {
  ArrowRight,
  ListTodo,
  CalendarDays,
  CheckCircle2,
  Settings,
} from 'lucide-react'
import type { ProjectDetailWithDashboard, Profile, Meeting } from '@/types/api'
import type { NextAction, TaskStatsResponse } from '@/lib/api'
import { ACTION_ICONS } from '@/lib/action-constants'
import { ProjectAvatar } from './ProjectAvatar'
import { UserAvatar } from './UserAvatar'
import { ReadinessCell } from './ReadinessCell'
import { StageAdvancePopover } from './StageAdvancePopover'

interface ProjectsCardsProps {
  projects: ProjectDetailWithDashboard[]
  ownerProfiles: Record<string, { first_name?: string; last_name?: string; photo_url?: string }>
  currentUser: Profile | null
  nextActionsMap: Record<string, NextAction | null>
  taskStatsMap: Record<string, TaskStatsResponse | null>
  meetings: Meeting[]
  onProjectClick: (projectId: string) => void
  onRefresh?: () => void
}

const STAGE_LABELS: Record<string, string> = {
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  prototype_refinement: 'Refinement',
  proposal: 'Proposal',
  build: 'Build',
  live: 'Live',
}

export function ProjectsCards({
  projects,
  ownerProfiles,
  currentUser,
  nextActionsMap,
  taskStatsMap,
  meetings,
  onProjectClick,
  onRefresh,
}: ProjectsCardsProps) {
  // Group meetings by project
  const meetingsByProject = useMemo(() => {
    const map: Record<string, { today: number; upcoming: number }> = {}
    for (const m of meetings) {
      if (!m.project_id || m.status === 'cancelled') continue
      if (!map[m.project_id]) map[m.project_id] = { today: 0, upcoming: 0 }
      const d = new Date(m.meeting_date)
      if (isToday(d)) {
        map[m.project_id].today++
      } else if (isTomorrow(d) || d > new Date()) {
        map[m.project_id].upcoming++
      }
    }
    return map
  }, [meetings])

  if (projects.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-[#999]">No projects match your filters</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {projects.map((project) => {
        const ownerProfile = project.created_by ? ownerProfiles[project.created_by] : undefined
        const ownerName = ownerProfile?.first_name || currentUser?.first_name || 'Unknown'
        const ownerPhotoUrl = ownerProfile?.photo_url || currentUser?.photo_url
        const stageLabel = STAGE_LABELS[project.stage] || project.stage
        const nextAction = nextActionsMap[project.id] ?? null
        const taskStats = taskStatsMap[project.id] ?? null
        const projectMeetings = meetingsByProject[project.id]
        const pendingTasks = taskStats?.by_status?.pending ?? 0
        const totalTasks = taskStats?.total ?? 0

        const isBuilding = project.launch_status === 'building'

        return (
          <div
            key={project.id}
            onClick={() => onProjectClick(project.id)}
            className={`bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5 hover:shadow-lg cursor-pointer transition-shadow flex flex-col relative overflow-hidden ${
              isBuilding ? 'border-[#3FAF7A]/30' : ''
            }`}
          >
            {/* Building overlay */}
            {isBuilding && (
              <div className="absolute inset-0 z-10 bg-white/80 backdrop-blur-[2px] flex flex-col items-center justify-center gap-3 rounded-2xl">
                <Settings className="w-8 h-8 text-[#3FAF7A] animate-spin" style={{ animationDuration: '3s' }} />
                <p className="text-sm font-medium text-[#333333]">Building your project...</p>
                <div className="w-32 h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
                  <div className="h-full bg-[#3FAF7A] rounded-full animate-pulse" style={{ width: '45%' }} />
                </div>
              </div>
            )}

            {/* Top: Avatar + name + client + stage badge */}
            <div className={`flex items-start gap-3 ${isBuilding ? 'opacity-30 blur-sm' : ''}`}>
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
                {isBuilding ? 'Building' : stageLabel}
              </span>
            </div>

            {/* Readiness */}
            <div className={`mt-3 ${isBuilding ? 'opacity-30 blur-sm' : ''}`}>
              <ReadinessCell project={project} />
            </div>

            {/* Hero action */}
            {!isBuilding && nextAction && (() => {
              const ActionIcon = ACTION_ICONS[nextAction.action_type] || ArrowRight
              return (
                <div className="mt-3 flex items-start gap-2 bg-[#F0FAF5] rounded-lg px-3 py-2">
                  <ActionIcon className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
                  <span className="text-[12px] text-[#25785A] leading-snug line-clamp-2">
                    {nextAction.title}
                  </span>
                </div>
              )
            })()}

            {/* Description */}
            {!isBuilding && project.description && (
              <p className="text-[11px] text-[#666] leading-relaxed mt-2.5 line-clamp-2">
                {project.description}
              </p>
            )}

            {/* Stats row: tasks + meetings */}
            {!isBuilding && (
              <div className="mt-2.5 flex items-center gap-3 flex-wrap">
                {totalTasks > 0 && (
                  <span className="flex items-center gap-1 text-[11px] text-[#999]">
                    <ListTodo className="w-3 h-3" />
                    {pendingTasks > 0 ? (
                      <>{pendingTasks} pending</>
                    ) : (
                      <span className="flex items-center gap-0.5">
                        <CheckCircle2 className="w-2.5 h-2.5 text-[#3FAF7A]" />
                        All done
                      </span>
                    )}
                  </span>
                )}
                {projectMeetings && (projectMeetings.today > 0 || projectMeetings.upcoming > 0) && (
                  <span className="flex items-center gap-1 text-[11px] text-[#999]">
                    <CalendarDays className="w-3 h-3" />
                    {projectMeetings.today > 0
                      ? `${projectMeetings.today} today`
                      : `${projectMeetings.upcoming} upcoming`}
                  </span>
                )}
              </div>
            )}

            {/* Spacer to push footer down */}
            <div className="flex-1" />

            {/* Footer: owner + time + stage advance */}
            <div className={`flex items-center justify-between mt-3 pt-3 border-t border-[#E5E5E5] ${isBuilding ? 'opacity-30 blur-sm' : ''}`}>
              <UserAvatar name={ownerName} photoUrl={ownerPhotoUrl} size="small" />
              <div className="flex items-center gap-1.5">
                {project.stage_eligible === true && !isBuilding && (
                  <StageAdvancePopover projectId={project.id} onStageAdvanced={onRefresh}>
                    <button
                      onClick={(e) => e.stopPropagation()}
                      className="p-0.5 rounded hover:bg-[#E8F5E9] transition-colors"
                      title="Ready to advance stage"
                    >
                      <svg
                        className="w-3.5 h-3.5 text-[#3FAF7A]"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={2.5}
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
                      </svg>
                    </button>
                  </StageAdvancePopover>
                )}
                <span className="text-[11px] text-[#999]">
                  {formatDistanceToNow(new Date(project.updated_at || project.created_at), {
                    addSuffix: true,
                  })}
                </span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
