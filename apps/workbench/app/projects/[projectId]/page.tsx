/**
 * Main Workspace Page
 *
 * Unified 4-tab workspace for consultant workflow:
 * 1. Product Requirements - PRD sections with status tracking
 * 2. Value Path - VP steps with enrichment details
 * 3. Insights - Red team analysis with decision workflow
 * 4. Next Steps - Batched client confirmations
 *
 * Features:
 * - Tab navigation with counts
 * - Header with agent actions and research toggle
 * - Real-time data loading and updates
 * - Job polling for async operations
 */

'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { TabNavigation, MobileTabNavigation, type TabType } from './components/TabNavigation'
import { WorkspaceHeader, CompactHeader } from './components/WorkspaceHeader'
import { ProductRequirementsTab } from './components/tabs/ProductRequirementsTab'
import { ValuePathTab } from './components/tabs/ValuePathTab'
import { InsightsTab } from './components/tabs/InsightsTab'
import { NextStepsTab } from './components/tabs/NextStepsTab'
import { AddSignalModal } from './components/AddSignalModal'
import { AddResearchModal } from './components/AddResearchModal'
import BaselineStatus from './components/BaselineStatus'
import PatchFeed from './components/PatchFeed'
import { getBaselineStatus, getBaselineCompleteness, finalizeBaseline, listConfirmations, getFeatures, getPrdSections, getVpSteps, getInsights } from '@/lib/api'
import type { BaselineStatus as BaselineStatusType } from '@/types/api'

export default function WorkspacePage() {
  const params = useParams()
  const projectId = params.projectId as string

  // Tab state
  const [activeTab, setActiveTab] = useState<TabType>('requirements')

  // Data state
  const [baseline, setBaseline] = useState<BaselineStatus | null>(null)
  const [baselineCompleteness, setBaselineCompleteness] = useState<any>(null)
  const [prdMode, setPrdMode] = useState<'initial' | 'maintenance'>('initial')
  const [counts, setCounts] = useState({
    requirements: 0,
    valuePath: 0,
    insights: 0,
    nextSteps: 0
  })
  const [loading, setLoading] = useState(true)
  const [loadingCompleteness, setLoadingCompleteness] = useState(true)

  // Modal state
  const [showAddSignal, setShowAddSignal] = useState(false)
  const [showAddResearch, setShowAddResearch] = useState(false)

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
        confirmationsData,
      ] = await Promise.all([
        getBaselineStatus(projectId),
        getPrdSections(projectId),
        getVpSteps(projectId),
        getInsights(projectId),
        listConfirmations(projectId, 'open'),
      ])

      setBaseline(baselineData)

      // Update counts
      setCounts({
        requirements: prdData.length,
        valuePath: vpData.length,
        insights: insightsData.length,
        nextSteps: confirmationsData.confirmations?.length || 0
      })

      console.log('✅ Workspace data loaded:', {
        prd: prdData.length,
        vp: vpData.length,
        insights: insightsData.length,
        confirmations: confirmationsData.confirmations?.length || 0
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

  // Handle agent runs
  const handleRunAgent = async (agentType: 'build' | 'reconcile' | 'redteam' | 'enrich-prd' | 'enrich-vp') => {
    try {
      console.log('🚀 Running agent:', agentType)

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
            alert(`${agentType} completed successfully!`)
            loadProjectData() // Refresh data
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
      case 'requirements':
        return <ProductRequirementsTab projectId={projectId} />
      case 'value-path':
        return <ValuePathTab projectId={projectId} />
      case 'insights':
        return <InsightsTab projectId={projectId} />
      case 'next-steps':
        return <NextStepsTab projectId={projectId} />
      default:
        return null
    }
  }

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
            onBaselineToggle={handleBaselineToggle}
            onRefresh={loadProjectData}
            onRunAgent={handleRunAgent}
            onAddSignal={() => setShowAddSignal(true)}
            onAddResearch={() => setShowAddResearch(true)}
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
        />
      </div>

      {/* Mobile Tab Navigation */}
      <div className="lg:hidden">
        <MobileTabNavigation
          activeTab={activeTab}
          onTabChange={setActiveTab}
        />
      </div>

      {/* Tab Content with Sidebar */}
      <main className="max-w-[1600px] mx-auto px-4 lg:px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Content (2/3 width) */}
          <div className="lg:col-span-2">
            {renderTabContent()}
          </div>

          {/* Right Sidebar (1/3 width) - Baseline Status & Patch Feed */}
          <div className="lg:col-span-1 space-y-6">
            <div className="sticky top-6 space-y-6">
              <BaselineStatus
                projectId={projectId}
                completeness={baselineCompleteness}
                prdMode={prdMode}
                onFinalize={handleFinalizeBaseline}
                onRefresh={loadBaselineCompleteness}
                loading={loadingCompleteness}
              />

              {/* Patch Feed - only show in maintenance mode */}
              {prdMode === 'maintenance' && (
                <PatchFeed
                  projectId={projectId}
                  limit={10}
                />
              )}
            </div>
          </div>
        </div>
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
    </div>
  )
}
