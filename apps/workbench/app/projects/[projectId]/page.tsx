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

import { useState, useEffect, useMemo, useRef } from 'react'
import { useParams } from 'next/navigation'
import { TabNavigation, MobileTabNavigation, type TabType } from './components/TabNavigation'
import { WorkspaceHeader, CompactHeader } from './components/WorkspaceHeader'
import { OverviewTab } from './components/tabs/OverviewTab'
import { StrategicFoundationTab } from './components/tabs/StrategicFoundationTab'
import { ValuePathTab } from './components/tabs/ValuePathTab'
import { EnhancedResearchTab } from './components/tabs/research/EnhancedResearchTab'
import { CollaborationTab } from './components/tabs/CollaborationTab'
import { PersonasFeaturesTab } from './components/tabs/PersonasFeaturesTab'
import { ResearchAgentModal } from './components/ResearchAgentModal'
import { ChatBubble } from './components/ChatBubble'
import { ChatPanel } from './components/ChatPanel'
import { ActivityDrawer } from './components/ActivityDrawer'
import CascadeSidebar from '@/components/cascades/CascadeSidebar'
import { AssistantProvider } from '@/lib/assistant'
import { getBaselineStatus, getProjectDetails, listConfirmations, listProjectSignals, listPendingCascades, applyCascade, dismissCascade, getTaskStats } from '@/lib/api'
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

  // Track processed signals to prevent infinite reload loops
  const processedSignalsRef = useRef<Set<string>>(new Set())

  // Cascade state
  const [cascades, setCascades] = useState<any[]>([])
  const [isCascadeSidebarOpen, setIsCascadeSidebarOpen] = useState(false)

  // Load all project data in a single consolidated effect
  useEffect(() => {
    loadProjectData()
  }, [projectId])

  // Watch for signal processing completion and trigger refresh
  useEffect(() => {
    // Find the most recent add_signal tool call
    const lastMessage = messages[messages.length - 1]
    if (!lastMessage || lastMessage.role !== 'assistant') return

    const addSignalTool = lastMessage.toolCalls?.find(
      (tc) => tc.tool_name === 'add_signal' && tc.status === 'complete'
    )

    if (addSignalTool && addSignalTool.result?.signal_id) {
      const result = addSignalTool.result
      const signalId = result.signal_id

      // Skip if we've already processed this signal (prevents infinite loop)
      if (processedSignalsRef.current.has(signalId)) {
        return
      }

      // Check if processing already completed (synchronous path)
      if (result.processed === true) {
        // Mark as processed BEFORE calling loadProjectData to prevent re-entry
        processedSignalsRef.current.add(signalId)

        console.log('✅ Signal processed synchronously:', signalId)
        if (result.proposal_id) {
          console.log(`📋 Bulk proposal created: ${result.proposal_id} with ${result.total_changes || 0} changes`)
        } else if (result.features_created || result.personas_created || result.vp_steps_created) {
          console.log(`📝 Entities created: ${result.features_created || 0} features, ${result.personas_created || 0} personas, ${result.vp_steps_created || 0} VP steps`)
        }
        // Refresh data immediately since processing is done
        loadProjectData()
        return
      }

      // Processing was deferred or failed - check if we need to poll
      if (result.processed === false && result.pipeline_error) {
        // Mark as processed to prevent re-entry
        processedSignalsRef.current.add(signalId)

        console.error('❌ Signal processing failed:', result.pipeline_error)
        // Still refresh to show the signal was added
        loadProjectData()
        return
      }

      // Only poll if processing was explicitly deferred (process_immediately=false)
      // Mark as processed before starting polling
      processedSignalsRef.current.add(signalId)

      console.log('📥 Signal added, starting polling for:', signalId)
      pollSignalStatus(signalId)
    }
  }, [messages])

  const loadProjectData = async () => {
    try {
      setLoading(true)

      // FAST PATH: Only load project details first (has counts, cached readiness)
      const projectData = await getProjectDetails(projectId)
      setProject(projectData)

      // Use counts from project details (already includes vp_steps, features, etc.)
      const projectCounts = projectData.counts || {}
      setCounts({
        strategicContext: 0, // Strategic foundation is separate from PRD sections
        valuePath: projectCounts.vp_steps || 0,
        improvements: 0,
        nextSteps: 0, // Will update in background
        sources: projectCounts.signals || 0,
        research: 0
      })

      // Show page immediately
      setLoading(false)

      // BACKGROUND: Load secondary data without blocking
      loadSecondaryData()
    } catch (error) {
      console.error('Failed to load workspace data:', error)
      setLoading(false)
    }
  }

  const loadSecondaryData = async () => {
    // Load secondary data in parallel, don't block page
    try {
      const [baselineData, confirmationsData, cascadesData, taskStatsData] = await Promise.all([
        getBaselineStatus(projectId).catch(() => ({ baseline_ready: false })),
        listConfirmations(projectId, 'open').catch(() => ({ confirmations: [] })),
        listPendingCascades(projectId).catch(() => ({ cascades: [] })),
        getTaskStats(projectId).catch(() => ({ by_status: { pending: 0 }, client_relevant: 0 })),
      ])

      setBaseline(baselineData)
      setCascades(cascadesData.cascades || [])

      // Update collaboration count (confirmations + pending client tasks)
      const confirmationCount = confirmationsData.confirmations?.length || 0
      const clientTaskCount = taskStatsData.client_relevant || 0
      setCounts(prev => ({
        ...prev,
        nextSteps: confirmationCount + clientTaskCount,
      }))
    } catch (error) {
      console.error('Failed to load secondary data:', error)
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
  const handleRunAgent = async (agentType: 'build' | 'reconcile' | 'enrich-vp' | 'research') => {
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

  // Poll signal processing status (fallback for deferred/streaming processing)
  const pollSignalStatus = async (signalId: string) => {
    console.log('📥 Signal processing deferred - polling for completion:', signalId)
    let pollCount = 0
    const maxPolls = 20 // ~1 minute max (reduced since sync path is primary)

    const checkStatus = async () => {
      pollCount++

      try {
        // Check signal details to see if processing is complete
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/signals/${signalId}`)
        if (response.ok) {
          const signal = await response.json()

          // Check for proposal creation (heavyweight signals)
          const hasProposal = signal.batch_proposal_id || signal.proposal_id

          // Check for direct impacts (lightweight signals or auto-applied)
          const impactResponse = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/signals/${signalId}/impact`)
          const impact = impactResponse.ok ? await impactResponse.json() : { total_impacts: 0 }
          const totalImpacts = impact.total_impacts || 0

          // Processing is complete if we have either a proposal OR impacts
          if (hasProposal || totalImpacts > 0) {
            if (hasProposal) {
              console.log(`📋 Signal processing complete! Proposal created for review`)
            }
            if (totalImpacts > 0) {
              console.log(`✅ Signal processing complete! ${totalImpacts} entities created/updated`)
            }

            // Refresh project data to show new entities or proposals
            loadProjectData()

            // Don't continue polling
            return
          }

          // Check max polls - still refresh in case entities were created without impact tracking
          if (pollCount >= maxPolls) {
            console.log('⏰ Signal processing timeout - may still be running in background')
            // Refresh anyway in case something was created
            loadProjectData()
            return
          }

          // Still processing, check again in 3 seconds
          setTimeout(checkStatus, 3000)
        } else {
          console.error('Failed to fetch signal status:', response.statusText)
        }
      } catch (error) {
        console.error('❌ Failed to check signal status:', error)
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
            cachedNarrative={project?.status_narrative || null}
            cachedReadinessData={project?.cached_readiness_data as any}
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
      case 'collaboration':
        return <CollaborationTab projectId={projectId} />
      default:
        return null
    }
  }

  // Build project data for assistant context - memoized to prevent infinite loops
  const assistantProjectData = useMemo(() => ({
    readinessScore: project?.readiness_score ?? 0,
    blockers: [],
    warnings: [],
    pendingConfirmations: counts.nextSteps,
    stats: {
      features: project?.counts?.features ?? 0,
      personas: project?.counts?.personas ?? 0,
      vpSteps: counts.valuePath,
      signals: counts.sources,
    },
  }), [
    project?.readiness_score,
    project?.counts?.features,
    project?.counts?.personas,
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
    <AssistantProvider
      projectId={projectId}
      initialProjectData={assistantProjectData}
      onProjectDataChanged={loadProjectData}
    >
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
