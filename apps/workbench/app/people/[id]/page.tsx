'use client'

import { useState, useEffect } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import { getStakeholder } from '@/lib/api'
import type { StakeholderDetail } from '@/types/workspace'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { StakeholderHeader } from './components/StakeholderHeader'
import { StakeholderOverviewTab } from './components/StakeholderOverviewTab'
import { StakeholderEnrichmentTab } from './components/StakeholderEnrichmentTab'

type TabId = 'overview' | 'enrichment'

export default function PersonDetailPage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const router = useRouter()
  const stakeholderId = params.id as string
  const projectId = searchParams.get('project_id') || ''

  const [stakeholder, setStakeholder] = useState<StakeholderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  useEffect(() => {
    if (!stakeholderId || !projectId) return
    setLoading(true)
    getStakeholder(projectId, stakeholderId)
      .then((data) => {
        setStakeholder(data)
        setError(null)
      })
      .catch((err) => {
        console.error('Failed to load stakeholder:', err)
        setError('Failed to load stakeholder details')
      })
      .finally(() => setLoading(false))
  }, [stakeholderId, projectId])

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  const tabs: { id: TabId; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'enrichment', label: 'Enrichment (AI)' },
  ]

  if (loading) {
    return (
      <>
        <AppSidebar isCollapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#009b87] mx-auto mb-4" />
            <p className="text-sm text-[rgba(55,53,47,0.45)]">Loading stakeholder...</p>
          </div>
        </div>
      </>
    )
  }

  if (error || !stakeholder) {
    return (
      <>
        <AppSidebar isCollapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <div className="min-h-screen bg-[#FAFAFA] flex items-center justify-center transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
          <div className="text-center">
            <p className="text-red-500 mb-3">{error || 'Stakeholder not found'}</p>
            <button
              onClick={() => router.push('/people')}
              className="px-4 py-2 text-sm text-white bg-[#009b87] rounded-md hover:bg-[#008474] transition-colors"
            >
              Back to People
            </button>
          </div>
        </div>
      </>
    )
  }

  return (
    <>
      <AppSidebar isCollapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="min-h-screen bg-[#FAFAFA] transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
        <div className="max-w-[800px] mx-auto px-4 py-6">
          <StakeholderHeader
            stakeholder={stakeholder}
            onBack={() => router.push('/people')}
          />

          {/* Tabs */}
          <div className="border-b border-gray-200 mb-6">
            <div className="flex gap-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`pb-2.5 text-[13px] font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'text-[#009b87] border-[#009b87]'
                      : 'text-[rgba(55,53,47,0.45)] border-transparent hover:text-[rgba(55,53,47,0.65)]'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            {activeTab === 'overview' && <StakeholderOverviewTab stakeholder={stakeholder} />}
            {activeTab === 'enrichment' && <StakeholderEnrichmentTab stakeholder={stakeholder} />}
          </div>
        </div>
      </div>
    </>
  )
}
