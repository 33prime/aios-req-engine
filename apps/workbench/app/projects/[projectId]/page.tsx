/**
 * Main Workspace Page
 *
 * Unified workspace for consultant workflow with tabs:
 * - Overview - Project dashboard with status and tasks
 * - Strategic Foundation - PRD sections and context
 * - Personas & Features - User personas and feature specs
 * - Value Path - User journey steps
 * - Sources - Signals and research
 * - Next Steps - Confirmations and actions
 *
 * Features:
 * - Clean header with project info, stage, and portal status
 * - Tab navigation with counts
 * - Chat assistant for adding signals/research
 * - Activity drawer
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { useParams } from 'next/navigation'
import { TabNavigation, MobileTabNavigation, type TabType } from './components/TabNavigation'
import { WorkspaceHeader, CompactHeader } from './components/WorkspaceHeader'
import { OverviewTab } from './components/tabs/OverviewTab'
import { StrategicFoundationTab } from './components/tabs/StrategicFoundationTab'
import { ValuePathTab } from './components/tabs/ValuePathTab'
import { EnhancedResearchTab } from './components/tabs/research/EnhancedResearchTab'
import { NextStepsTab } from './components/tabs/NextStepsTab'
import { PersonasFeaturesTab } from './components/tabs/PersonasFeaturesTab'
import { ResearchAgentModal } from './components/ResearchAgentModal'
import { ChatBubble } from './components/ChatBubble'
import { ChatPanel } from './components/ChatPanel'
import { ActivityDrawer } from './components/ActivityDrawer'
import CascadeSidebar from '@/components/cascades/CascadeSidebar'
import { AssistantProvider } from '@/lib/assistant'
import { getBaselineStatus, getBaselineCompleteness, getProjectDetails, listConfirmations, listProjectSignals, listPendingCascades, applyCascade, dismissCascade } from '@/lib/api'
import { useChat } from '@/lib/useChat'
import type { BaselineStatus, ProjectDetailWithDashboard } from '@/types/api'

export default function WorkspacePage() {
  const params = useParams()
  const projectId = params.projectId as string

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('overview')

  // Project data state
  const [project, setProject] = useState<ProjectDetailWithDashboard | null>(null)
  const [baseline, setBaseline] = useState<BaselineStatus | null>(null)
  const [baselineCompleteness, setBaselineCompleteness] = useState<any>(null)
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

  // Research modal state
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

  // Drawer state
  const [isActivityDrawerOpen, setIsActivityDrawerOpen] = useState(false)

  // Cascade state
  const [cascades, setCascades] = useState<any[]>([])
  const [isCascadeSidebarOpen, setIsCascadeSidebarOpen] = useState(false)

  // Load all project data in a single consolidated effect
  useEffect(() => {
    loadProjectData()
  }, [projectId])

  const loadProjectData = async () => {
    try {
      setLoading(true)

      // Fetch only what's needed for header + tab counts
      // Individual tabs will load their own detailed data
      const [
        projectData,
        baselineData,
        completenessData,
        confirmationsData,
        signalsData,
        cascadesData,
      ] = await Promise.all([
        getProjectDetails(projectId),
        getBaselineStatus(projectId),
        getBaselineCompleteness(projectId).catch(() => null),
        listConfirmations(projectId, 'open'),
        listProjectSignals(projectId),
        listPendingCascades(projectId).catch(() => ({ cascades: [] })),
      ])

      setProject(projectData)
      setBaseline(baselineData)
      setBaselineCompleteness(completenessData)
      setCascades(cascadesData.cascades || [])

      // Use counts from project details (already includes vp_steps, features, etc.)
      const projectCounts = projectData.counts || {}
      setCounts({
        strategicContext: projectCounts.prd_sections || 0,
        valuePath: projectCounts.vp_steps || 0,
        improvements: 0,
        nextSteps: confirmationsData.confirmations?.length || 0,
        sources: signalsData.total || 0,
        research: 0
      })

      // Reset recent changes (not critical for initial load)
      setRecentChanges({
        strategicContext: 0,
        valuePath: 0,
        improvements: 0
      })
    } catch (error) {
      console.error('Failed to load workspace data:', error)
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

  // Cascade handlers
  const handleApplyCascade = async (cascadeId: string) => {
    try {
      await applyCascade(cascadeId)
      setCascades(prev => prev.filter(c => c.id !== cascadeId))
      loadProjectData() // Refresh all data including cascades
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
  const handleRunAgent = async (agentType: 'build' | 'reconcile' | 'enrich-prd' | 'enrich-vp' | 'research') => {
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

            loadProjectData() // Refresh all data including cascades
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
        return (
          <OverviewTab
            projectId={projectId}
            isActive={activeTab === 'overview'}
          />
        )
      case 'strategic-foundation':
        return <StrategicFoundationTab projectId={projectId} />
      case 'personas-features':
        return <PersonasFeaturesTab projectId={projectId} isActive={activeTab === 'personas-features'} />
      case 'value-path':
        return <ValuePathTab projectId={projectId} />
      case 'sources':
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
        <WorkspaceHeader
          projectId={projectId}
          projectName={project?.name || 'Loading...'}
          clientName={project?.client_name}
          stage={project?.stage}
          portalEnabled={project?.portal_enabled}
          onShowActivity={() => setIsActivityDrawerOpen(true)}
        />
      </div>

      {/* Mobile Header */}
      <div className="lg:hidden">
        <CompactHeader
          projectName={project?.name || 'Loading...'}
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

      {/* Research Agent Modal */}
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
