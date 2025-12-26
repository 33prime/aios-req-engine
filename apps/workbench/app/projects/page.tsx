/**
 * Projects List Page
 *
 * Dashboard for browsing and managing projects
 *
 * Features:
 * - List all projects with search
 * - Filter by status (Active | Archived | All)
 * - Create new projects
 * - Navigate to project workspace
 */

'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Search, FileText, Zap } from 'lucide-react'
import { listProjects } from '@/lib/api'
import type { ProjectDetail } from '@/types/api'
import { CreateProjectModal } from './components/CreateProjectModal'

export default function ProjectsPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<ProjectDetail[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'active' | 'archived' | 'all'>('active')
  const [showCreateModal, setShowCreateModal] = useState(false)

  useEffect(() => {
    loadProjects()
  }, [statusFilter])

  const loadProjects = async () => {
    try {
      setLoading(true)
      const status = statusFilter === 'all' ? undefined : statusFilter
      const data = await listProjects(status, searchQuery)
      setProjects(data.projects as ProjectDetail[])
    } catch (error) {
      console.error('Failed to load projects:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadProjects()
  }

  const handleProjectClick = (projectId: string) => {
    router.push(`/projects/${projectId}`)
  }

  const filteredProjects = projects.filter((project) => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      project.name.toLowerCase().includes(query) ||
      project.description?.toLowerCase().includes(query)
    )
  })

  if (loading) {
    return (
      <div className="min-h-screen bg-ui-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
          <p className="text-support text-ui-supportText">Loading projects...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-ui-background">
      {/* Header */}
      <div className="bg-white border-b border-ui-cardBorder">
        <div className="max-w-[1600px] mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-ui-headingDark">Projects</h1>
              <p className="text-sm text-ui-supportText mt-1">
                Manage your requirements projects
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-primary/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Project
            </button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="max-w-[1600px] mx-auto px-6 py-6">
        <div className="bg-white rounded-lg border border-ui-cardBorder p-4 mb-6">
          <div className="flex flex-col lg:flex-row gap-4">
            {/* Search */}
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-ui-supportText" />
                <input
                  type="text"
                  placeholder="Search projects..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent"
                />
              </div>
            </form>

            {/* Status Filter */}
            <div className="flex gap-2">
              <button
                onClick={() => setStatusFilter('active')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  statusFilter === 'active'
                    ? 'bg-brand-primary text-white'
                    : 'bg-ui-background text-ui-bodyText hover:bg-ui-buttonGray'
                }`}
              >
                Active
              </button>
              <button
                onClick={() => setStatusFilter('archived')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  statusFilter === 'archived'
                    ? 'bg-brand-primary text-white'
                    : 'bg-ui-background text-ui-bodyText hover:bg-ui-buttonGray'
                }`}
              >
                Archived
              </button>
              <button
                onClick={() => setStatusFilter('all')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  statusFilter === 'all'
                    ? 'bg-brand-primary text-white'
                    : 'bg-ui-background text-ui-bodyText hover:bg-ui-buttonGray'
                }`}
              >
                All
              </button>
            </div>
          </div>
        </div>

        {/* Projects Grid */}
        {filteredProjects.length === 0 ? (
          <div className="bg-white rounded-lg border border-ui-cardBorder p-12 text-center">
            <FileText className="w-12 h-12 text-ui-supportText mx-auto mb-4" />
            <h3 className="text-lg font-medium text-ui-bodyText mb-2">
              No projects found
            </h3>
            <p className="text-sm text-ui-supportText mb-6">
              {searchQuery
                ? 'Try adjusting your search or filters'
                : 'Get started by creating your first project'}
            </p>
            {!searchQuery && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-primary/90 transition-colors"
              >
                <Plus className="w-4 h-4" />
                Create Project
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredProjects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onClick={() => handleProjectClick(project.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      <CreateProjectModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={(projectId) => {
          setShowCreateModal(false)
          router.push(`/projects/${projectId}`)
        }}
      />
    </div>
  )
}

interface ProjectCardProps {
  project: ProjectDetail
  onClick: () => void
}

function ProjectCard({ project, onClick }: ProjectCardProps) {
  const getModeColor = (mode: 'initial' | 'maintenance') => {
    return mode === 'maintenance' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
  }

  const getModeLabel = (mode: 'initial' | 'maintenance') => {
    return mode === 'maintenance' ? '🔧 Maintenance' : '🌱 Initial'
  }

  return (
    <button
      onClick={onClick}
      className="bg-white rounded-lg border border-ui-cardBorder p-6 text-left hover:border-brand-primary hover:shadow-lg transition-all cursor-pointer group"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-semibold text-ui-headingDark group-hover:text-brand-primary transition-colors">
          {project.name}
        </h3>
        <span
          className={`flex-shrink-0 ml-2 px-2 py-1 text-xs font-medium rounded-full ${getModeColor(
            project.prd_mode
          )}`}
        >
          {getModeLabel(project.prd_mode)}
        </span>
      </div>

      {/* Description */}
      {project.description && (
        <p className="text-sm text-ui-supportText mb-4 line-clamp-2">
          {project.description}
        </p>
      )}

      {/* Entity Counts */}
      <div className="grid grid-cols-2 gap-3 pt-4 border-t border-ui-cardBorder">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-ui-supportText" />
          <div className="flex-1">
            <p className="text-xs text-ui-supportText">PRD Sections</p>
            <p className="text-sm font-semibold text-ui-bodyText">
              {project.counts?.prd_sections || 0}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Zap className="w-4 h-4 text-ui-supportText" />
          <div className="flex-1">
            <p className="text-xs text-ui-supportText">Features</p>
            <p className="text-sm font-semibold text-ui-bodyText">
              {project.counts?.features || 0}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 flex items-center justify-center text-ui-supportText text-xs">
            💡
          </div>
          <div className="flex-1">
            <p className="text-xs text-ui-supportText">Insights</p>
            <p className="text-sm font-semibold text-ui-bodyText">
              {project.counts?.insights || 0}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 flex items-center justify-center text-ui-supportText text-xs">
            📊
          </div>
          <div className="flex-1">
            <p className="text-xs text-ui-supportText">Signals</p>
            <p className="text-sm font-semibold text-ui-bodyText">
              {project.counts?.signals || 0}
            </p>
          </div>
        </div>
      </div>

      {/* Timestamp */}
      <div className="mt-4 pt-4 border-t border-ui-cardBorder">
        <p className="text-xs text-ui-supportText">
          Created {new Date(project.created_at).toLocaleDateString()}
        </p>
      </div>
    </button>
  )
}
