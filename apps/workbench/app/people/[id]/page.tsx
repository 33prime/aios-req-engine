'use client'

import { useState, useEffect } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import { Loader2, User, Activity, FileSearch, Sparkles } from 'lucide-react'
import { getStakeholder } from '@/lib/api'
import type { StakeholderDetail } from '@/types/workspace'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { StakeholderHeader } from './components/StakeholderHeader'
import { StakeholderOverviewTab } from './components/StakeholderOverviewTab'
import { StakeholderActivityTab } from './components/StakeholderActivityTab'
import { StakeholderEvidenceTab } from './components/StakeholderEvidenceTab'
import { StakeholderInsightsTab } from './components/StakeholderInsightsTab'

type TabId = 'overview' | 'activity' | 'evidence' | 'insights'

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
    getStakeholder(projectId, stakeholderId, true)
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

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'overview', label: 'Overview', icon: <User className="w-3.5 h-3.5" /> },
    { id: 'activity', label: 'Activity', icon: <Activity className="w-3.5 h-3.5" /> },
    { id: 'evidence', label: 'Evidence & Sources', icon: <FileSearch className="w-3.5 h-3.5" /> },
    { id: 'insights', label: 'Intelligence', icon: <Sparkles className="w-3.5 h-3.5" /> },
  ]

  if (loading) {
    return (
      <>
        <AppSidebar isCollapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <div className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
          <div className="text-center">
            <Loader2 className="w-8 h-8 text-[#3FAF7A] animate-spin mx-auto mb-3" />
            <p className="text-[13px] text-[#999]">Loading stakeholder...</p>
          </div>
        </div>
      </>
    )
  }

  if (error || !stakeholder) {
    return (
      <>
        <AppSidebar isCollapsed={sidebarCollapsed} onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)} />
        <div className="min-h-screen bg-[#F4F4F4] flex items-center justify-center transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
          <div className="text-center">
            <p className="text-[14px] text-[#666] mb-3">{error || 'Stakeholder not found'}</p>
            <button
              onClick={() => router.push('/people')}
              className="px-6 py-3 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
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
      <div className="min-h-screen bg-[#F4F4F4] transition-all duration-300" style={{ marginLeft: sidebarWidth }}>
        <div className="max-w-[1200px] mx-auto px-6 py-6">
          <StakeholderHeader
            stakeholder={stakeholder}
            onBack={() => router.push('/people')}
          />

          {/* Tabs */}
          <div className="border-b border-[#E5E5E5] mb-6">
            <div className="flex gap-6">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`inline-flex items-center gap-1.5 pb-2.5 text-[13px] font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'text-[#3FAF7A] border-[#3FAF7A]'
                      : 'text-[#999] border-transparent hover:text-[#666]'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Tab Content */}
          {activeTab === 'overview' && <StakeholderOverviewTab stakeholder={stakeholder} />}
          {activeTab === 'activity' && <StakeholderActivityTab />}
          {activeTab === 'evidence' && <StakeholderEvidenceTab projectId={projectId} stakeholderId={stakeholderId} />}
          {activeTab === 'insights' && <StakeholderInsightsTab stakeholder={stakeholder} />}
        </div>
      </div>
    </>
  )
}
