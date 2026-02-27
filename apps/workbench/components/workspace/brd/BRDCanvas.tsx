'use client'

import { FileText, RefreshCw } from 'lucide-react'
import { BusinessContextSection } from './sections/BusinessContextSection'
import { ActorsSection } from './sections/ActorsSection'
import { WorkflowsSection } from './sections/WorkflowsSection'
import { RequirementsSection } from './sections/RequirementsSection'
import { ConstraintsSection } from './sections/ConstraintsSection'
import { DataEntitiesSection } from './sections/DataEntitiesSection'
import { StakeholdersSection } from './sections/StakeholdersSection'
import { IntelligenceSection } from './sections/IntelligenceSection'
import { SolutionFlowSection } from './sections/SolutionFlowSection'
import { SolutionFlowModal } from './components/SolutionFlowModal'
import { WorkflowCreateModal } from './components/WorkflowCreateModal'
import { WorkflowStepEditor } from './components/WorkflowStepEditor'
import { DataEntityCreateModal } from './components/DataEntityCreateModal'
import { StakeholderDetailDrawer } from './components/StakeholderDetailDrawer'
import { WorkflowStepDetailDrawer } from './components/WorkflowStepDetailDrawer'
import { WorkflowDetailDrawer } from './components/WorkflowDetailDrawer'
import { VisionDetailDrawer } from './components/VisionDetailDrawer'
import { ClientIntelligenceDrawer } from './components/ClientIntelligenceDrawer'
import { DataEntityDetailDrawer } from './components/DataEntityDetailDrawer'
import { PersonaDrawer } from './components/PersonaDrawer'
import { ConstraintDrawer } from './components/ConstraintDrawer'
import { FeatureDrawer } from './components/FeatureDrawer'
import { BusinessDriverDetailDrawer } from './components/BusinessDriverDetailDrawer'
import { ConfidenceDrawer } from './components/ConfidenceDrawer'
import { OpenQuestionsPanel } from './components/OpenQuestionsPanel'
import { ImpactPreviewModal } from './components/ImpactPreviewModal'
import { ConfirmationClusters } from './components/ConfirmationClusters'
import { inferConstraints } from '@/lib/api'
import type { NextAction } from '@/lib/api'
import { CompletenessRing } from './components/CompletenessRing'
import type { BRDWorkspaceData, SectionScore } from '@/types/workspace'

import { useBRDDataLoading } from './hooks/useBRDDataLoading'
import { useBRDDrawerManager } from './hooks/useBRDDrawerManager'
import { useBRDEntityActions } from './hooks/useBRDEntityActions'
import { useBRDWorkflowCRUD } from './hooks/useBRDWorkflowCRUD'
import { countEntities, countConfirmed, countStale } from './hooks/brd-canvas-utils'

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
}

export function BRDCanvas({ projectId, initialData, initialNextActions, onRefresh, onSendToChat, pendingAction, onPendingActionConsumed, onActiveSectionChange, onNavigateToCollaborate }: BRDCanvasProps) {
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
    setVisionDrawer: drawers.setVisionDrawer,
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
  const totalEntities = countEntities(data)
  const confirmedEntities = countConfirmed(data)
  const readinessPercent = totalEntities > 0 ? Math.round((confirmedEntities / totalEntities) * 100) : 0
  const staleCount = countStale(data)
  const isStepEdit = !!workflows.stepEditorState.stepId

  const sectionScoreMap: Record<string, SectionScore> = {}
  if (data.completeness?.sections) {
    for (const s of data.completeness.sections) {
      sectionScoreMap[s.section] = s
    }
  }

  return (
    <div className="flex h-full">
      {/* BRD Content — full width */}
      <div ref={scrollContainerRef} className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto py-8 px-6">
          {/* Document header */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <FileText className="w-6 h-6 text-text-placeholder" />
                <h1 className="text-[28px] font-bold text-[#37352f]">Business Requirements Document</h1>
                {data.completeness && (
                  <CompletenessRing score={data.completeness.overall_score} size="md" />
                )}
              </div>
              <button
                onClick={() => { loadData(); onRefresh?.() }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-gray-500 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Refresh
              </button>
            </div>

            {/* Readiness bar */}
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-primary rounded-full transition-all duration-300"
                  style={{ width: `${readinessPercent}%` }}
                />
              </div>
              <span className="text-[12px] font-medium text-[#666666] whitespace-nowrap">
                {confirmedEntities}/{totalEntities} confirmed ({readinessPercent}%)
              </span>
            </div>
            {data.pending_count > 0 && (
              <p className="mt-2 text-[12px] text-yellow-600">
                {data.pending_count} items pending review
              </p>
            )}
            {staleCount > 0 && (
              <p className="mt-1 text-[12px] text-orange-600">
                {staleCount} {staleCount === 1 ? 'item' : 'items'} may be outdated
              </p>
            )}
          </div>

          {/* Intelligence Dashboard */}
          <IntelligenceSection
            data={data}
            health={dataState.health}
            healthLoading={dataState.healthLoading}
            onRefreshAll={dataState.handleRefreshHealth}
            isRefreshing={dataState.isRefreshingHealth}
          />

          {/* Confirmation Clusters */}
          {dataState.clusters.length > 0 && (
            <div className="mb-6">
              <ConfirmationClusters
                projectId={projectId}
                clusters={dataState.clusters}
                onConfirmed={() => { dataState.loadClusters(); loadData() }}
              />
            </div>
          )}

          {/* Open Questions (collapsed by default) */}
          <div id="brd-section-questions">
            <OpenQuestionsPanel
              projectId={projectId}
              questions={dataState.openQuestions}
              loading={dataState.questionsLoading}
              onMutate={dataState.loadOpenQuestions}
            />
          </div>

          {/* BRD Sections */}
          <div className="space-y-10">
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
          onOpenVisionDetail={drawers.handleOpenVisionDetail}
          onOpenBackgroundDetail={drawers.handleOpenBackgroundDetail}
          stakeholders={data.stakeholders}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-personas">
        <ActorsSection
          actors={data.actors}
          workflows={data.workflows}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
          onConfirmAll={actions.handleConfirmAll}
          onRefreshEntity={actions.handleRefreshEntity}
          onStatusClick={drawers.handleOpenConfidence}
          onCanvasRoleUpdate={actions.handleCanvasRoleUpdate}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-workflows">
        <WorkflowsSection
          workflows={data.workflows}
          workflowPairs={data.workflow_pairs}
          roiSummary={data.roi_summary}
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
          onViewStepDetail={drawers.handleViewStepDetail}
          onViewWorkflowDetail={drawers.handleViewWorkflowDetail}
          sectionScore={sectionScoreMap['workflows'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-solution-flow">
        <SolutionFlowSection
          flow={data.solution_flow}
          onOpen={() => workflows.setShowSolutionFlowModal(true)}
          onGenerate={workflows.handleGenerateSolutionFlow}
          isGenerating={workflows.isGeneratingSolutionFlow}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-features">
        <RequirementsSection
          requirements={data.requirements}
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
          onOpenDetail={drawers.handleOpenDataEntityDetail}
          sectionScore={sectionScoreMap['data_entities'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-stakeholders">
        <StakeholdersSection
          stakeholders={data.stakeholders}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
          onConfirmAll={actions.handleConfirmAll}
          onOpenDetail={(stakeholder) => {
            drawers.setConfidenceDrawer((prev) => ({ ...prev, open: false }))
            drawers.setStakeholderDrawer({ open: true, stakeholder })
          }}
          onRefreshEntity={actions.handleRefreshEntity}
          onStatusClick={drawers.handleOpenConfidence}
          sectionScore={sectionScoreMap['stakeholders'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-constraints">
        <ConstraintsSection
          constraints={data.constraints}
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

      {/* Stakeholder Detail Drawer */}
      {drawers.stakeholderDrawer.open && drawers.stakeholderDrawer.stakeholder && (
        <StakeholderDetailDrawer
          stakeholderId={drawers.stakeholderDrawer.stakeholder.id}
          projectId={projectId}
          initialData={drawers.stakeholderDrawer.stakeholder}
          onClose={() => drawers.setStakeholderDrawer({ open: false, stakeholder: null })}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
        />
      )}

      {/* Workflow Step Detail Drawer */}
      {drawers.stepDetailDrawer.open && drawers.stepDetailDrawer.stepId && (
        <WorkflowStepDetailDrawer
          stepId={drawers.stepDetailDrawer.stepId}
          projectId={projectId}
          onClose={() => drawers.setStepDetailDrawer({ open: false, stepId: '' })}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
        />
      )}

      {/* Workflow Detail Drawer */}
      {drawers.workflowDetailDrawer.open && drawers.workflowDetailDrawer.workflowId && (
        <WorkflowDetailDrawer
          workflowId={drawers.workflowDetailDrawer.workflowId}
          projectId={projectId}
          stakeholders={data?.stakeholders}
          onClose={() => drawers.setWorkflowDetailDrawer({ open: false, workflowId: '' })}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
          onViewStepDetail={(stepId) => {
            drawers.setWorkflowDetailDrawer({ open: false, workflowId: '' })
            drawers.setStepDetailDrawer({ open: true, stepId })
          }}
        />
      )}

      {/* Vision Detail Drawer */}
      {drawers.visionDrawer && (
        <VisionDetailDrawer
          projectId={projectId}
          initialVision={data.business_context.vision}
          onClose={() => drawers.setVisionDrawer(false)}
          onVisionUpdated={(vision) => {
            setData((prev) => prev ? {
              ...prev,
              business_context: { ...prev.business_context, vision },
            } : prev)
          }}
        />
      )}

      {/* Client Intelligence Drawer */}
      {drawers.clientIntelDrawer && (
        <ClientIntelligenceDrawer
          projectId={projectId}
          onClose={() => drawers.setClientIntelDrawer(false)}
        />
      )}

      {/* Data Entity Detail Drawer */}
      {drawers.dataEntityDrawer.open && drawers.dataEntityDrawer.entityId && (
        <DataEntityDetailDrawer
          entityId={drawers.dataEntityDrawer.entityId}
          projectId={projectId}
          onClose={() => drawers.setDataEntityDrawer({ open: false, entityId: '' })}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
        />
      )}

      {/* Confidence Drawer (fallback) */}
      {drawers.confidenceDrawer.open && (
        <ConfidenceDrawer
          entityType={drawers.confidenceDrawer.entityType}
          entityId={drawers.confidenceDrawer.entityId}
          entityName={drawers.confidenceDrawer.entityName}
          projectId={projectId}
          initialStatus={drawers.confidenceDrawer.initialStatus}
          onClose={() => drawers.setConfidenceDrawer((prev) => ({ ...prev, open: false }))}
          onConfirm={(entityType, entityId) => actions.handleConfirm(entityType, entityId)}
          onNeedsReview={(entityType, entityId) => actions.handleNeedsReview(entityType, entityId)}
        />
      )}

      {/* Persona Drawer */}
      {drawers.personaDrawer.open && drawers.personaDrawer.persona && (
        <PersonaDrawer
          persona={drawers.personaDrawer.persona}
          projectId={projectId}
          stakeholders={data?.stakeholders}
          features={data ? [
            ...data.requirements.must_have,
            ...data.requirements.should_have,
            ...data.requirements.could_have,
            ...data.requirements.out_of_scope,
          ] : []}
          onClose={() => drawers.setPersonaDrawer({ open: false, persona: null })}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
        />
      )}

      {/* Constraint Drawer */}
      {drawers.constraintDrawer.open && drawers.constraintDrawer.constraint && (
        <ConstraintDrawer
          constraint={drawers.constraintDrawer.constraint}
          projectId={projectId}
          features={data ? [
            ...data.requirements.must_have,
            ...data.requirements.should_have,
            ...data.requirements.could_have,
            ...data.requirements.out_of_scope,
          ] : []}
          onClose={() => drawers.setConstraintDrawer({ open: false, constraint: null })}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
        />
      )}

      {/* Feature Drawer */}
      {drawers.featureDrawer.open && drawers.featureDrawer.feature && (
        <FeatureDrawer
          feature={drawers.featureDrawer.feature}
          projectId={projectId}
          onClose={() => drawers.setFeatureDrawer({ open: false, feature: null })}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
        />
      )}

      {/* Business Driver Detail Drawer */}
      {drawers.driverDrawer.open && drawers.driverDrawer.initialData && (
        <BusinessDriverDetailDrawer
          driverId={drawers.driverDrawer.driverId}
          driverType={drawers.driverDrawer.driverType}
          projectId={projectId}
          initialData={drawers.driverDrawer.initialData}
          stakeholders={data?.stakeholders}
          onClose={() => drawers.setDriverDrawer({ open: false, driverId: '', driverType: 'pain', initialData: null })}
          onConfirm={actions.handleConfirm}
          onNeedsReview={actions.handleNeedsReview}
        />
      )}
    </div>
  )
}
