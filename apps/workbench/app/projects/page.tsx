/**
 * Projects Overview - Daily Snapshot
 *
 * Dashboard showing all projects with:
 * - Welcome header with date
 * - Project cards with stage, readiness, next steps, gaps
 * - Upcoming meetings sidebar
 */

'use client'

import React, { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Search, FolderOpen } from 'lucide-react'
import { listProjects, listUpcomingMeetings, getReadinessScore } from '@/lib/api'
import type { ProjectDetailWithDashboard, Meeting } from '@/types/api'
import { SmartProjectCreation } from './components/SmartProjectCreation'
import { OnboardingModal } from './components/OnboardingModal'
import { ProjectCard } from './components/ProjectCard'
import { MeetingCard } from './components/MeetingCard'

function formatDate() {
  const now = new Date()
  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

  return `${days[now.getDay()]}, ${months[now.getMonth()]} ${now.getDate()}`
}

export default function ProjectsPage() {
  const router = useRouter()
  const [projects, setProjects] = useState<ProjectDetailWithDashboard[]>([])
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [readinessScores, setReadinessScores] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'active' | 'archived' | 'all'>('active')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [onboardingProject, setOnboardingProject] = useState<{
    id: string
    name: string
    jobId: string
  } | null>(null)

  useEffect(() => {
    loadData()
  }, [statusFilter])

  const loadData = async () => {
    try {
      setLoading(true)

      // Load projects and meetings in parallel
      const status = statusFilter === 'all' ? undefined : statusFilter
      const [projectsData, meetingsData] = await Promise.all([
        listProjects(status, searchQuery),
        listUpcomingMeetings(10),
      ])

      const projectsList = projectsData.projects as ProjectDetailWithDashboard[]
      setProjects(projectsList)
      setMeetings(meetingsData)

      // Show page immediately - don't wait for readiness scores
      setLoading(false)

      // Fetch readiness scores in background (don't block page load)
      projectsList.forEach(async (project) => {
        try {
          const readiness = await getReadinessScore(project.id)
          setReadinessScores(prev => ({ ...prev, [project.id]: readiness.score }))
        } catch {
          setReadinessScores(prev => ({ ...prev, [project.id]: 0 }))
        }
      })
    } catch (error) {
      console.error('Failed to load data:', error)
      setLoading(false)
    }
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    loadData()
  }

  const handleProjectClick = (projectId: string) => {
    router.push(`/projects/${projectId}`)
  }

  const handleProjectCreated = (response: any) => {
    setShowCreateModal(false)
    if (response.onboarding_job_id) {
      setOnboardingProject({
        id: response.id,
        name: response.name,
        jobId: response.onboarding_job_id,
      })
    } else {
      router.push(`/projects/${response.id}`)
    }
  }

  const handleOnboardingComplete = () => {
    if (onboardingProject) {
      const projectId = onboardingProject.id
      setOnboardingProject(null)
      router.push(`/projects/${projectId}`)
    }
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#009b87] mx-auto mb-4"></div>
          <p className="text-sm text-gray-500">Loading projects...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-[1600px] mx-auto px-6 py-8">
        {/* Daily Snapshot Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Daily Snapshot</h1>
          <p className="text-gray-600">
            Welcome back! Here&apos;s the latest for <span className="font-medium text-gray-900">{formatDate()}</span>.
          </p>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Left Column - Projects */}
          <div className="lg:col-span-3">
            {/* Section Header with Actions */}
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-gray-900">Latest Projects</h2>
              <div className="flex items-center gap-3">
                {/* Search */}
                <form onSubmit={handleSearch} className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9 pr-4 py-2 w-48 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
                  />
                </form>

                {/* Status Filter */}
                <div className="flex border border-gray-300 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setStatusFilter('active')}
                    className={`px-3 py-2 text-sm font-medium transition-colors ${
                      statusFilter === 'active'
                        ? 'bg-[#009b87] text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Active
                  </button>
                  <button
                    onClick={() => setStatusFilter('archived')}
                    className={`px-3 py-2 text-sm font-medium transition-colors border-l border-gray-300 ${
                      statusFilter === 'archived'
                        ? 'bg-[#009b87] text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Archived
                  </button>
                </div>

                {/* New Project Button */}
                <button
                  onClick={() => setShowCreateModal(true)}
                  className="flex items-center gap-2 px-4 py-2 bg-[#009b87] text-white rounded-lg hover:bg-[#007a6b] transition-colors text-sm font-medium"
                >
                  <Plus className="w-4 h-4" />
                  New Project
                </button>
              </div>
            </div>

            {/* Projects List */}
            {filteredProjects.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <FolderOpen className="w-8 h-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  No projects found
                </h3>
                <p className="text-gray-600 text-sm mb-6">
                  {searchQuery
                    ? 'Try adjusting your search'
                    : 'Get started by creating your first project'}
                </p>
                {!searchQuery && (
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-[#009b87] text-white rounded-lg hover:bg-[#007a6b] transition-colors text-sm font-medium"
                  >
                    <Plus className="w-4 h-4" />
                    Create Project
                  </button>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                {filteredProjects.map((project) => (
                  <ProjectCard
                    key={project.id}
                    project={project}
                    readinessScore={readinessScores[project.id]}
                    onClick={() => handleProjectClick(project.id)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Right Column - Upcoming Meetings */}
          <div className="lg:col-span-1">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Upcoming Meetings</h2>

            {meetings.length === 0 ? (
              <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
                <p className="text-sm text-gray-500">No upcoming meetings</p>
              </div>
            ) : (
              <div className="space-y-3">
                {meetings.map((meeting) => (
                  <MeetingCard
                    key={meeting.id}
                    meeting={meeting}
                    onClick={() => router.push(`/projects/${meeting.project_id}?tab=meetings`)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Smart Project Creation Chat */}
      <SmartProjectCreation
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSuccess={handleProjectCreated}
      />

      {/* Onboarding Modal */}
      {onboardingProject && (
        <OnboardingModal
          isOpen={true}
          projectId={onboardingProject.id}
          projectName={onboardingProject.name}
          jobId={onboardingProject.jobId}
          onComplete={handleOnboardingComplete}
        />
      )}
    </div>
  )
}
