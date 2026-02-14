'use client'

import { useState, useEffect, useCallback } from 'react'
import { Cpu, RefreshCw } from 'lucide-react'
import { CanvasActorsRow } from './CanvasActorsRow'
import { ValuePathSection } from './ValuePathSection'
import { MvpFeaturesSection } from './MvpFeaturesSection'
import { AssumptionsSection } from './AssumptionsSection'
import { ProjectContextSection } from './ProjectContextSection'
import { ValuePathStepDrawer } from './ValuePathStepDrawer'
import { UnlockDetailDrawer } from './UnlockDetailDrawer'
import { FeatureDrawer } from '../brd/components/FeatureDrawer'
import { PersonaDrawer } from '../brd/components/PersonaDrawer'
import {
  getCanvasViewData,
  triggerValuePathSynthesis,
  getProjectContext,
  generateProjectContext,
  batchConfirmEntities,
} from '@/lib/api'
import type { CanvasViewData, ProjectContext, ValuePathUnlock, FeatureBRDSummary, PersonaBRDSummary } from '@/types/workspace'

interface CanvasViewProps {
  projectId: string
  onRefresh?: () => void
}

export function CanvasView({ projectId, onRefresh }: CanvasViewProps) {
  const [data, setData] = useState<CanvasViewData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSynthesizing, setIsSynthesizing] = useState(false)

  // Project Context state
  const [projectContext, setProjectContext] = useState<ProjectContext | null>(null)
  const [isGeneratingContext, setIsGeneratingContext] = useState(false)

  // Value Path Step Drawer state (left-click on a step)
  const [selectedStep, setSelectedStep] = useState<{
    stepIndex: number
    stepTitle: string
  } | null>(null)

  // Unlock Detail Drawer state (click on an unlock)
  const [selectedUnlock, setSelectedUnlock] = useState<{
    stepIndex: number
    stepTitle: string
    unlock: ValuePathUnlock
  } | null>(null)

  // Feature Drawer state (click on an MVP feature)
  const [selectedFeature, setSelectedFeature] = useState<FeatureBRDSummary | null>(null)

  // Persona Drawer state (click on an actor card)
  const [selectedPersona, setSelectedPersona] = useState<PersonaBRDSummary | null>(null)

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const result = await getCanvasViewData(projectId)
      setData(result)
    } catch (err) {
      console.error('Failed to load canvas view data:', err)
      setError('Failed to load canvas data')
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  // Load project context separately (non-blocking)
  const [contextLoaded, setContextLoaded] = useState(false)
  const loadContext = useCallback(async () => {
    try {
      const ctx = await getProjectContext(projectId)
      setProjectContext(ctx)
    } catch (err) {
      console.error('Failed to load project context:', err)
    } finally {
      setContextLoaded(true)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
    loadContext()
  }, [loadData, loadContext])

  // Auto-generate missing data after both loads complete
  const [autoGenTriggered, setAutoGenTriggered] = useState(false)

  useEffect(() => {
    if (isLoading || !contextLoaded || autoGenTriggered) return
    if (!data) return

    let triggered = false

    // Auto-generate project context if missing
    if (!projectContext && !isGeneratingContext) {
      setIsGeneratingContext(true)
      triggered = true
      generateProjectContext(projectId)
        .then((ctx) => setProjectContext(ctx))
        .catch((err) => console.error('Auto-generate context failed:', err))
        .finally(() => setIsGeneratingContext(false))
    }

    // Auto-synthesize value path if we have actors but no path
    if (data.actors.length > 0 && data.value_path.length === 0 && !isSynthesizing) {
      triggered = true
      setIsSynthesizing(true)
      triggerValuePathSynthesis(projectId)
        .then(() => loadData())
        .catch((err) => console.error('Auto-synthesize value path failed:', err))
        .finally(() => setIsSynthesizing(false))
    }

    if (triggered) setAutoGenTriggered(true)
  }, [isLoading, contextLoaded, data, projectContext, autoGenTriggered, projectId, isGeneratingContext, isSynthesizing, loadData])

  const handleSynthesize = useCallback(async () => {
    try {
      setIsSynthesizing(true)
      await triggerValuePathSynthesis(projectId)
      await loadData()
    } catch (err) {
      console.error('Failed to synthesize value path:', err)
    } finally {
      setIsSynthesizing(false)
    }
  }, [projectId, loadData])

  const handleGenerateContext = useCallback(async () => {
    try {
      setIsGeneratingContext(true)
      const ctx = await generateProjectContext(projectId)
      setProjectContext(ctx)
    } catch (err) {
      console.error('Failed to generate project context:', err)
    } finally {
      setIsGeneratingContext(false)
    }
  }, [projectId])

  const handleStepClick = useCallback(
    (stepIndex: number, stepTitle: string) => {
      setSelectedUnlock(null) // close unlock drawer if open
      setSelectedStep({ stepIndex, stepTitle })
    },
    []
  )

  const handleUnlockClick = useCallback(
    (stepIndex: number, stepTitle: string, unlock: ValuePathUnlock) => {
      setSelectedStep(null) // close step drawer if open
      setSelectedUnlock({ stepIndex, stepTitle, unlock })
    },
    []
  )

  const handleActorClick = useCallback((actor: PersonaBRDSummary) => {
    setSelectedPersona(actor)
  }, [])

  const handleFeatureClick = useCallback((feature: FeatureBRDSummary) => {
    setSelectedFeature(feature)
  }, [])

  const handleFeatureConfirm = useCallback(
    async (_entityType: string, entityId: string) => {
      await batchConfirmEntities(projectId, 'feature', [entityId], 'confirmed_consultant')
      await loadData()
    },
    [projectId, loadData]
  )

  const handleFeatureNeedsReview = useCallback(
    async (_entityType: string, entityId: string) => {
      await batchConfirmEntities(projectId, 'feature', [entityId], 'needs_client')
      await loadData()
    },
    [projectId, loadData]
  )

  const handleConfirm = useCallback(
    async (entityType: string, entityId: string) => {
      await batchConfirmEntities(projectId, entityType, [entityId], 'confirmed_consultant')
      await loadData()
    },
    [projectId, loadData]
  )

  const handleNeedsReview = useCallback(
    async (entityType: string, entityId: string) => {
      await batchConfirmEntities(projectId, entityType, [entityId], 'needs_client')
      await loadData()
    },
    [projectId, loadData]
  )

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3FAF7A] mx-auto mb-3" />
        <p className="text-[13px] text-[#999999]">Loading Canvas View...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center">
        <p className="text-red-500 mb-3">{error || 'No data available'}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 text-sm text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  const hasActors = data.actors.length > 0
  const hasValuePath = data.value_path.length > 0

  return (
    <div className="max-w-5xl mx-auto py-8 px-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Cpu className="w-6 h-6 text-[#3FAF7A]" />
          <div>
            <h1 className="text-[24px] font-bold text-[#333333]">Product Intelligence Canvas</h1>
            <p className="text-[13px] text-[#999999] mt-0.5">
              AI-synthesized product blueprint — the translation from discovery to build
            </p>
          </div>
        </div>
        <button
          onClick={() => {
            loadData()
            loadContext()
            onRefresh?.()
          }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Project Context — always shown */}
      <div className="mb-8">
        <ProjectContextSection
          projectId={projectId}
          context={projectContext}
          onGenerate={handleGenerateContext}
          isGenerating={isGeneratingContext}
        />
      </div>

      {/* Empty state when no actors selected */}
      {!hasActors && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-12 text-center">
          <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-[#F4F4F4] flex items-center justify-center">
            <Cpu className="w-7 h-7 text-[#999999]" />
          </div>
          <h3 className="text-[16px] font-semibold text-[#333333] mb-2">No canvas actors selected</h3>
          <p className="text-[13px] text-[#666666] max-w-md mx-auto">
            Switch to BRD View and click the star icon on personas to select them as canvas actors
            (max 2 primary + 1 secondary). Then return here to synthesize the value path.
          </p>
        </div>
      )}

      {/* Canvas sections */}
      {hasActors && (
        <div className="space-y-8">
          {/* Actors Row — persona cards with inline workflow journeys */}
          <CanvasActorsRow
            actors={data.actors}
            workflowPairs={data.workflow_pairs}
            onSynthesize={handleSynthesize}
            isSynthesizing={isSynthesizing}
            synthesisStale={data.synthesis_stale}
            hasValuePath={hasValuePath}
            onActorClick={handleActorClick}
          />

          {/* Value Path — side-by-side: Steps ↔ What This Unlocks */}
          <ValuePathSection
            steps={data.value_path}
            rationale={data.synthesis_rationale}
            isStale={data.synthesis_stale}
            onRegenerate={handleSynthesize}
            isSynthesizing={isSynthesizing}
            onStepClick={handleStepClick}
            onUnlockClick={handleUnlockClick}
            selectedStepIndex={selectedStep?.stepIndex ?? null}
          />

          {/* MVP Features */}
          <MvpFeaturesSection features={data.mvp_features} onFeatureClick={handleFeatureClick} />

          {/* Assumptions & Open Questions — from project context */}
          {projectContext && (
            <AssumptionsSection
              assumptions={projectContext.assumptions}
              openQuestions={projectContext.open_questions}
            />
          )}
        </div>
      )}

      {/* Value Path Step Drawer — opens on step click */}
      {selectedStep && (
        <ValuePathStepDrawer
          projectId={projectId}
          stepIndex={selectedStep.stepIndex}
          stepTitle={selectedStep.stepTitle}
          onClose={() => setSelectedStep(null)}
        />
      )}

      {/* Unlock Detail Drawer — opens on unlock click */}
      {selectedUnlock && (
        <UnlockDetailDrawer
          stepIndex={selectedUnlock.stepIndex}
          stepTitle={selectedUnlock.stepTitle}
          unlock={selectedUnlock.unlock}
          onClose={() => setSelectedUnlock(null)}
        />
      )}

      {/* Feature Drawer — opens on MVP feature click */}
      {selectedFeature && (
        <FeatureDrawer
          feature={selectedFeature}
          projectId={projectId}
          onClose={() => setSelectedFeature(null)}
          onConfirm={handleFeatureConfirm}
          onNeedsReview={handleFeatureNeedsReview}
        />
      )}

      {/* Persona Drawer — opens on actor card click */}
      {selectedPersona && (
        <PersonaDrawer
          persona={selectedPersona}
          projectId={projectId}
          onClose={() => setSelectedPersona(null)}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
        />
      )}
    </div>
  )
}
