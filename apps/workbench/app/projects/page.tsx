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

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { listProjects, getMyProfile } from '@/lib/api'
import type { ProjectDetailWithDashboard, Profile } from '@/types/api'
import { ProjectsTopNav } from './components/ProjectsTopNav'
import { ProjectsTable } from './components/ProjectsTable'
import { ProjectsKanban } from './components/ProjectsKanban'
import { AppSidebar } from '@/components/workspace/AppSidebar'

type ViewMode = 'table' | 'kanban'
type SortField = 'name' | 'updated_at' | 'readiness_score'
type SortOrder = 'asc' | 'desc'

export default function ProjectsPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<ProjectDetailWithDashboard[]>([])
  const [ownerProfiles, setOwnerProfiles] = useState<Record<string, { first_name?: string; last_name?: string; photo_url?: string }>>({})
  const [currentUser, setCurrentUser] = useState<Profile | null>(null)
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [searchQuery, setSearchQuery] = useState('')
  const [stageFilter, setStageFilter] = useState<string>('all')
  const [clientFilter, setClientFilter] = useState<string>('all')
  const [sortField, setSortField] = useState<SortField>('updated_at')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  useEffect(() => {
    loadProjects()
    loadCurrentUser()
  }, [])

  const loadCurrentUser = async () => {
    try {
      const profile = await getMyProfile()
      setCurrentUser(profile)
    } catch (error) {
      console.error('Failed to load current user profile:', error)
    }
  }

  const loadProjects = async () => {
    try {
      setLoading(true)
      const response = await listProjects('active')
      setProjects(response.projects)
      setOwnerProfiles(response.owner_profiles || {})
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = () => {
    loadProjects()
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
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#009b87] mx-auto mb-4"></div>
            <p className="text-sm text-ui-supportText">Loading projects...</p>
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
          ) : (
            <ProjectsKanban
              projects={sortedProjects}
              ownerProfiles={ownerProfiles}
              currentUser={currentUser}
              onProjectClick={handleProjectClick}
              onRefresh={handleRefresh}
            />
          )}
        </div>
      </div>
    </>
  )
}
