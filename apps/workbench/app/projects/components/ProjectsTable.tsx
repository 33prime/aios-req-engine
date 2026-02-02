import React from 'react'
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import type { ProjectDetailWithDashboard, Profile } from '@/types/api'
import { ProjectRow } from './ProjectRow'

interface ProjectsTableProps {
  projects: ProjectDetailWithDashboard[]
  ownerProfiles: Record<string, { first_name?: string; last_name?: string; photo_url?: string }>
  currentUser: Profile | null
  sortField: 'name' | 'updated_at' | 'readiness_score'
  sortOrder: 'asc' | 'desc'
  onSort: (field: 'name' | 'updated_at' | 'readiness_score') => void
  onProjectClick: (projectId: string) => void
}

export function ProjectsTable({
  projects,
  ownerProfiles,
  currentUser,
  sortField,
  sortOrder,
  onSort,
  onProjectClick,
}: ProjectsTableProps) {
  const SortIcon = ({ field }: { field: string }) => {
    if (sortField !== field) {
      return <ArrowUpDown className="w-3 h-3 text-ui-supportText" />
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-3 h-3 text-brand-teal" />
    ) : (
      <ArrowDown className="w-3 h-3 text-brand-teal" />
    )
  }

  if (projects.length === 0) {
    return (
      <div className="bg-white rounded-card border border-ui-cardBorder shadow-card p-8 text-center">
        <p className="text-xs text-ui-supportText">No projects found</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-card border border-ui-cardBorder shadow-card overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-[#FAFAFA] border-b border-ui-cardBorder">
            <tr>
              <th className="px-3 py-2 text-left">
                <button
                  onClick={() => onSort('name')}
                  className="flex items-center gap-1.5 text-xs font-semibold text-ui-headingDark uppercase tracking-wide hover:text-brand-teal transition-colors"
                >
                  Project
                  <SortIcon field="name" />
                </button>
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-ui-headingDark uppercase tracking-wide">
                Stage
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-ui-headingDark uppercase tracking-wide">
                Client
              </th>
              <th className="px-3 py-2 text-left">
                <button
                  onClick={() => onSort('readiness_score')}
                  className="flex items-center gap-1.5 text-xs font-semibold text-ui-headingDark uppercase tracking-wide hover:text-brand-teal transition-colors"
                >
                  Readiness
                  <SortIcon field="readiness_score" />
                </button>
              </th>
              <th className="px-3 py-2 text-left text-xs font-semibold text-ui-headingDark uppercase tracking-wide">
                Owner
              </th>
              <th className="px-3 py-2 text-left">
                <button
                  onClick={() => onSort('updated_at')}
                  className="flex items-center gap-1.5 text-xs font-semibold text-ui-headingDark uppercase tracking-wide hover:text-brand-teal transition-colors"
                >
                  Updated
                  <SortIcon field="updated_at" />
                </button>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ui-cardBorder">
            {projects.map((project) => (
              <ProjectRow
                key={project.id}
                project={project}
                ownerProfile={project.created_by ? ownerProfiles[project.created_by] : undefined}
                currentUser={currentUser}
                onClick={() => onProjectClick(project.id)}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
