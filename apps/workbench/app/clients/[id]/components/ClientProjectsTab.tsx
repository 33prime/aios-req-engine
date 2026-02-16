'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { FolderKanban, Plus, Unlink } from 'lucide-react'
import { listProjects, linkProjectToClient, unlinkProjectFromClient } from '@/lib/api'
import type { ClientDetail, ClientDetailProject } from '@/types/workspace'

interface ClientProjectsTabProps {
  client: ClientDetail
  onRefresh: () => void
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function ProjectCard({ project, onView, onUnlink }: { project: ClientDetailProject; onView: () => void; onUnlink: () => void }) {
  const counts = project.counts
  const readiness = project.cached_readiness_score ?? 0

  return (
    <div
      className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5 hover:shadow-lg transition-shadow cursor-pointer"
      onClick={onView}
    >
      <div className="flex items-start justify-between mb-3">
        <h4 className="text-[14px] font-semibold text-[#333]">{project.name}</h4>
        {project.stage && (
          <span className="px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md flex-shrink-0">
            {project.stage}
          </span>
        )}
      </div>

      {/* Entity counts grid */}
      {counts && (
        <div className="grid grid-cols-3 gap-2 mb-3">
          {[
            { label: 'Features', count: counts.features ?? 0 },
            { label: 'Personas', count: counts.personas ?? 0 },
            { label: 'Steps', count: counts.vp_steps ?? 0 },
            { label: 'Signals', count: counts.signals ?? 0 },
            { label: 'Drivers', count: counts.business_drivers ?? 0 },
          ].map((item) => (
            <div key={item.label} className="bg-[#F4F4F4] rounded-lg px-2 py-1.5 text-center">
              <span className="text-[13px] font-semibold text-[#333]">{item.count}</span>
              <span className="text-[11px] text-[#999] ml-1">{item.label}</span>
            </div>
          ))}
        </div>
      )}

      {/* Readiness bar + footer */}
      <div className="flex items-center justify-between mt-2">
        <div className="flex items-center gap-2 flex-1 mr-3">
          <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-[#3FAF7A] rounded-full transition-all"
              style={{ width: `${readiness}%` }}
            />
          </div>
          <span className="text-[11px] font-medium text-[#666] flex-shrink-0">{readiness}% Ready</span>
        </div>
        <div className="flex items-center gap-2">
          {project.updated_at && (
            <span className="text-[11px] text-[#999]">{formatTimeAgo(project.updated_at)}</span>
          )}
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
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {client.projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              onView={() => router.push(`/projects/${project.id}`)}
              onUnlink={() => handleUnlink(project.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
