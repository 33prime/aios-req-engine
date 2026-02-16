/**
 * Projects List Page - Table and Kanban Views
 *
 * Displays all projects with:
 * - Toggle between table and kanban view
 * - Search, filters (stage, client)
 * - Sorting (name, updated_at, readiness_score)
 * - Navigation to project detail pages
 */

'use client'

import React, { useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import type { NextAction, TaskStatsResponse } from '@/lib/api'
import { useProfile, useProjects, useUpcomingMeetings, useBatchDashboardData } from '@/lib/hooks/use-api'
import { ProjectsTopNav } from './components/ProjectsTopNav'
import { ProjectsTable } from './components/ProjectsTable'
import { ProjectsKanban } from './components/ProjectsKanban'
import { ProjectsCards } from './components/ProjectsCards'
import { AppSidebar } from '@/components/workspace/AppSidebar'

type ViewMode = 'table' | 'kanban' | 'cards'
type SortField = 'name' | 'updated_at' | 'readiness_score'
type SortOrder = 'asc' | 'desc'

export default function ProjectsPage() {
  const router = useRouter()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('cards')
  const [searchQuery, setSearchQuery] = useState('')
  const [stageFilter, setStageFilter] = useState<string>('all')
  const [clientFilter, setClientFilter] = useState<string>('all')
  const [sortField, setSortField] = useState<SortField>('updated_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  // SWR hooks — cached, deduplicated, auto-revalidating
  const { data: profileData } = useProfile()
  const { data: projectsData, isLoading: projectsLoading, mutate: mutateProjects } = useProjects('active')
  const { data: meetingsData } = useUpcomingMeetings(30)

  const projects = projectsData?.projects ?? []
  const ownerProfiles = projectsData?.owner_profiles ?? {}
  const currentUser = profileData ?? null
  const meetings = meetingsData ?? []

  // Batch dashboard data loads once project IDs are available
  const projectIds = useMemo(() => projects.map((p) => p.id), [projects])
  const { data: dashboardData } = useBatchDashboardData(
    projectIds.length > 0 ? projectIds : undefined,
  )

  const nextActionsMap = useMemo(() => {
    const map: Record<string, NextAction | null> = {}
    if (dashboardData?.next_actions) {
      for (const [pid, actions] of Object.entries(dashboardData.next_actions)) {
        map[pid] = actions[0] ?? null
      }
    }
    return map
  }, [dashboardData])

  const taskStatsMap = useMemo(() => {
    const map: Record<string, TaskStatsResponse | null> = {}
    if (dashboardData?.task_stats) {
      for (const [pid, stats] of Object.entries(dashboardData.task_stats)) {
        map[pid] = stats
      }
    }
    return map
  }, [dashboardData])

  const loading = projectsLoading

  const handleRefresh = () => {
    mutateProjects()
  }

  const handleProjectClick = (projectId: string) => {
    router.push(`/projects/${projectId}`)
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  // Filter projects
  const filteredProjects = projects.filter((project) => {
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchesSearch =
        project.name.toLowerCase().includes(query) ||
        project.description?.toLowerCase().includes(query) ||
        project.client_name?.toLowerCase().includes(query)
      if (!matchesSearch) return false
    }

    // Stage filter
    if (stageFilter !== 'all' && project.stage !== stageFilter) {
      return false
    }

    // Client filter
    if (clientFilter !== 'all') {
      if (!project.client_name) return false
      if (project.client_name.toLowerCase() !== clientFilter.toLowerCase()) return false
    }

    return true
  })

  // Sort projects
  const sortedProjects = [...filteredProjects].sort((a, b) => {
    let aVal: any
    let bVal: any

    if (sortField === 'name') {
      aVal = a.name.toLowerCase()
      bVal = b.name.toLowerCase()
    } else if (sortField === 'updated_at') {
      aVal = new Date(a.updated_at || a.created_at).getTime()
      bVal = new Date(b.updated_at || b.created_at).getTime()
    } else if (sortField === 'readiness_score') {
      aVal = a.readiness_score ?? 0
      bVal = b.readiness_score ?? 0
    }

    if (sortOrder === 'asc') {
      return aVal > bVal ? 1 : -1
    } else {
      return aVal < bVal ? 1 : -1
    }
  })

  // Extract unique clients for filter
  const uniqueClients = Array.from(
    new Set(projects.map((p) => p.client_name).filter((name): name is string => Boolean(name)))
  ).sort()

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (loading) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-[#FAFAFA] flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#3FAF7A] mx-auto mb-4"></div>
            <p className="text-sm text-[#999999]">Loading projects...</p>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <AppSidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div
        className="min-h-screen bg-[#FAFAFA] transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="max-w-[1400px] mx-auto px-4 py-4">
          <ProjectsTopNav
            viewMode={viewMode}
            searchQuery={searchQuery}
            stageFilter={stageFilter}
            clientFilter={clientFilter}
            uniqueClients={uniqueClients}
            sortField={sortField}
            sortOrder={sortOrder}
            onViewModeChange={setViewMode}
            onSearchChange={setSearchQuery}
            onStageFilterChange={setStageFilter}
            onClientFilterChange={setClientFilter}
            onSortFieldChange={setSortField}
            onRefresh={handleRefresh}
          />

          {viewMode === 'table' ? (
            <ProjectsTable
              projects={sortedProjects}
              ownerProfiles={ownerProfiles}
              currentUser={currentUser}
              sortField={sortField}
              sortOrder={sortOrder}
              onSort={handleSort}
              onProjectClick={handleProjectClick}
            />
          ) : viewMode === 'kanban' ? (
            <ProjectsKanban
              projects={sortedProjects}
              ownerProfiles={ownerProfiles}
              currentUser={currentUser}
              onProjectClick={handleProjectClick}
              onRefresh={handleRefresh}
            />
          ) : (
            <ProjectsCards
              projects={sortedProjects}
              ownerProfiles={ownerProfiles}
              currentUser={currentUser}
              nextActionsMap={nextActionsMap}
              taskStatsMap={taskStatsMap}
              meetings={meetings}
              onProjectClick={handleProjectClick}
              onRefresh={handleRefresh}
            />
          )}
        </div>
      </div>
    </>
  )
}
