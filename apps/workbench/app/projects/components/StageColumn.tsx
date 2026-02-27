import React from 'react'
import type { ProjectDetailWithDashboard, Profile } from '@/types/api'
import { ProjectKanbanCard } from './ProjectKanbanCard'

interface StageColumnProps {
  stage: string
  label: string
  projects: ProjectDetailWithDashboard[]
  ownerProfiles: Record<string, { first_name?: string; last_name?: string; photo_url?: string }>
  currentUser: Profile | null
  onProjectClick: (projectId: string) => void
  onRefresh?: () => void
}

const STAGE_COLORS = {
  discovery: 'bg-emerald-100 border-emerald-300',
  validation: 'bg-emerald-50 border-emerald-200',
  prototype: 'bg-teal-50 border-teal-200',
  proposal: 'bg-brand-primary-light border-brand-primary/30',
  build: 'bg-emerald-200 border-emerald-400',
  live: 'bg-emerald-100 border-emerald-300',
}

export function StageColumn({
  stage,
  label,
  projects,
  ownerProfiles,
  currentUser,
  onProjectClick,
  onRefresh,
}: StageColumnProps) {
  const stageColor = STAGE_COLORS[stage as keyof typeof STAGE_COLORS] || 'bg-gray-100 border-gray-300'

  return (
    <div className="flex-shrink-0 min-w-60 w-60">
      <div className={`rounded-t-card border-t-4 ${stageColor} px-3 py-1.5 mb-2`}>
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-text-body">{label}</h3>
          <span className="text-[10px] font-medium text-text-placeholder bg-white px-1.5 py-0.5 rounded-full border border-border">
            {projects.length}
          </span>
        </div>
      </div>

      <div className="space-y-2 min-h-[200px]">
        {projects.length === 0 ? (
          <div className="bg-white border-2 border-dashed border-border rounded-lg p-6 text-center">
            <p className="text-xs text-text-placeholder">No projects</p>
          </div>
        ) : (
          projects.map((project) => (
            <ProjectKanbanCard
              key={project.id}
              project={project}
              ownerProfile={project.created_by ? ownerProfiles[project.created_by] : undefined}
              currentUser={currentUser}
              onClick={() => onProjectClick(project.id)}
              onRefresh={onRefresh}
            />
          ))
        )}
      </div>
    </div>
  )
}
