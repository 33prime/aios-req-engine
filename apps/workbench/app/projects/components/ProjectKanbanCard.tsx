import React from 'react'
import { formatDistanceToNow } from 'date-fns'
import type { ProjectDetailWithDashboard, Profile } from '@/types/api'
import { ProjectAvatar } from './ProjectAvatar'
import { UserAvatar } from './UserAvatar'
import { ReadinessCell } from './ReadinessCell'
import { StageAdvancePopover } from './StageAdvancePopover'

interface ProjectKanbanCardProps {
  project: ProjectDetailWithDashboard
  ownerProfile?: { first_name?: string; last_name?: string; photo_url?: string }
  currentUser: Profile | null
  onClick: () => void
  onRefresh?: () => void
}

export function ProjectKanbanCard({ project, ownerProfile, currentUser, onClick, onRefresh }: ProjectKanbanCardProps) {
  // Owner display logic with current user fallback
  const ownerName = ownerProfile?.first_name || currentUser?.first_name || 'Unknown'
  const ownerPhotoUrl = ownerProfile?.photo_url || currentUser?.photo_url

  return (
    <div
      onClick={onClick}
      className="bg-white border border-border rounded-lg shadow-sm p-3 hover:shadow-lg transition-shadow cursor-pointer"
    >
      {/* Header */}
      <div className="flex flex-col items-center gap-1 mb-2">
        <ProjectAvatar name={project.name} clientName={project.client_name} />
        <div className="text-center min-w-0 w-full">
          <h4 className="text-xs font-medium text-text-body truncate">{project.name}</h4>
          {project.client_name && (
            <p className="text-xs text-text-placeholder truncate">{project.client_name}</p>
          )}
        </div>
      </div>

      {/* Description */}
      {project.description && (
        <p className="text-xs text-text-body leading-relaxed mb-2 line-clamp-2">
          {project.description}
        </p>
      )}

      {/* Readiness Score */}
      <div className="mb-2">
        <ReadinessCell project={project} />
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-border">
        <UserAvatar name={ownerName} photoUrl={ownerPhotoUrl} size="small" />
        <div className="flex items-center gap-1.5">
          {project.stage_eligible === true && (
            <StageAdvancePopover projectId={project.id} onStageAdvanced={onRefresh}>
              <button
                onClick={(e) => e.stopPropagation()}
                className="p-0.5 rounded hover:bg-emerald-50 transition-colors"
                title="Ready to advance stage"
              >
                <svg
                  className="w-3.5 h-3.5 text-emerald-500"
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
          <div className="text-xs text-text-placeholder">
            {formatDistanceToNow(new Date(project.updated_at || project.created_at), {
              addSuffix: true,
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
