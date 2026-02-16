'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { formatDistanceToNow } from 'date-fns'
import { FolderKanban, Plus, Unlink } from 'lucide-react'
import { listProjects, linkProjectToClient, unlinkProjectFromClient } from '@/lib/api'
import type { ClientDetail, ClientDetailProject } from '@/types/workspace'

interface ClientProjectsTabProps {
  client: ClientDetail
  onRefresh: () => void
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

function ProjectCard({ project, clientName, onView, onUnlink }: {
  project: ClientDetailProject
  clientName: string
  onView: () => void
  onUnlink: () => void
}) {
  const readiness = project.cached_readiness_score ?? 0
  const stageLabel = STAGE_LABELS[project.stage || ''] || project.stage || ''

  // Generate initials from client name
  const initials = clientName
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)

  const readinessColor = readiness >= 80
    ? { bar: 'bg-[#3FAF7A]', dot: 'bg-[#3FAF7A]', text: 'text-[#3FAF7A]' }
    : readiness >= 50
      ? { bar: 'bg-[#4CC08C]', dot: 'bg-[#4CC08C]', text: 'text-[#25785A]' }
      : readiness >= 20
        ? { bar: 'bg-emerald-300', dot: 'bg-emerald-300', text: 'text-emerald-600' }
        : { bar: 'bg-gray-300', dot: 'bg-gray-300', text: 'text-[#999]' }

  return (
    <div
      className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5 hover:shadow-lg cursor-pointer transition-shadow flex flex-col"
      onClick={onView}
    >
      {/* Top: Avatar + name + stage badge */}
      <div className="flex items-start gap-3">
        <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-500 text-white flex items-center justify-center text-[10px] font-semibold flex-shrink-0 shadow-sm">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-semibold text-[#333] truncate">{project.name}</p>
          <p className="text-[11px] text-[#999] truncate">{clientName}</p>
        </div>
        {stageLabel && (
          <span className="flex-shrink-0 text-[10px] px-2 py-0.5 rounded-full bg-[#F0F0F0] text-[#666]">
            {stageLabel}
          </span>
        )}
      </div>

      {/* Readiness bar */}
      <div className="mt-3 flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${readinessColor.dot}`} />
        <div className="w-20 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${readinessColor.bar}`}
            style={{ width: `${readiness}%` }}
          />
        </div>
        <span className={`text-sm font-semibold tabular-nums ${readinessColor.text}`}>
          {readiness}%
        </span>
      </div>

      {/* Entity counts */}
      {project.counts && (
        <div className="mt-3 flex items-center gap-3 flex-wrap">
          {[
            { label: 'features', count: project.counts.features ?? 0 },
            { label: 'personas', count: project.counts.personas ?? 0 },
            { label: 'signals', count: project.counts.signals ?? 0 },
          ].filter(item => item.count > 0).map((item) => (
            <span key={item.label} className="text-[11px] text-[#999]">
              <strong className="text-[#666]">{item.count}</strong> {item.label}
            </span>
          ))}
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#E5E5E5]">
        <span className="text-[11px] text-[#999]">
          {project.updated_at
            ? formatDistanceToNow(new Date(project.updated_at), { addSuffix: true })
            : '—'}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onUnlink()
          }}
          className="p-1.5 text-[#999] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
          title="Unlink project"
        >
          <Unlink className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  )
}

export function ClientProjectsTab({ client, onRefresh }: ClientProjectsTabProps) {
  const router = useRouter()
  const [showLinkDropdown, setShowLinkDropdown] = useState(false)
  const [availableProjects, setAvailableProjects] = useState<{ id: string; name: string }[]>([])
  const [loadingProjects, setLoadingProjects] = useState(false)

  const linkedProjectIds = new Set(client.projects.map((p) => p.id))

  const loadAvailableProjects = async () => {
    setLoadingProjects(true)
    try {
      const result = await listProjects('active')
      const unlinked = result.projects
        .filter((p: { id: string }) => !linkedProjectIds.has(p.id))
        .map((p: { id: string; name: string }) => ({ id: p.id, name: p.name }))
      setAvailableProjects(unlinked)
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      setLoadingProjects(false)
    }
  }

  const handleLink = async (projectId: string) => {
    try {
      await linkProjectToClient(client.id, projectId)
      setShowLinkDropdown(false)
      onRefresh()
    } catch (error) {
      console.error('Failed to link project:', error)
    }
  }

  const handleUnlink = async (projectId: string) => {
    try {
      await unlinkProjectFromClient(client.id, projectId)
      onRefresh()
    } catch (error) {
      console.error('Failed to unlink project:', error)
    }
  }

  const handleToggleLinkDropdown = () => {
    if (!showLinkDropdown) {
      loadAvailableProjects()
    }
    setShowLinkDropdown(!showLinkDropdown)
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FolderKanban className="w-4 h-4 text-[#666]" />
          <h3 className="text-[14px] font-semibold text-[#333]">
            Linked Projects ({client.projects.length})
          </h3>
        </div>

        <div className="relative">
          <button
            onClick={handleToggleLinkDropdown}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#3FAF7A] border border-[#3FAF7A] rounded-xl hover:bg-[#E8F5E9] transition-colors"
          >
            <Plus className="w-3 h-3" />
            Link Project
          </button>

          {showLinkDropdown && (
            <div className="absolute right-0 top-full mt-1 w-64 bg-white rounded-xl border border-[#E5E5E5] shadow-lg z-10 max-h-[240px] overflow-y-auto">
              {loadingProjects ? (
                <div className="px-3 py-4 text-center text-[12px] text-[#999]">Loading...</div>
              ) : availableProjects.length === 0 ? (
                <div className="px-3 py-4 text-center text-[12px] text-[#999]">
                  No unlinked projects available
                </div>
              ) : (
                availableProjects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => handleLink(project.id)}
                    className="w-full text-left px-3 py-2 text-[13px] text-[#333] hover:bg-[#F0F0F0] transition-colors first:rounded-t-xl last:rounded-b-xl"
                  >
                    {project.name}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>

      {/* Projects grid */}
      {client.projects.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-2xl border border-[#E5E5E5] shadow-md">
          <FolderKanban className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
          <p className="text-[13px] text-[#666] mb-1">No linked projects</p>
          <p className="text-[12px] text-[#999]">Link existing projects to this client</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {client.projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              clientName={client.name}
              onView={() => router.push(`/projects/${project.id}`)}
              onUnlink={() => handleUnlink(project.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
