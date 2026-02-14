'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { FolderKanban, Link2, Unlink, Plus } from 'lucide-react'
import { listProjects, linkProjectToClient, unlinkProjectFromClient } from '@/lib/api'
import type { ClientDetail } from '@/types/workspace'

interface ClientProjectsTabProps {
  client: ClientDetail
  onRefresh: () => void
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

      {/* Projects table */}
      {client.projects.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-2xl border border-[#E5E5E5] shadow-md">
          <FolderKanban className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
          <p className="text-[13px] text-[#666] mb-1">No linked projects</p>
          <p className="text-[12px] text-[#999]">Link existing projects to this client</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#E5E5E5]">
                <th className="text-left px-4 py-3 text-[11px] font-medium text-[#999] uppercase tracking-wide">
                  Project
                </th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-[#999] uppercase tracking-wide">
                  Stage
                </th>
                <th className="text-left px-4 py-3 text-[11px] font-medium text-[#999] uppercase tracking-wide">
                  Last Updated
                </th>
                <th className="text-right px-4 py-3 text-[11px] font-medium text-[#999] uppercase tracking-wide">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {client.projects.map((project) => (
                <tr
                  key={project.id}
                  className="border-b border-[#F0F0F0] last:border-0 hover:bg-[#FAFAFA] transition-colors cursor-pointer"
                  onClick={() => router.push(`/projects/${project.id}`)}
                >
                  <td className="px-4 py-3">
                    <span className="text-[13px] font-medium text-[#333] hover:text-[#3FAF7A] transition-colors">
                      {project.name}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {project.stage && (
                      <span className="px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                        {project.stage}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-[12px] text-[#999]">
                    {project.updated_at
                      ? new Date(project.updated_at).toLocaleDateString()
                      : '-'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleUnlink(project.id)
                      }}
                      className="p-1.5 text-[#999] hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                      title="Unlink project"
                    >
                      <Unlink className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
