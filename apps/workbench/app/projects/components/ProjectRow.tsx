import React from 'react'
import { formatDistanceToNow } from 'date-fns'
import type { ProjectDetailWithDashboard, Profile } from '@/types/api'
import { ProjectAvatar } from './ProjectAvatar'
import { UserAvatar } from './UserAvatar'
import { ReadinessCell } from './ReadinessCell'

interface ProjectRowProps {
  project: ProjectDetailWithDashboard
  ownerProfile?: { first_name?: string; last_name?: string; photo_url?: string }
  currentUser: Profile | null
  onClick: () => void
}

const STAGE_COLORS = {
  discovery: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  validation: 'bg-emerald-50 text-emerald-600 border-emerald-100',
  prototype: 'bg-teal-50 text-teal-700 border-teal-100',
  proposal: 'bg-[#009b87]/10 text-[#009b87] border-[#009b87]/20',
  build: 'bg-emerald-200 text-emerald-800 border-emerald-300',
  live: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  prototype_refinement: 'bg-emerald-50 text-emerald-600 border-emerald-100',
}

const STAGE_LABELS = {
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  proposal: 'Proposal',
  build: 'Build',
  live: 'Live',
  prototype_refinement: 'Validation',
}

export function ProjectRow({ project, ownerProfile, currentUser, onClick }: ProjectRowProps) {
  const stageLabel = STAGE_LABELS[project.stage as keyof typeof STAGE_LABELS] || project.stage
  const stageColor = STAGE_COLORS[project.stage as keyof typeof STAGE_COLORS] || 'bg-gray-100 text-gray-700 border-gray-200'

  // Owner display logic with current user fallback
  const ownerName = ownerProfile?.first_name || currentUser?.first_name || 'Unknown'
  const ownerPhotoUrl = ownerProfile?.photo_url || currentUser?.photo_url

  return (
    <tr
      onClick={onClick}
      className="hover:bg-[#FAFAFA] cursor-pointer transition-colors"
    >
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <ProjectAvatar name={project.name} clientName={project.client_name} />
          <div className="min-w-0">
            <div className="text-xs font-medium text-ui-headingDark truncate">{project.name}</div>
            {project.description && (
              <div className="text-xs text-ui-supportText truncate max-w-md">
                {project.description}
              </div>
            )}
          </div>
        </div>
      </td>

      <td className="px-3 py-2">
        <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-medium border ${stageColor}`}>
          {stageLabel}
        </span>
      </td>

      <td className="px-3 py-2">
        <div className="text-xs text-ui-bodyText">
          {project.client_name || '-'}
        </div>
      </td>

      <td className="px-3 py-2">
        <ReadinessCell project={project} />
      </td>

      <td className="px-3 py-2">
        <div className="flex items-center gap-1.5">
          <UserAvatar name={ownerName} photoUrl={ownerPhotoUrl} size="small" />
          <span className="text-xs text-ui-bodyText">{ownerName}</span>
        </div>
      </td>

      <td className="px-3 py-2">
        <div className="text-xs text-ui-supportText">
          {formatDistanceToNow(new Date(project.updated_at || project.created_at), {
            addSuffix: true,
          })}
        </div>
      </td>
    </tr>
  )
}
