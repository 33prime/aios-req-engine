import React from 'react'
import type { ProjectDetailWithDashboard, Profile } from '@/types/api'
import { StageColumn } from './StageColumn'

interface ProjectsKanbanProps {
  projects: ProjectDetailWithDashboard[]
  ownerProfiles: Record<string, { first_name?: string; last_name?: string; photo_url?: string }>
  currentUser: Profile | null
  onProjectClick: (projectId: string) => void
  onRefresh?: () => void
}

const STAGES = [
  { id: 'discovery', label: 'Discovery' },
  { id: 'validation', label: 'Validation' },
  { id: 'prototype', label: 'Prototype' },
  { id: 'proposal', label: 'Proposal' },
  { id: 'build', label: 'Build' },
  { id: 'live', label: 'Live' },
]

export function ProjectsKanban({
  projects,
  ownerProfiles,
  currentUser,
  onProjectClick,
  onRefresh,
}: ProjectsKanbanProps) {
  // Group projects by stage
  const projectsByStage = STAGES.reduce((acc, stage) => {
    acc[stage.id] = projects.filter((p) => {
      // Map prototype_refinement to validation column
      if (stage.id === 'validation' && p.stage === 'prototype_refinement') {
        return true
      }
      return p.stage === stage.id
    })
    return acc
  }, {} as Record<string, ProjectDetailWithDashboard[]>)

  return (
    <div className="overflow-x-auto pb-3">
      <div className="inline-flex gap-3 min-w-full">
        {STAGES.map((stage) => (
          <StageColumn
            key={stage.id}
            stage={stage.id}
            label={stage.label}
            projects={projectsByStage[stage.id] || []}
            ownerProfiles={ownerProfiles}
            currentUser={currentUser}
            onProjectClick={onProjectClick}
            onRefresh={onRefresh}
          />
        ))}
      </div>
    </div>
  )
}
