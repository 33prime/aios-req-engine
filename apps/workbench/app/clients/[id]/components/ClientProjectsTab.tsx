'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { formatDistanceToNow } from 'date-fns'
import { FolderKanban, Plus, Unlink, ArrowRight, ListFilter } from 'lucide-react'
import { listProjects, linkProjectToClient, unlinkProjectFromClient, getNextActions } from '@/lib/api'
import type { NextAction } from '@/lib/api'
import type { ClientDetail, ClientDetailProject } from '@/types/workspace'
import { ProjectAvatar } from '@/app/projects/components/ProjectAvatar'

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

function ProjectCard({ project, clientName, nextAction, onView, onUnlink }: {
  project: ClientDetailProject
  clientName: string
  nextAction: NextAction | null
  onView: () => void
  onUnlink: () => void
}) {
  // Compute dimensional score like home page
  const readiness = project.cached_readiness_data
  let score = 0
  if (readiness?.dimensions) {
    for (const key of Object.keys(readiness.dimensions)) {
      const d = readiness.dimensions[key]
      if (d && typeof d.score === 'number' && typeof d.weight === 'number') {
        score += d.score * d.weight
      }
    }
  } else {
    score = readiness?.score ?? project.cached_readiness_score ?? 0
  }

  const stageLabel = STAGE_LABELS[project.stage || ''] || project.stage || ''

  // Pending entity count
  const totalEntities = readiness?.total_entities ?? 0
  const confirmedEntities = readiness?.confirmed_entities ?? 0
  const pendingEntities = totalEntities - confirmedEntities

  return (
    <div
      className="bg-white rounded-2xl shadow-md border border-border p-5 hover:shadow-lg cursor-pointer transition-shadow flex flex-col"
      onClick={onView}
    >
      {/* Top row: avatar + name + stage */}
      <div className="flex items-start gap-3">
        <ProjectAvatar name={project.name} clientName={clientName} />
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
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${score > 0 ? 'bg-brand-primary' : 'bg-brand-primary'}`} />
        <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-primary rounded-full transition-all"
            style={{ width: `${Math.min(score, 100)}%` }}
          />
        </div>
        <span className={`text-sm font-semibold tabular-nums ${score > 0 ? 'text-brand-primary' : 'text-brand-primary'}`}>
          {Math.round(score)}%
        </span>
      </div>

      {/* Next action */}
      <div className="mt-3">
        {nextAction ? (
          <div className="flex items-center gap-1.5 bg-[#E8F5E9] rounded-lg px-3 py-2">
            <ArrowRight className="w-3 h-3 text-brand-primary flex-shrink-0" />
            <span className="text-[12px] text-brand-primary truncate">{nextAction.title}</span>
          </div>
        ) : (
          <p className="text-[12px] text-[#999]">All caught up</p>
        )}
      </div>

      {/* Description */}
      {project.description && (
        <p className="text-[12px] text-[#666] mt-3 line-clamp-2 leading-relaxed">
          {project.description}
        </p>
      )}

      {/* Pending count */}
      {pendingEntities > 0 && (
        <div className="flex items-center gap-1.5 mt-2">
          <ListFilter className="w-3 h-3 text-[#999]" />
          <span className="text-[11px] text-[#999]">{pendingEntities} pending</span>
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
        <span className="text-[10px] text-[#999]">
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
  const [nextActionsMap, setNextActionsMap] = useState<Record<string, NextAction | null>>({})

  const linkedProjectIds = new Set(client.projects.map((p) => p.id))

  // Fetch next actions for each linked project
  useEffect(() => {
    async function loadNextActions() {
      const results = await Promise.all(
        client.projects.map((p) =>
          getNextActions(p.id)
            .then((res) => ({ id: p.id, action: res.actions[0] ?? null }))
            .catch(() => ({ id: p.id, action: null }))
        )
      )
      const map: Record<string, NextAction | null> = {}
      for (const r of results) map[r.id] = r.action
      setNextActionsMap(map)
    }
    if (client.projects.length > 0) loadNextActions()
  }, [client.projects])

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
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-brand-primary border border-brand-primary rounded-xl hover:bg-[#E8F5E9] transition-colors"
          >
            <Plus className="w-3 h-3" />
            Link Project
          </button>

          {showLinkDropdown && (
            <div className="absolute right-0 top-full mt-1 w-64 bg-white rounded-xl border border-border shadow-lg z-10 max-h-[240px] overflow-y-auto">
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
        <div className="text-center py-12 bg-white rounded-2xl border border-border shadow-md">
          <FolderKanban className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
          <p className="text-[13px] text-[#666] mb-1">No linked projects</p>
          <p className="text-[12px] text-[#999]">Link existing projects to this client</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {client.projects.map((project) => (
            <ProjectCard
              key={project.id}
              project={project}
              clientName={client.name}
              nextAction={nextActionsMap[project.id] ?? null}
              onView={() => router.push(`/projects/${project.id}`)}
              onUnlink={() => handleUnlink(project.id)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
