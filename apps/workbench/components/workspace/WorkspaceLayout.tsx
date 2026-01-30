/**
 * WorkspaceLayout - Three-zone layout for project workspace
 *
 * Layout:
 * - Left: AppSidebar (global navigation)
 * - Center: Main workspace (phase-dependent content)
 * - Right: CollaborationPanel (chat, portal, activity)
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { AppSidebar } from './AppSidebar'
import { PhaseSwitcher, WorkspacePhase } from './PhaseSwitcher'
import { CollaborationPanel, type PanelState } from './CollaborationPanel'
import { RequirementsCanvas } from './canvas/RequirementsCanvas'
import { BuildPhaseView } from './BuildPhaseView'
import { OverviewPanel } from './OverviewPanel'
import { BottomDock } from './BottomDock'
import { useChat } from '@/lib/useChat'
import { AssistantProvider } from '@/lib/assistant'
import {
  getWorkspaceData,
  updatePitchLine,
  updatePrototypeUrl,
  mapFeatureToStep,
  getReadinessScore,
  getStatusNarrative,
} from '@/lib/api'
import type { CanvasData } from '@/types/workspace'
import type { ReadinessScore } from '@/lib/api'
import type { StatusNarrative } from '@/types/api'

interface WorkspaceLayoutProps {
  projectId: string
  children?: React.ReactNode
}

export function WorkspaceLayout({ projectId, children }: WorkspaceLayoutProps) {
  const [phase, setPhase] = useState<WorkspacePhase>('overview')
  const [canvasData, setCanvasData] = useState<CanvasData | null>(null)
  const [readinessData, setReadinessData] = useState<ReadinessScore | null>(null)
  const [narrativeData, setNarrativeData] = useState<StatusNarrative | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [collaborationState, setCollaborationState] = useState<PanelState>('normal')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(true)
  const [activeBottomPanel, setActiveBottomPanel] = useState<'context' | 'evidence' | 'history' | null>(null)

  // Chat integration
  const { messages, isLoading: isChatLoading, sendMessage, sendSignal, addLocalMessage } = useChat({
    projectId,
    onError: (error) => {
      console.error('Chat error:', error)
    },
  })

  // Load workspace data
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const [data, readiness, narrative] = await Promise.all([
        getWorkspaceData(projectId),
        getReadinessScore(projectId).catch(() => null),
        getStatusNarrative(projectId).catch(() => null),
      ])

      setCanvasData(data)
      setReadinessData(readiness)
      setNarrativeData(narrative)

      // Auto-detect phase based on project state
      if (data.prototype_url) {
        setPhase('build')
      }
    } catch (err) {
      console.error('Failed to load workspace data:', err)
      setError('Failed to load workspace data')
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Handlers
  const handleUpdatePitchLine = async (pitchLine: string) => {
    await updatePitchLine(projectId, pitchLine)
    setCanvasData((prev) =>
      prev ? { ...prev, pitch_line: pitchLine } : prev
    )
  }

  const handleUpdatePrototypeUrl = async (url: string) => {
    await updatePrototypeUrl(projectId, url)
    setCanvasData((prev) =>
      prev ? { ...prev, prototype_url: url, prototype_updated_at: new Date().toISOString() } : prev
    )
  }

  const handleMapFeatureToStep = async (featureId: string, stepId: string | null) => {
    await mapFeatureToStep(projectId, featureId, stepId)
    // Reload data to get updated state
    await loadData()
  }

  // Calculate sidebar widths
  const sidebarWidth = sidebarCollapsed ? 64 : 224
  const collaborationWidth =
    collaborationState === 'collapsed' ? 48 :
    collaborationState === 'wide' ? 400 : 320

  // Build assistant project data
  const assistantProjectData = canvasData
    ? {
        readinessScore: canvasData.readiness_score,
        blockers: [],
        warnings: [],
        pendingConfirmations: canvasData.pending_count,
        stats: {
          features: canvasData.features.length,
          personas: canvasData.personas.length,
          vpSteps: canvasData.vp_steps.length,
          signals: 0,
        },
      }
    : undefined

  if (isLoading) {
    return (
      <div className="min-h-screen bg-ui-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-teal mx-auto mb-4" />
          <p className="text-support text-ui-supportText">Loading workspace...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-ui-background flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error}</p>
          <button
            onClick={loadData}
            className="px-4 py-2 bg-brand-teal text-white rounded-lg hover:bg-brand-tealDark transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <AssistantProvider
      projectId={projectId}
      initialProjectData={assistantProjectData}
      onProjectDataChanged={loadData}
    >
      <div className="min-h-screen bg-[#F8F9FB]">
        {/* Left Sidebar */}
        <AppSidebar
          isCollapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        {/* Main Content Area */}
        <div
          className="transition-all duration-300"
          style={{
            marginLeft: sidebarWidth,
            marginRight: collaborationWidth,
          }}
        >
          {/* Header with Phase Switcher */}
          <header className="sticky top-0 z-20 bg-white border-b border-ui-cardBorder">
            <div className="flex items-center justify-between px-6 py-4">
              <div className="flex items-center gap-4">
                <Link
                  href={`/projects/${projectId}`}
                  className="flex items-center gap-1.5 text-sm text-ui-supportText hover:text-ui-headingDark transition-colors"
                  title="Back to classic view"
                >
                  <ArrowLeft className="w-4 h-4" />
                  <span className="hidden sm:inline">Classic</span>
                </Link>
                <div className="h-5 w-px bg-ui-cardBorder" />
                <div>
                  <h1 className="text-h2 text-ui-headingDark">
                    {canvasData?.project_name}
                  </h1>
                  {canvasData?.pitch_line && (
                    <p className="text-support text-ui-supportText mt-0.5 truncate max-w-xl">
                      {canvasData.pitch_line}
                    </p>
                  )}
                </div>
              </div>

              <PhaseSwitcher
                currentPhase={phase}
                onPhaseChange={setPhase}
              />
            </div>
          </header>

          {/* Phase Content */}
          <main className="p-6">
            {phase === 'overview' && canvasData && (
              <OverviewPanel
                projectId={projectId}
                canvasData={canvasData}
                readinessData={readinessData}
                narrativeData={narrativeData}
                onNavigateToPhase={(p) => setPhase(p)}
              />
            )}

            {phase === 'discovery' && canvasData && (
              <RequirementsCanvas
                data={canvasData}
                projectId={projectId}
                onUpdatePitchLine={handleUpdatePitchLine}
                onMapFeatureToStep={handleMapFeatureToStep}
                onRefresh={loadData}
              />
            )}

            {phase === 'build' && canvasData && (
              <div className="h-[calc(100vh-140px)] bg-white rounded-card border border-ui-cardBorder overflow-hidden">
                <BuildPhaseView
                  projectId={projectId}
                  prototypeUrl={canvasData.prototype_url}
                  prototypeUpdatedAt={canvasData.prototype_updated_at}
                  readinessScore={canvasData.readiness_score}
                  onUpdatePrototypeUrl={handleUpdatePrototypeUrl}
                />
              </div>
            )}

            {phase === 'live' && (
              <div className="flex items-center justify-center h-[calc(100vh-200px)]">
                <div className="text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-ui-background flex items-center justify-center">
                    <span className="text-2xl">🚀</span>
                  </div>
                  <h3 className="text-section text-ui-headingDark mb-2">
                    Live Product View
                  </h3>
                  <p className="text-support text-ui-supportText">
                    Coming soon - track your product post-launch
                  </p>
                </div>
              </div>
            )}

            {/* Optional children for extension */}
            {children}
          </main>

          {/* Bottom Dock */}
          <BottomDock
            projectId={projectId}
            activePanel={activeBottomPanel}
            onPanelChange={setActiveBottomPanel}
          />
        </div>

        {/* Right Collaboration Panel */}
        <CollaborationPanel
          projectId={projectId}
          projectName={canvasData?.project_name || 'Project'}
          pendingCount={canvasData?.pending_count}
          messages={messages}
          isChatLoading={isChatLoading}
          onSendMessage={sendMessage}
          onSendSignal={sendSignal}
          onAddLocalMessage={addLocalMessage}
          panelState={collaborationState}
          onPanelStateChange={setCollaborationState}
        />
      </div>
    </AssistantProvider>
  )
}

export default WorkspaceLayout
