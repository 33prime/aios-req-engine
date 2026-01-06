/**
 * Main Workspace Page
 *
 * Unified 5-tab workspace for consultant workflow:
 * 1. Product Requirements - PRD sections with status tracking
 * 2. Value Path - VP steps with enrichment details
 * 3. Insights - Red team analysis with decision workflow
 * 4. Next Steps - Batched client confirmations
 * 5. Sources - Signal provenance and impact tracking
 *
 * Features:
 * - Tab navigation with counts
 * - Header with agent actions and research toggle
 * - Real-time data loading and updates
 * - Job polling for async operations
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { useParams } from 'next/navigation'
import { TabNavigation, MobileTabNavigation, type TabType } from './components/TabNavigation'
import { WorkspaceHeader, CompactHeader } from './components/WorkspaceHeader'
import { OverviewTab } from './components/tabs/OverviewTab'
import { StrategicContextTab } from './components/tabs/StrategicContextTab'
import { ValuePathTab } from './components/tabs/ValuePathTab'
import { EnhancedResearchTab } from './components/tabs/research/EnhancedResearchTab'
import { NextStepsTab } from './components/tabs/NextStepsTab'
import { PersonasFeaturesTab } from './components/tabs/PersonasFeaturesTab'
import { AddSignalModal } from './components/AddSignalModal'
import { AddResearchModal } from './components/AddResearchModal'
import { ResearchAgentModal } from './components/ResearchAgentModal'
import { ChatBubble } from './components/ChatBubble'
import { ChatPanel } from './components/ChatPanel'
import { ActivityDrawer } from './components/ActivityDrawer'
import { CreativeBriefModal } from './components/CreativeBriefModal'
import PatchFeed from './components/PatchFeed'
import CascadeSidebar from '@/components/cascades/CascadeSidebar'
import { AssistantProvider } from '@/lib/assistant'
import { getBaselineStatus, getBaselineCompleteness, finalizeBaseline, listConfirmations, getFeatures, getPrdSections, getVpSteps, getInsights, listProjectSignals, listPendingCascades, applyCascade, dismissCascade } from '@/lib/api'
import { useChat } from '@/lib/useChat'
import type { BaselineStatus } from '@/types/api'

export default function WorkspacePage() {
  const params = useParams()
  const projectId = params.projectId as string

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('overview')

  // Data state
  const [baseline, setBaseline] = useState<BaselineStatus | null>(null)
  const [baselineCompleteness, setBaselineCompleteness] = useState<any>(null)
  const [prdMode, setPrdMode] = useState<'initial' | 'maintenance'>('initial')
  const [counts, setCounts] = useState({
    strategicContext: 0,
    valuePath: 0,
    improvements: 0,
    nextSteps: 0,
    sources: 0,
    research: 0
  })
  const [recentChanges, setRecentChanges] = useState({
    strategicContext: 0,
    valuePath: 0,
    improvements: 0
  })
  const [loading, setLoading] = useState(true)
  const [loadingCompleteness, setLoadingCompleteness] = useState(true)

  // Modal state
  const [showAddSignal, setShowAddSignal] = useState(false)
  const [showAddResearch, setShowAddResearch] = useState(false)
  const [showResearchModal, setShowResearchModal] = useState(false)
  const [researchSeedContext, setResearchSeedContext] = useState({
    client_name: '',
    industry: '',
    competitors: [] as string[],
    focus_areas: [] as string[],
    custom_questions: [] as string[],
  })

  // Chat state
  const [isChatOpen, setIsChatOpen] = useState(false)
  const [isChatMinimized, setIsChatMinimized] = useState(false)
  const { messages, isLoading: isChatLoading, sendMessage, sendSignal } = useChat({
    projectId,
    onError: (error) => {
      console.error('Chat error:', error)
      alert('Failed to send message. Please try again.')
    },
  })

  // Modal/drawer state
  const [isActivityDrawerOpen, setIsActivityDrawerOpen] = useState(false)
  const [isCreativeBriefModalOpen, setIsCreativeBriefModalOpen] = useState(false)

  // Cascade state
  const [cascades, setCascades] = useState<any[]>([])
  const [isCascadeSidebarOpen, setIsCascadeSidebarOpen] = useState(false)

  // Load project data
  useEffect(() => {
    loadProjectData()
  }, [projectId])

  // Load baseline completeness
  useEffect(() => {
    loadBaselineCompleteness()
  }, [projectId])

  const loadBaselineCompleteness = async () => {
    try {
      setLoadingCompleteness(true)
      const data = await getBaselineCompleteness(projectId)
      // Extract prd_mode from response
      const { prd_mode, ...completeness } = data
      setBaselineCompleteness(completeness)
      setPrdMode(prd_mode)
      console.log('✅ Baseline completeness loaded:', data)
    } catch (error) {
      console.error('❌ Failed to load baseline completeness:', error)
    } finally {
      setLoadingCompleteness(false)
    }
  }

  const handleFinalizeBaseline = async () => {
    try {
      await finalizeBaseline(projectId)
      console.log('✅ Baseline finalized')
      // Reload completeness data
      await loadBaselineCompleteness()
      await loadProjectData()
    } catch (error) {
      console.error('❌ Failed to finalize baseline:', error)
      throw error
    }
  }

  const loadProjectData = async () => {
    try {
      setLoading(true)
      console.log('🔄 Loading workspace data for:', projectId)

      const [
        baselineData,
        prdData,
        vpData,
        insightsData,
        patchesResponse,
        confirmationsData,
        signalsData,
        researchJobsResponse,
      ] = await Promise.all([
        getBaselineStatus(projectId),
        getPrdSections(projectId),
        getVpSteps(projectId),
        getInsights(projectId),
        fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/insights?project_id=${projectId}&insight_type=patch`).then(r => r.json()),
        listConfirmations(projectId, 'open'),
        listProjectSignals(projectId),
        fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/jobs?project_id=${projectId}&job_type=research_query&limit=50`).then(r => r.json()),
      ])

      setBaseline(baselineData)

      // Handle patches response (could be array or object with patches property)
      const patchesData = Array.isArray(patchesResponse) ? patchesResponse : patchesResponse.patches || []

      // Calculate combined improvements count (insights + patches)
      const totalImprovements = insightsData.length + patchesData.length

      // Update counts (strategicContext count stays at 0 for now - will be updated when we add strategic context API)
      const researchJobs = Array.isArray(researchJobsResponse) ? researchJobsResponse : researchJobsResponse.jobs || []
      setCounts({
        strategicContext: 0, // TODO: Update when strategic context API is connected
        valuePath: vpData.length,
        improvements: totalImprovements,
        nextSteps: confirmationsData.confirmations?.length || 0,
        sources: signalsData.total || 0,
        research: researchJobs.length
      })

      // Calculate recent changes (entities updated in last 24 hours)
      const cutoff = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
      const recentInsights = insightsData.filter((i: any) => i.updated_at > cutoff).length
      const recentPatches = patchesData.filter((p: any) => p.updated_at > cutoff).length

      setRecentChanges({
        strategicContext: 0, // TODO: Update when strategic context API is connected
        valuePath: vpData.filter((v: any) => v.updated_at > cutoff).length,
        improvements: recentInsights + recentPatches
      })

      console.log('✅ Workspace data loaded:', {
        prd: prdData.length,
        vp: vpData.length,
        improvements: totalImprovements,
        confirmations: confirmationsData.confirmations?.length || 0,
        sources: signalsData.total || 0
      })
    } catch (error) {
      console.error('❌ Failed to load workspace data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle baseline toggle
  const handleBaselineToggle = async () => {
    if (!baseline) return

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/projects/${projectId}/baseline`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ baseline_ready: !baseline.baseline_ready }),
      })

      if (response.ok) {
        const updated = await response.json()
        setBaseline(updated)
        console.log('✅ Baseline toggled:', updated.baseline_ready)
      }
    } catch (error) {
      console.error('❌ Failed to toggle baseline:', error)
      alert('Failed to toggle research access')
    }
  }

  // Load cascades
  const loadCascades = async () => {
    try {
      const data = await listPendingCascades(projectId)
      setCascades(data.cascades || [])
    } catch (error) {
      console.error('Failed to load cascades:', error)
    }
  }

  // Load cascades on mount
  useEffect(() => {
    loadCascades()
  }, [projectId])

  // Cascade handlers
  const handleApplyCascade = async (cascadeId: string) => {
    try {
      await applyCascade(cascadeId)
      setCascades(prev => prev.filter(c => c.id !== cascadeId))
      loadProjectData() // Refresh data after applying cascade
      loadCascades() // Refresh cascades in case more were created
    } catch (error) {
      console.error('Failed to apply cascade:', error)
    }
  }

  const handleDismissCascade = async (cascadeId: string) => {
    try {
      await dismissCascade(cascadeId)
      setCascades(prev => prev.filter(c => c.id !== cascadeId))
    } catch (error) {
      console.error('Failed to dismiss cascade:', error)
    }
  }

  // Handle agent runs
  const handleRunAgent = async (agentType: 'build' | 'reconcile' | 'redteam' | 'enrich-prd' | 'enrich-vp' | 'research') => {
    try {
      console.log('🚀 Running agent:', agentType)

      // Research agent shows modal first
      if (agentType === 'research') {
        setShowResearchModal(true)
        return
      }

      let endpoint = ''
      let body: any = { project_id: projectId }

      switch (agentType) {
        case 'build':
          endpoint = '/v1/state/build'
          break
        case 'reconcile':
          endpoint = '/v1/state/reconcile'
          body.include_research = baseline?.baseline_ready
          break
        case 'redteam':
          endpoint = '/v1/agents/red-team'
          body.include_research = baseline?.baseline_ready
          break
        case 'enrich-prd':
          endpoint = '/v1/agents/enrich-prd'
          body.include_research = baseline?.baseline_ready
          break
        case 'enrich-vp':
          endpoint = '/v1/agents/enrich-vp'
          body.include_research = baseline?.baseline_ready
          break
      }

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (response.ok) {
        const result = await response.json()
        console.log('✅ Agent started:', result)

        // Poll job status
        if (result.job_id) {
          pollJobStatus(result.job_id, agentType)
        }
      } else {
        throw new Error(`Failed to run ${agentType} agent`)
      }
    } catch (error) {
      console.error(`❌ Failed to run ${agentType} agent:`, error)
      alert(`Failed to run ${agentType} agent`)
    }
  }

  // Handle research agent submission
  const handleSubmitResearch = async () => {
    try {
      console.log('🚀 Running Research Agent:', researchSeedContext)
      setShowResearchModal(false)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/agents/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          seed_context: researchSeedContext,
          max_queries: 15,
        }),
      })

      if (response.ok) {
        const result = await response.json()
        console.log('✅ Research Agent started:', result)

        if (result.job_id) {
          pollJobStatus(result.job_id, 'research')
        }
      } else {
        throw new Error(await response.text())
      }
    } catch (error) {
      console.error('❌ Failed to run research agent:', error)
      alert('Failed to start research agent')
    }
  }

  // Poll job status
  const pollJobStatus = async (jobId: string, agentType: string) => {
    console.log('🔍 Polling job:', jobId)
    let pollCount = 0
    const maxPolls = 30 // 1 minute max

    const checkStatus = async () => {
      pollCount++

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/jobs/${jobId}`)
        if (response.ok) {
          const job = await response.json()

          if (job.status === 'completed') {
            console.log('✅ Job completed:', job)

            // Show agent-specific success message
            if (agentType === 'research') {
              const findings = job.output?.findings_summary || {}
              const total = Object.values(findings).reduce((sum: number, val: any) => sum + (val || 0), 0)
              alert(`Research completed! Generated ${total} findings across ${job.output?.queries_executed || 0} queries.`)
            } else {
              alert(`${agentType} completed successfully!`)
            }

            loadProjectData() // Refresh data
            loadCascades() // Refresh cascades (may have new conflicts/suggestions)
          } else if (job.status === 'failed') {
            console.log('❌ Job failed:', job.error)
            alert(`${agentType} failed: ${job.error}`)
          } else if (pollCount >= maxPolls) {
            console.log('⏰ Job polling timeout')
            alert('Job is taking longer than expected. Check back later.')
          } else {
            // Still running, check again in 2 seconds
            setTimeout(checkStatus, 2000)
          }
        }
      } catch (error) {
        console.error('❌ Failed to check job status:', error)
      }
    }

    checkStatus()
  }

  // Render active tab content
  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewTab projectId={projectId} isActive={activeTab === 'overview'} />
      case 'strategic-context':
        return <StrategicContextTab projectId={projectId} />
      case 'personas-features':
        return <PersonasFeaturesTab projectId={projectId} isActive={activeTab === 'personas-features'} />
      case 'value-path':
        return <ValuePathTab projectId={projectId} />
      case 'research':
        return <EnhancedResearchTab projectId={projectId} />
      case 'next-steps':
        return <NextStepsTab projectId={projectId} />
      default:
        return null
    }
  }

  // Build project data for assistant context - memoized to prevent infinite loops
  const assistantProjectData = useMemo(() => ({
    readinessScore: baselineCompleteness?.overall_score ?? 0,
    blockers: baselineCompleteness?.blockers ?? [],
    warnings: baselineCompleteness?.warnings ?? [],
    pendingConfirmations: counts.nextSteps,
    stats: {
      features: baselineCompleteness?.features_count ?? 0,
      personas: baselineCompleteness?.personas_count ?? 0,
      vpSteps: counts.valuePath,
      signals: counts.sources,
    },
  }), [
    baselineCompleteness?.overall_score,
    baselineCompleteness?.blockers,
    baselineCompleteness?.warnings,
    baselineCompleteness?.features_count,
    baselineCompleteness?.personas_count,
    counts.nextSteps,
    counts.valuePath,
    counts.sources,
  ])

  if (loading) {
    return (
      <div className="min-h-screen bg-ui-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
          <p className="text-support text-ui-supportText">Loading workspace...</p>
        </div>
      </div>
    )
  }

  return (
    <AssistantProvider projectId={projectId} initialProjectData={assistantProjectData}>
    <div className="min-h-screen bg-ui-background">
      {/* Desktop Header */}
      <div className="hidden lg:block">
        <div className="bg-white border-b border-gray-200">
          {/* PRD Mode Badge */}
          <div className="px-6 py-2 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-600">Project Mode:</span>
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                  prdMode === 'maintenance'
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-gray-100 text-gray-800'
                }`}
              >
                {prdMode === 'maintenance' ? '🔧 Maintenance (Surgical Updates)' : '🌱 Initial (Generative)'}
              </span>
            </div>
          </div>

          <WorkspaceHeader
            projectId={projectId}
            baseline={baseline}
            baselineCompleteness={baselineCompleteness}
            prdMode={prdMode}
            onBaselineToggle={handleBaselineToggle}
            onFinalizeBaseline={handleFinalizeBaseline}
            onRefresh={loadProjectData}
            onAddSignal={() => setShowAddSignal(true)}
            onAddResearch={() => setShowAddResearch(true)}
            onShowActivity={() => setIsActivityDrawerOpen(true)}
            onShowCreativeBrief={() => setIsCreativeBriefModalOpen(true)}
          />
        </div>
      </div>

      {/* Mobile Header */}
      <div className="lg:hidden">
        <CompactHeader
          projectId={projectId}
          onRefresh={loadProjectData}
        />
      </div>

      {/* Desktop Tab Navigation */}
      <div className="hidden lg:block">
        <TabNavigation
          activeTab={activeTab}
          onTabChange={setActiveTab}
          counts={counts}
          recentChanges={recentChanges}
        />
      </div>

      {/* Mobile Tab Navigation */}
      <div className="lg:hidden">
        <MobileTabNavigation
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </div>

      {/* Tab Content - Full Width */}
      <main className="max-w-[1600px] mx-auto px-4 lg:px-6 py-6">
        {renderTabContent()}
      </main>

      {/* Modals */}
      <AddSignalModal
        isOpen={showAddSignal}
        onClose={() => setShowAddSignal(false)}
        projectId={projectId}
        onSuccess={loadProjectData}
      />
      <AddResearchModal
        isOpen={showAddResearch}
        onClose={() => setShowAddResearch(false)}
        projectId={projectId}
        onSuccess={loadProjectData}
      />
      {showResearchModal && (
        <ResearchAgentModal
          projectId={projectId}
          seedContext={researchSeedContext}
          onUpdate={setResearchSeedContext}
          onSubmit={handleSubmitResearch}
          onClose={() => setShowResearchModal(false)}
        />
      )}

      {/* Chat Assistant - Floating */}
      {!isChatOpen && (
        <ChatBubble
          isOpen={isChatOpen}
          onToggle={() => {
            setIsChatOpen(true)
            setIsChatMinimized(false)
          }}
        />
      )}
      <ChatPanel
        isOpen={isChatOpen}
        onClose={() => {
          setIsChatOpen(false)
          setIsChatMinimized(false)
        }}
        projectId={projectId}
        messages={messages}
        isLoading={isChatLoading}
        onSendMessage={sendMessage}
        onSendSignal={sendSignal}
        activeTab={activeTab}
        isMinimized={isChatMinimized}
        onToggleMinimize={() => setIsChatMinimized(!isChatMinimized)}
      />

      {/* Activity Drawer */}
      <ActivityDrawer
        projectId={projectId}
        isOpen={isActivityDrawerOpen}
        onClose={() => setIsActivityDrawerOpen(false)}
      />

      {/* Creative Brief Modal */}
      <CreativeBriefModal
        projectId={projectId}
        isOpen={isCreativeBriefModalOpen}
        onClose={() => setIsCreativeBriefModalOpen(false)}
      />

      {/* Cascade Sidebar */}
      <CascadeSidebar
        cascades={cascades}
        isOpen={isCascadeSidebarOpen}
        onToggle={() => setIsCascadeSidebarOpen(!isCascadeSidebarOpen)}
        onApply={handleApplyCascade}
        onDismiss={handleDismissCascade}
      />
    </div>
    </AssistantProvider>
  )
}
