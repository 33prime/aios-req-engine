import React from 'react'
import type { ProjectDetailWithDashboard, Profile } from '@/types/api'
import { getReadinessScore } from './ReadinessCell'
import { StageColumn } from './StageColumn'

interface ProjectsKanbanProps {
  projects: ProjectDetailWithDashboard[]
  ownerProfiles: Record<string, { first_name?: string; last_name?: string; photo_url?: string }>
  currentUser: Profile | null
  onProjectClick: (projectId: string) => void
  onRefresh?: () => void
}

const TIERS = [
  { id: 'not_scored', label: 'Not Scored', color: 'bg-gray-100 border-gray-300' },
  { id: 'at_risk', label: 'At Risk', color: 'bg-amber-50 border-amber-300' },
  { id: 'progressing', label: 'Progressing', color: 'bg-emerald-50 border-emerald-300' },
  { id: 'on_track', label: 'On Track', color: 'bg-emerald-100 border-emerald-400' },
  { id: 'ready', label: 'Ready', color: 'bg-brand-primary-light border-brand-primary/30' },
]

function getTier(project: ProjectDetailWithDashboard): string {
  const score = getReadinessScore(project)
  if (score === null) return 'not_scored'
  if (score < 20) return 'at_risk'
  if (score < 40) return 'progressing'
  if (score < 70) return 'on_track'
  return 'ready'
}

export function ProjectsKanban({
  projects,
  ownerProfiles,
  currentUser,
  onProjectClick,
  onRefresh,
}: ProjectsKanbanProps) {
  // Group projects by readiness tier
  const projectsByTier = TIERS.reduce((acc, tier) => {
    acc[tier.id] = projects
      .filter((p) => getTier(p) === tier.id)
      .sort((a, b) => (getReadinessScore(a) ?? -1) - (getReadinessScore(b) ?? -1))
    return acc
  }, {} as Record<string, ProjectDetailWithDashboard[]>)

  return (
    <div className="overflow-x-auto pb-3">
      <div className="inline-flex gap-3 min-w-full">
        {TIERS.map((tier) => (
          <StageColumn
            key={tier.id}
            stage={tier.id}
            label={tier.label}
            projects={projectsByTier[tier.id] || []}
            ownerProfiles={ownerProfiles}
            currentUser={currentUser}
            onProjectClick={onProjectClick}
            onRefresh={onRefresh}
            colorOverride={tier.color}
          />
        ))}
      </div>
    </div>
  )
}
