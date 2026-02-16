'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useSearchParams, useRouter } from 'next/navigation'
import { Loader2, User, Activity, FileSearch, Sparkles } from 'lucide-react'
import { getStakeholder, getStakeholderIntelligence, analyzeStakeholder } from '@/lib/api'
import type { StakeholderDetail, StakeholderIntelligenceProfile } from '@/types/workspace'
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
  const [intelligence, setIntelligence] = useState<StakeholderIntelligenceProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [analyzing, setAnalyzing] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadIntelligence = useCallback(async () => {
    if (!projectId || !stakeholderId) return null
    try {
      const data = await getStakeholderIntelligence(projectId, stakeholderId)
      setIntelligence(data)
      return data
    } catch {
      // No intelligence data yet — that's fine
      return null
    }
  }, [projectId, stakeholderId])

  useEffect(() => {
    if (!stakeholderId || !projectId) return
    setLoading(true)

    Promise.all([
      getStakeholder(projectId, stakeholderId, true),
      getStakeholderIntelligence(projectId, stakeholderId).catch(() => null),
    ])
      .then(([stakeholderData, intelligenceData]) => {
        setStakeholder(stakeholderData)
        setIntelligence(intelligenceData)
        setError(null)
      })
      .catch((err) => {
        console.error('Failed to load stakeholder:', err)
        setError('Failed to load stakeholder details')
      })
      .finally(() => setLoading(false))
  }, [stakeholderId, projectId])

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const handleAnalyze = useCallback(async () => {
    if (!projectId || !stakeholderId || analyzing) return
    setAnalyzing(true)

    try {
      await analyzeStakeholder(projectId, stakeholderId)

      // The agent loops through multiple enrichment tools in one run.
      // Poll every 5s, keep going while completeness is still increasing.
      // Stop after 2 consecutive polls with no change, or after 180s max.
      let elapsed = 0
      let lastScore: number | null = null
      let stableCount = 0

      pollRef.current = setInterval(async () => {
        elapsed += 5000
        try {
          const updated = await getStakeholderIntelligence(projectId, stakeholderId)
          if (updated) {
            setIntelligence(updated)

            if (lastScore !== null && updated.profile_completeness === lastScore) {
              stableCount++
            } else {
              stableCount = 0
            }
            lastScore = updated.profile_completeness

            // Reload stakeholder data on each poll (enrichment fields change)
            getStakeholder(projectId, stakeholderId, true)
              .then(setStakeholder)
              .catch(() => {})

            // Stop if score hasn't changed for 2 consecutive polls (10s stable)
            if (stableCount >= 2) {
              if (pollRef.current) clearInterval(pollRef.current)
              pollRef.current = null
              setAnalyzing(false)
              return
            }
          }
        } catch {
          // Keep polling on transient errors
        }

        if (elapsed >= 180000) {
          if (pollRef.current) clearInterval(pollRef.current)
          pollRef.current = null
          setAnalyzing(false)
          loadIntelligence()
        }
      }, 5000)
    } catch (err) {
      console.error('Failed to trigger analysis:', err)
      setAnalyzing(false)
    }
  }, [projectId, stakeholderId, analyzing, loadIntelligence])

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
            completeness={intelligence?.profile_completeness}
            analyzing={analyzing}
            onAnalyze={handleAnalyze}
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
          {activeTab === 'activity' && <StakeholderActivityTab projectId={projectId} stakeholderId={stakeholderId} />}
          {activeTab === 'evidence' && <StakeholderEvidenceTab projectId={projectId} stakeholderId={stakeholderId} />}
          {activeTab === 'insights' && (
            <StakeholderInsightsTab
              stakeholder={stakeholder}
              intelligence={intelligence}
              projectId={projectId}
              stakeholderId={stakeholderId}
            />
          )}
        </div>
      </div>
    </>
  )
}
