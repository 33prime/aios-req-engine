'use client'

import { FileText } from 'lucide-react'
import { BusinessContextSection } from './sections/BusinessContextSection'
import { ActorsSection } from './sections/ActorsSection'
import { WorkflowsSection } from './sections/WorkflowsSection'
import { RequirementsSection } from './sections/RequirementsSection'
import { ConstraintsSection } from './sections/ConstraintsSection'
import { CompetitorsSection } from './sections/CompetitorsSection'
import { DataEntitiesSection } from './sections/DataEntitiesSection'
import { IntelligenceRequirementsSection } from './sections/IntelligenceRequirementsSection'
import { ProblemSolutionSection } from './sections/ProblemSolutionSection'
import { IntelligenceSection } from './sections/IntelligenceSection'
import { SolutionFlowSection } from './sections/SolutionFlowSection'
import { SolutionFlowModal } from './components/SolutionFlowModal'
import { WorkflowCreateModal } from './components/WorkflowCreateModal'
import { WorkflowStepEditor } from './components/WorkflowStepEditor'
import { DataEntityCreateModal } from './components/DataEntityCreateModal'
// Drawer components removed — entity detail is now inline on cards,
// deep-dive available via chat assistant.
import { OpenQuestionsPanel } from './components/OpenQuestionsPanel'
import { ImpactPreviewModal } from './components/ImpactPreviewModal'
import { ConfirmationClusters } from './components/ConfirmationClusters'
import { inferConstraints } from '@/lib/api'
import { getProjectLabels } from '@/lib/project-type-labels'
import type { NextAction } from '@/lib/api'
import type { BRDWorkspaceData, SectionScore } from '@/types/workspace'

import { useBRDDataLoading } from './hooks/useBRDDataLoading'
import { useBRDDrawerManager } from './hooks/useBRDDrawerManager'
import { useBRDEntityActions } from './hooks/useBRDEntityActions'
import { useBRDWorkflowCRUD } from './hooks/useBRDWorkflowCRUD'

interface BRDCanvasProps {
  projectId: string
  initialData?: BRDWorkspaceData | null
  initialNextActions?: NextAction[] | null
  onRefresh?: () => void
  onSendToChat?: (action: NextAction) => void
  pendingAction?: NextAction | null
  onPendingActionConsumed?: () => void
  onActiveSectionChange?: (sectionId: string) => void
  onNavigateToCollaborate?: () => void
  onActionClick?: (action: import('@/lib/api/workspace').SynthesizedAction) => void
}

export function BRDCanvas({ projectId, initialData, initialNextActions, onRefresh, onSendToChat, pendingAction, onPendingActionConsumed, onActiveSectionChange, onNavigateToCollaborate, onActionClick }: BRDCanvasProps) {
  // Hook 1: Data loading, health, questions, clusters
  const dataState = useBRDDataLoading(projectId, initialData, initialNextActions, onActiveSectionChange)
  const { data, setData, isLoading, error, loadData, scrollContainerRef } = dataState

  // Hook 2: Drawer management
  const drawers = useBRDDrawerManager(data)

  // Hook 3: Entity actions (confirm, priority, vision, etc.)
  const actions = useBRDEntityActions({
    projectId,
    data,
    setData,
    loadData,
    closeAllDrawers: drawers.closeAllDrawers,
    handleOpenConfidence: drawers.handleOpenConfidence,
    onSendToChat,
    pendingAction,
    onPendingActionConsumed,
    onNavigateToCollaborate,
  })

  // Hook 4: Workflow/step/data-entity CRUD
  const workflows = useBRDWorkflowCRUD({
    projectId,
    data,
    loadData,
    showImpactPreview: drawers.showImpactPreview,
  })

  // Loading state
  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary mx-auto mb-3" />
        <p className="text-[13px] text-text-placeholder">Loading BRD...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <p className="text-red-500 mb-3">{error || 'No data available'}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 text-sm text-white bg-brand-primary rounded-md hover:bg-[#25785A] transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  // Computed values
  const isStepEdit = !!workflows.stepEditorState.stepId

  const sectionScoreMap: Record<string, SectionScore> = {}
  if (data.completeness?.sections) {
    for (const s of data.completeness.sections) {
      sectionScoreMap[s.section] = s
    }
  }

  const labels = getProjectLabels(data.project_type)

  return (
    <div className="flex h-full">
      {/* BRD Content — full width */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto py-8 px-6">
          {/* Document header */}
          <div className="mb-8">
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-text-placeholder" />
              <h1 className="text-[28px] font-bold text-[#37352f]">
                {data.project_type === 'internal' ? 'Business Requirements Document' : 'Product Requirements Document'}
              </h1>
            </div>
            <p className="mt-2 text-[13px] text-[#666666] leading-relaxed">
              The living foundation of your project — every requirement, decision, and insight traced back to its source.
            </p>
          </div>

          {/* Intelligence header moved to Outcomes tab */}
          {/* Solution Flow removed — has its own tab */}

          {/* 1. Confirmation Clusters */}
          {dataState.clusters.length > 0 && (
            <div className="mb-6">
              <ConfirmationClusters
                projectId={projectId}
                clusters={dataState.clusters}
                onConfirmed={() => { dataState.loadClusters(); loadData() }}
              />
            </div>
          )}

          {/* 4. Open Questions (collapsed by default) */}
          <div id="brd-section-questions">
            <OpenQuestionsPanel
              projectId={projectId}
              questions={dataState.openQuestions}
              loading={dataState.questionsLoading}
              onMutate={dataState.loadOpenQuestions}
            />
          </div>

          {/* Problem / Solution — only for new_product (replaces Background/Vision) */}
          {data.project_type !== 'internal' && (
            <ProblemSolutionSection
              macroOutcome={data.macro_outcome}
              outcomeThesis={data.outcome_thesis}
              projectId={projectId}
              projectType={data.project_type}
              onUpdateMacroOutcome={actions.handleUpdateMacroOutcome}
              onUpdateOutcomeThesis={actions.handleUpdateOutcomeThesis}
            />
          )}

          {/* BRD Sections */}
          <div className="space-y-10">

        {/* 6. Business Context (vision, drivers, metrics) */}
        <div id="brd-section-business-context">
        <BusinessContextSection
          data={data.business_context}
          projectId={projectId}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
          onConfirmAll={actions.handleConfirmAll}
          onUpdateVision={actions.handleUpdateVision}
          onUpdateBackground={actions.handleUpdateBackground}
          onStatusClick={drawers.handleOpenConfidence}
          sectionScore={sectionScoreMap['vision'] || null}
          stakeholders={data.stakeholders}
          goalsLabel={labels.goals.toUpperCase()}
          painPointsLabel={labels.painPoints.toUpperCase()}
          hideNarratives={data.project_type !== 'internal'}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        {/* 7. Actors & Personas */}
        <div id="brd-section-personas">
        <ActorsSection
          actors={data.actors}
          workflows={data.workflows}
          sectionTitle={labels.actors}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
          onConfirmAll={actions.handleConfirmAll}
          onRefreshEntity={actions.handleRefreshEntity}
          onStatusClick={drawers.handleOpenConfidence}
          onCanvasRoleUpdate={actions.handleCanvasRoleUpdate}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        {/* 8. Key Workflows */}
        <div id="brd-section-workflows">
        <WorkflowsSection
          workflows={data.workflows}
          workflowPairs={data.workflow_pairs}
          roiSummary={data.roi_summary}
          sectionTitle={labels.workflows}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
          onConfirmAll={actions.handleConfirmAll}
          onCreateWorkflow={() => workflows.setShowCreateWorkflow(true)}
          onEditWorkflow={workflows.handleEditWorkflow}
          onDeleteWorkflow={workflows.handleDeleteWorkflow}
          onPairWorkflow={workflows.handlePairWorkflow}
          onCreateStep={(workflowId, stateType) =>
            workflows.setStepEditorState({ open: true, workflowId, stateType })
          }
          onEditStep={workflows.handleEditStep}
          onDeleteStep={workflows.handleDeleteStep}
          onRefreshEntity={actions.handleRefreshEntity}
          onStatusClick={drawers.handleOpenConfidence}
          sectionScore={sectionScoreMap['workflows'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        {/* 8b. Competitive Landscape */}
        {data.competitors && data.competitors.length > 0 && (
          <>
            <div id="brd-section-competitors">
              <CompetitorsSection
                competitors={data.competitors}
                onConfirm={actions.handleConfirm}
                onNeedsReview={actions.handleNeedsReview}
                onConfirmAll={actions.handleConfirmAll}
                onOpenDetail={() => {}}
                onOpenSynthesis={() => {}}
                onStatusClick={drawers.handleOpenConfidence}
                sectionScore={sectionScoreMap['competitors'] || null}
              />
            </div>
            <div className="border-t border-[#e9e9e7]" />
          </>
        )}

        {/* 9. Requirements (max 20, MoSCoW) */}
        <div id="brd-section-features">
        <RequirementsSection
          requirements={data.requirements}
          sectionTitle={labels.requirements}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
          onConfirmAll={actions.handleConfirmAll}
          onMovePriority={actions.handleMovePriority}
          onRefreshEntity={actions.handleRefreshEntity}
          onStatusClick={drawers.handleOpenConfidence}
          sectionScore={sectionScoreMap['features'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        {/* 9b. Intelligence Requirements */}
        <IntelligenceRequirementsSection projectId={projectId} />

        <div className="border-t border-[#e9e9e7]" />

        {/* 10. Constraints */}
        <div id="brd-section-constraints">
        <ConstraintsSection
          constraints={data.constraints}
          sectionTitle={labels.constraints}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
          onConfirmAll={actions.handleConfirmAll}
          onStatusClick={drawers.handleOpenConfidence}
          onInferConstraints={async () => {
            try {
              await inferConstraints(projectId)
              loadData()
            } catch (err) {
              console.error('Failed to infer constraints:', err)
            }
          }}
          sectionScore={sectionScoreMap['constraints'] || null}
        />
        </div>

        {/* 11. Data Entities — What the System Must Know */}
        {data.data_entities && data.data_entities.length > 0 && (
          <>
            <div className="border-t border-[#e9e9e7]" />
            <div id="brd-section-data-entities">
              <DataEntitiesSection
                projectId={projectId}
                dataEntities={data.data_entities}
                onConfirm={actions.handleConfirm}
                onNeedsReview={actions.handleNeedsReview}
                onConfirmAll={actions.handleConfirmAll}
                onCreateEntity={() => workflows.setShowCreateDataEntity(true)}
                onDeleteEntity={workflows.handleDeleteDataEntityWithPreview}
                onRefreshEntity={actions.handleRefreshEntity}
                onStatusClick={drawers.handleOpenConfidence}
                sectionScore={sectionScoreMap['data_entities'] || null}
              />
            </div>
          </>
        )}

      </div>
        </div>{/* end max-w-4xl */}
      </div>{/* end flex-1 overflow-y-auto (BRD content) */}

      {/* Data Entity Create Modal */}
      <DataEntityCreateModal
        open={workflows.showCreateDataEntity}
        onClose={() => workflows.setShowCreateDataEntity(false)}
        onSave={workflows.handleCreateDataEntity}
      />

      {/* Workflow Create/Edit Modal */}
      <WorkflowCreateModal
        open={workflows.showCreateWorkflow || !!workflows.editWorkflowData}
        onClose={() => {
          workflows.setShowCreateWorkflow(false)
          workflows.setEditWorkflowData(null)
        }}
        onSave={workflows.editWorkflowData ? workflows.handleUpdateWorkflow : workflows.handleCreateWorkflow}
        initialData={workflows.editWorkflowData || undefined}
      />

      {/* Workflow Step Create/Edit Editor */}
      <WorkflowStepEditor
        open={workflows.stepEditorState.open}
        stateType={workflows.stepEditorState.stateType}
        onClose={() => workflows.setStepEditorState({ open: false, workflowId: '', stateType: 'future' })}
        onSave={isStepEdit ? workflows.handleUpdateStep : workflows.handleCreateStep}
        initialData={workflows.stepEditorState.initialData}
      />

      {/* Impact Preview Modal */}
      <ImpactPreviewModal
        open={drawers.impactPreview.open}
        projectId={projectId}
        entityType={drawers.impactPreview.entityType}
        entityId={drawers.impactPreview.entityId}
        entityName={drawers.impactPreview.entityName}
        onClose={() => drawers.setImpactPreview((prev) => ({ ...prev, open: false }))}
        onConfirmDelete={drawers.impactPreview.onDelete}
      />

      {/* Solution Flow Modal */}
      <SolutionFlowModal
        projectId={projectId}
        isOpen={workflows.showSolutionFlowModal}
        onClose={() => {
          workflows.setShowSolutionFlowModal(false)
          loadData()
        }}
        onConfirm={actions.handleConfirm}
        onNeedsReview={actions.handleNeedsReview}
        entityLookup={workflows.entityLookup}
      />

      {/* All entity drawers removed — detail available via chat assistant */}
    </div>
  )
}
