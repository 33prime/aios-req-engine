'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { listAllStakeholders, listProjects, createStakeholder } from '@/lib/api'
import type { StakeholderDetail } from '@/types/workspace'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { PeopleTopNav } from './components/PeopleTopNav'
import { PeopleTable } from './components/PeopleTable'
import { StakeholderCreateModal } from './components/StakeholderCreateModal'

export default function PeoplePage() {
  const router = useRouter()
  const [stakeholders, setStakeholders] = useState<StakeholderDetail[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState('all')
  const [influenceFilter, setInfluenceFilter] = useState('all')
  const [projectFilter, setProjectFilter] = useState('all')
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([])
  const [showCreate, setShowCreate] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const params: Record<string, string | number> = { limit: 100 }
      if (searchQuery) params.search = searchQuery
      if (typeFilter !== 'all') params.stakeholder_type = typeFilter
      if (influenceFilter !== 'all') params.influence_level = influenceFilter
      if (projectFilter !== 'all') params.project_id = projectFilter

      const result = await listAllStakeholders(params as any)
      setStakeholders(result.stakeholders)
      setTotal(result.total)
    } catch (error) {
      console.error('Failed to load stakeholders:', error)
    } finally {
      setLoading(false)
    }
  }, [searchQuery, typeFilter, influenceFilter, projectFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    listProjects('active')
      .then((res) => setProjects(res.projects.map((p) => ({ id: p.id, name: p.name }))))
      .catch(() => {})
  }, [])

  const handleRowClick = (stakeholder: StakeholderDetail) => {
    router.push(`/people/${stakeholder.id}?project_id=${stakeholder.project_id}`)
  }

  const handleCreatePerson = async (projectId: string, data: any) => {
    try {
      await createStakeholder(projectId, data)
      setShowCreate(false)
      loadData()
    } catch (error) {
      console.error('Failed to create stakeholder:', error)
    }
  }

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  if (loading && stakeholders.length === 0) {
    return (
      <>
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
        <div
          className="min-h-screen bg-surface-page flex items-center justify-center transition-all duration-300"
          style={{ marginLeft: sidebarWidth }}
        >
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#009b87] mx-auto mb-4" />
            <p className="text-sm text-text-placeholder">Loading people...</p>
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
        className="min-h-screen bg-surface-page transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="max-w-[1400px] mx-auto px-4 py-4">
          <PeopleTopNav
            searchQuery={searchQuery}
            typeFilter={typeFilter}
            influenceFilter={influenceFilter}
            projectFilter={projectFilter}
            projects={projects}
            onSearchChange={setSearchQuery}
            onTypeFilterChange={setTypeFilter}
            onInfluenceFilterChange={setInfluenceFilter}
            onProjectFilterChange={setProjectFilter}
            onRefresh={loadData}
            onCreatePerson={() => setShowCreate(true)}
          />

          <div className="mb-3 text-[12px] text-text-placeholder">
            {total} {total === 1 ? 'person' : 'people'} found
          </div>

          <PeopleTable
            stakeholders={stakeholders}
            onRowClick={handleRowClick}
          />
        </div>
      </div>

      <StakeholderCreateModal
        open={showCreate}
        projects={projects}
        onClose={() => setShowCreate(false)}
        onSave={handleCreatePerson}
      />
    </>
  )
}
