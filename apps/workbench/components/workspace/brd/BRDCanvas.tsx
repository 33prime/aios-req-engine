'use client'

import { useState, useEffect, useCallback } from 'react'
import { FileText, RefreshCw } from 'lucide-react'
import { BusinessContextSection } from './sections/BusinessContextSection'
import { ActorsSection } from './sections/ActorsSection'
import { WorkflowsSection } from './sections/WorkflowsSection'
import { RequirementsSection } from './sections/RequirementsSection'
import { ConstraintsSection } from './sections/ConstraintsSection'
import { DataEntitiesSection } from './sections/DataEntitiesSection'
import { StakeholdersSection } from './sections/StakeholdersSection'
import { WorkflowCreateModal } from './components/WorkflowCreateModal'
import { WorkflowStepEditor } from './components/WorkflowStepEditor'
import { DataEntityCreateModal } from './components/DataEntityCreateModal'
import { StakeholderDetailDrawer } from './components/StakeholderDetailDrawer'
import { ConfidenceDrawer } from './components/ConfidenceDrawer'
import { HealthPanel } from './components/HealthPanel'
import { ImpactPreviewModal } from './components/ImpactPreviewModal'
import {
  getBRDWorkspaceData,
  updateProjectVision,
  updateProjectBackground,
  updateFeaturePriority,
  batchConfirmEntities,
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  createWorkflowStep,
  updateWorkflowStep,
  deleteWorkflowStep,
  pairWorkflows,
  createDataEntity,
  deleteDataEntity,
  refreshStaleEntity,
} from '@/lib/api'
import type { BRDWorkspaceData, MoSCoWGroup, StakeholderBRDSummary, AutomationLevel } from '@/types/workspace'

interface BRDCanvasProps {
  projectId: string
  onRefresh?: () => void
}

export function BRDCanvas({ projectId, onRefresh }: BRDCanvasProps) {
  const [data, setData] = useState<BRDWorkspaceData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const result = await getBRDWorkspaceData(projectId)
      setData(result)
    } catch (err) {
      console.error('Failed to load BRD data:', err)
      setError('Failed to load BRD data')
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Optimistic confirm: update local state immediately, then sync
  const handleConfirm = useCallback(async (entityType: string, entityId: string) => {
    if (!data) return

    // Optimistic update
    setData((prev) => {
      if (!prev) return prev
      return applyConfirmationUpdate(prev, entityType, entityId, 'confirmed_consultant')
    })

    try {
      await batchConfirmEntities(projectId, entityType, [entityId], 'confirmed_consultant')
    } catch (err) {
      console.error('Failed to confirm entity:', err)
      // Revert on failure
      loadData()
    }
  }, [data, projectId, loadData])

  const handleNeedsReview = useCallback(async (entityType: string, entityId: string) => {
    if (!data) return

    setData((prev) => {
      if (!prev) return prev
      return applyConfirmationUpdate(prev, entityType, entityId, 'needs_client')
    })

    try {
      await batchConfirmEntities(projectId, entityType, [entityId], 'needs_client')
    } catch (err) {
      console.error('Failed to mark entity for review:', err)
      loadData()
    }
  }, [data, projectId, loadData])

  const handleConfirmAll = useCallback(async (entityType: string, ids: string[]) => {
    if (!data || ids.length === 0) return

    // Optimistic update all
    setData((prev) => {
      if (!prev) return prev
      let updated = prev
      for (const id of ids) {
        updated = applyConfirmationUpdate(updated, entityType, id, 'confirmed_consultant')
      }
      return updated
    })

    try {
      await batchConfirmEntities(projectId, entityType, ids, 'confirmed_consultant')
    } catch (err) {
      console.error('Failed to batch confirm:', err)
      loadData()
    }
  }, [data, projectId, loadData])

  const handleMovePriority = useCallback(async (featureId: string, targetGroup: MoSCoWGroup) => {
    if (!data) return

    // Optimistic move
    setData((prev) => {
      if (!prev) return prev
      return moveFeatureToGroup(prev, featureId, targetGroup)
    })

    try {
      await updateFeaturePriority(projectId, featureId, targetGroup)
    } catch (err) {
      console.error('Failed to update feature priority:', err)
      loadData()
    }
  }, [data, projectId, loadData])

  const handleUpdateVision = useCallback(async (vision: string) => {
    if (!data) return

    // Optimistic update
    setData((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        business_context: { ...prev.business_context, vision },
      }
    })

    try {
      await updateProjectVision(projectId, vision)
    } catch (err) {
      console.error('Failed to update vision:', err)
      loadData()
    }
  }, [data, projectId, loadData])

  const handleUpdateBackground = useCallback(async (background: string) => {
    if (!data) return

    // Optimistic update
    setData((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        business_context: { ...prev.business_context, background },
      }
    })

    try {
      await updateProjectBackground(projectId, background)
    } catch (err) {
      console.error('Failed to update background:', err)
      loadData()
    }
  }, [data, projectId, loadData])

  // ============================================================================
  // Staleness / Refresh
  // ============================================================================

  const handleRefreshEntity = useCallback(async (entityType: string, entityId: string) => {
    try {
      await refreshStaleEntity(projectId, entityType, entityId)
      loadData()
    } catch (err) {
      console.error('Failed to refresh entity:', err)
    }
  }, [projectId, loadData])

  // ============================================================================
  // Impact Preview (delete confirmation)
  // ============================================================================

  const [impactPreview, setImpactPreview] = useState<{
    open: boolean
    entityType: string
    entityId: string
    entityName: string
    onDelete: () => void
  }>({ open: false, entityType: '', entityId: '', entityName: '', onDelete: () => {} })

  const showImpactPreview = useCallback((entityType: string, entityId: string, entityName: string, onDelete: () => void) => {
    setImpactPreview({ open: true, entityType, entityId, entityName, onDelete })
  }, [])

  // ============================================================================
  // Stakeholder Detail Drawer
  // ============================================================================

  const [stakeholderDrawer, setStakeholderDrawer] = useState<{
    open: boolean
    stakeholder: StakeholderBRDSummary | null
  }>({ open: false, stakeholder: null })

  // ============================================================================
  // Confidence Drawer
  // ============================================================================

  const [confidenceDrawer, setConfidenceDrawer] = useState<{
    open: boolean
    entityType: string
    entityId: string
    entityName: string
    initialStatus?: string | null
  }>({ open: false, entityType: '', entityId: '', entityName: '' })

  const handleOpenConfidence = useCallback((entityType: string, entityId: string, entityName: string, status?: string | null) => {
    // Close other drawers when opening confidence
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer({ open: true, entityType, entityId, entityName, initialStatus: status })
  }, [])

  // ============================================================================
  // Workflow CRUD
  // ============================================================================

  const [showCreateDataEntity, setShowCreateDataEntity] = useState(false)
  const [showCreateWorkflow, setShowCreateWorkflow] = useState(false)

  // Edit workflow state
  const [editWorkflowData, setEditWorkflowData] = useState<{
    id: string
    name: string
    description?: string
    owner?: string
    state_type?: 'current' | 'future'
    frequency_per_week?: number
    hourly_rate?: number
  } | null>(null)

  // Step editor state — extended with stepId + initialData for edit mode
  const [stepEditorState, setStepEditorState] = useState<{
    open: boolean
    workflowId: string
    stateType: 'current' | 'future'
    stepId?: string
    initialData?: {
      label?: string
      description?: string
      time_minutes?: number | null
      automation_level?: AutomationLevel
      operation_type?: string | null
      pain_description?: string | null
      benefit_description?: string | null
    }
  }>({ open: false, workflowId: '', stateType: 'future' })

  const handleCreateWorkflow = useCallback(async (wfData: {
    name: string
    description: string
    owner: string
    state_type: 'current' | 'future'
    frequency_per_week: number
    hourly_rate: number
  }) => {
    try {
      await createWorkflow(projectId, wfData)
      setShowCreateWorkflow(false)
      loadData()
    } catch (err) {
      console.error('Failed to create workflow:', err)
    }
  }, [projectId, loadData])

  const handleEditWorkflow = useCallback((workflowId: string) => {
    if (!data?.workflow_pairs) return
    const pair = data.workflow_pairs.find((p) => p.id === workflowId)
    if (!pair) return
    setEditWorkflowData({
      id: pair.id,
      name: pair.name,
      description: pair.description,
      owner: pair.owner || undefined,
    })
  }, [data])

  const handleUpdateWorkflow = useCallback(async (wfData: {
    name: string
    description: string
    owner: string
    state_type: 'current' | 'future'
    frequency_per_week: number
    hourly_rate: number
  }) => {
    if (!editWorkflowData) return
    try {
      await updateWorkflow(projectId, editWorkflowData.id, {
        name: wfData.name,
        description: wfData.description,
        owner: wfData.owner,
        frequency_per_week: wfData.frequency_per_week,
        hourly_rate: wfData.hourly_rate,
      })
      setEditWorkflowData(null)
      loadData()
    } catch (err) {
      console.error('Failed to update workflow:', err)
    }
  }, [projectId, editWorkflowData, loadData])

  const handleDeleteWorkflow = useCallback(async (workflowId: string) => {
    try {
      await deleteWorkflow(projectId, workflowId)
      loadData()
    } catch (err) {
      console.error('Failed to delete workflow:', err)
    }
  }, [projectId, loadData])

  const handleEditStep = useCallback((workflowId: string, stepId: string) => {
    if (!data?.workflow_pairs) return
    // Find the step in workflow pairs
    for (const pair of data.workflow_pairs) {
      const allSteps = [...pair.current_steps, ...pair.future_steps]
      const step = allSteps.find((s) => s.id === stepId)
      if (step) {
        const isCurrent = pair.current_steps.some((s) => s.id === stepId)
        const actualWorkflowId = isCurrent ? pair.current_workflow_id : pair.future_workflow_id
        setStepEditorState({
          open: true,
          workflowId: actualWorkflowId || workflowId,
          stateType: isCurrent ? 'current' : 'future',
          stepId: step.id,
          initialData: {
            label: step.label,
            description: step.description ?? undefined,
            time_minutes: step.time_minutes,
            automation_level: step.automation_level,
            operation_type: step.operation_type,
            pain_description: step.pain_description,
            benefit_description: step.benefit_description,
          },
        })
        return
      }
    }
  }, [data])

  const handleCreateStep = useCallback(async (stepData: {
    label: string
    description: string
    time_minutes: number | undefined
    automation_level: string
    operation_type: string | undefined
    pain_description: string
    benefit_description: string
  }) => {
    if (!stepEditorState.workflowId) return
    // Compute step_index: count existing steps in the pair for this side
    const pair = data?.workflow_pairs?.find(
      (p) => p.current_workflow_id === stepEditorState.workflowId || p.future_workflow_id === stepEditorState.workflowId
    )
    const existingSteps = stepEditorState.stateType === 'current' ? pair?.current_steps : pair?.future_steps
    const nextIndex = (existingSteps?.length || 0) + 1

    try {
      await createWorkflowStep(projectId, stepEditorState.workflowId, {
        step_index: nextIndex,
        label: stepData.label,
        description: stepData.description || undefined,
        time_minutes: stepData.time_minutes,
        automation_level: stepData.automation_level as 'manual' | 'semi_automated' | 'fully_automated',
        operation_type: stepData.operation_type,
        pain_description: stepData.pain_description || undefined,
        benefit_description: stepData.benefit_description || undefined,
      })
      setStepEditorState({ open: false, workflowId: '', stateType: 'future' })
      loadData()
    } catch (err) {
      console.error('Failed to create step:', err)
    }
  }, [projectId, stepEditorState, data, loadData])

  const handleUpdateStep = useCallback(async (stepData: {
    label: string
    description: string
    time_minutes: number | undefined
    automation_level: string
    operation_type: string | undefined
    pain_description: string
    benefit_description: string
  }) => {
    if (!stepEditorState.workflowId || !stepEditorState.stepId) return
    try {
      await updateWorkflowStep(projectId, stepEditorState.workflowId, stepEditorState.stepId, {
        label: stepData.label,
        description: stepData.description || undefined,
        time_minutes: stepData.time_minutes,
        automation_level: stepData.automation_level,
        operation_type: stepData.operation_type || undefined,
        pain_description: stepData.pain_description || undefined,
        benefit_description: stepData.benefit_description || undefined,
      })
      setStepEditorState({ open: false, workflowId: '', stateType: 'future' })
      loadData()
    } catch (err) {
      console.error('Failed to update step:', err)
    }
  }, [projectId, stepEditorState, loadData])

  const handleDeleteStep = useCallback(async (workflowId: string, stepId: string) => {
    try {
      await deleteWorkflowStep(projectId, workflowId, stepId)
      loadData()
    } catch (err) {
      console.error('Failed to delete step:', err)
    }
  }, [projectId, loadData])

  const handlePairWorkflow = useCallback(async (workflowId: string) => {
    if (!data?.workflow_pairs) return
    // Find unpaired current-state workflows to pair with
    const unpaired = data.workflow_pairs.filter(
      (wp) => wp.id !== workflowId && !wp.current_workflow_id && wp.future_workflow_id
    )
    if (unpaired.length === 0) {
      // No unpaired workflows available — prompt user via window.prompt
      const targetId = window.prompt('Enter the workflow ID to pair with (no unpaired workflows found):')
      if (targetId) {
        try {
          await pairWorkflows(projectId, workflowId, targetId)
          loadData()
        } catch (err) {
          console.error('Failed to pair workflows:', err)
        }
      }
      return
    }
    // Simple selection: use the first unpaired, or prompt if multiple
    const names = unpaired.map((wp, i) => `${i + 1}. ${wp.name}`).join('\n')
    const choice = window.prompt(`Select workflow to pair with:\n${names}\n\nEnter number:`)
    if (choice) {
      const idx = parseInt(choice, 10) - 1
      if (idx >= 0 && idx < unpaired.length) {
        try {
          await pairWorkflows(projectId, workflowId, unpaired[idx].id)
          loadData()
        } catch (err) {
          console.error('Failed to pair workflows:', err)
        }
      }
    }
  }, [data, projectId, loadData])

  // ============================================================================
  // Data Entity CRUD
  // ============================================================================

  const handleCreateDataEntity = useCallback(async (entityData: {
    name: string
    description: string
    entity_category: 'domain' | 'reference' | 'transactional' | 'system'
  }) => {
    try {
      await createDataEntity(projectId, entityData)
      setShowCreateDataEntity(false)
      loadData()
    } catch (err) {
      console.error('Failed to create data entity:', err)
    }
  }, [projectId, loadData])

  const handleDeleteDataEntity = useCallback(async (entityId: string) => {
    try {
      await deleteDataEntity(projectId, entityId)
      loadData()
    } catch (err) {
      console.error('Failed to delete data entity:', err)
    }
  }, [projectId, loadData])

  const handleDeleteDataEntityWithPreview = useCallback((entityId: string, entityName: string) => {
    showImpactPreview('data_entity', entityId, entityName, () => handleDeleteDataEntity(entityId))
  }, [showImpactPreview, handleDeleteDataEntity])

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3FAF7A] mx-auto mb-3" />
        <p className="text-[13px] text-[rgba(55,53,47,0.45)]">Loading BRD...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <p className="text-red-500 mb-3">{error || 'No data available'}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 text-sm text-white bg-[#3FAF7A] rounded-md hover:bg-[#25785A] transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  // Compute readiness bar
  const totalEntities = countEntities(data)
  const confirmedEntities = countConfirmed(data)
  const readinessPercent = totalEntities > 0 ? Math.round((confirmedEntities / totalEntities) * 100) : 0

  // Count stale entities
  const staleCount = countStale(data)

  // Determine whether step editor is in create or edit mode
  const isStepEdit = !!stepEditorState.stepId

  return (
    <div className="max-w-4xl mx-auto py-8 px-6">
      {/* Document header */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <FileText className="w-6 h-6 text-[rgba(55,53,47,0.45)]" />
            <h1 className="text-[28px] font-bold text-[#37352f]">Business Requirements Document</h1>
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
              className="h-full bg-[#3FAF7A] rounded-full transition-all duration-300"
              style={{ width: `${readinessPercent}%` }}
            />
          </div>
          <span className="text-[12px] font-medium text-[rgba(55,53,47,0.65)] whitespace-nowrap">
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

      {/* Health Panel */}
      <HealthPanel projectId={projectId} onDataRefresh={loadData} />

      {/* BRD Sections */}
      <div className="space-y-10">
        <BusinessContextSection
          data={data.business_context}
          projectId={projectId}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onUpdateVision={handleUpdateVision}
          onUpdateBackground={handleUpdateBackground}
          onStatusClick={handleOpenConfidence}
        />

        <div className="border-t border-[#e9e9e7]" />

        <ActorsSection
          actors={data.actors}
          workflows={data.workflows}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onRefreshEntity={handleRefreshEntity}
          onStatusClick={handleOpenConfidence}
        />

        <div className="border-t border-[#e9e9e7]" />

        <WorkflowsSection
          workflows={data.workflows}
          workflowPairs={data.workflow_pairs}
          roiSummary={data.roi_summary}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onCreateWorkflow={() => setShowCreateWorkflow(true)}
          onEditWorkflow={handleEditWorkflow}
          onDeleteWorkflow={handleDeleteWorkflow}
          onPairWorkflow={handlePairWorkflow}
          onCreateStep={(workflowId, stateType) =>
            setStepEditorState({ open: true, workflowId, stateType })
          }
          onEditStep={handleEditStep}
          onDeleteStep={handleDeleteStep}
          onRefreshEntity={handleRefreshEntity}
          onStatusClick={handleOpenConfidence}
        />

        <div className="border-t border-[#e9e9e7]" />

        <RequirementsSection
          requirements={data.requirements}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onMovePriority={handleMovePriority}
          onRefreshEntity={handleRefreshEntity}
          onStatusClick={handleOpenConfidence}
        />

        <div className="border-t border-[#e9e9e7]" />

        <DataEntitiesSection
          dataEntities={data.data_entities}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onCreateEntity={() => setShowCreateDataEntity(true)}
          onDeleteEntity={handleDeleteDataEntityWithPreview}
          onRefreshEntity={handleRefreshEntity}
          onStatusClick={handleOpenConfidence}
        />

        <div className="border-t border-[#e9e9e7]" />

        <StakeholdersSection
          stakeholders={data.stakeholders}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onOpenDetail={(stakeholder) => {
            setConfidenceDrawer((prev) => ({ ...prev, open: false }))
            setStakeholderDrawer({ open: true, stakeholder })
          }}
          onRefreshEntity={handleRefreshEntity}
          onStatusClick={handleOpenConfidence}
        />

        <div className="border-t border-[#e9e9e7]" />

        <ConstraintsSection
          constraints={data.constraints}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onStatusClick={handleOpenConfidence}
        />
      </div>

      {/* Data Entity Create Modal */}
      <DataEntityCreateModal
        open={showCreateDataEntity}
        onClose={() => setShowCreateDataEntity(false)}
        onSave={handleCreateDataEntity}
      />

      {/* Workflow Create/Edit Modal */}
      <WorkflowCreateModal
        open={showCreateWorkflow || !!editWorkflowData}
        onClose={() => {
          setShowCreateWorkflow(false)
          setEditWorkflowData(null)
        }}
        onSave={editWorkflowData ? handleUpdateWorkflow : handleCreateWorkflow}
        initialData={editWorkflowData || undefined}
      />

      {/* Workflow Step Create/Edit Editor */}
      <WorkflowStepEditor
        open={stepEditorState.open}
        stateType={stepEditorState.stateType}
        onClose={() => setStepEditorState({ open: false, workflowId: '', stateType: 'future' })}
        onSave={isStepEdit ? handleUpdateStep : handleCreateStep}
        initialData={stepEditorState.initialData}
      />

      {/* Impact Preview Modal */}
      <ImpactPreviewModal
        open={impactPreview.open}
        projectId={projectId}
        entityType={impactPreview.entityType}
        entityId={impactPreview.entityId}
        entityName={impactPreview.entityName}
        onClose={() => setImpactPreview((prev) => ({ ...prev, open: false }))}
        onConfirmDelete={impactPreview.onDelete}
      />

      {/* Stakeholder Detail Drawer */}
      {stakeholderDrawer.open && stakeholderDrawer.stakeholder && (
        <StakeholderDetailDrawer
          stakeholderId={stakeholderDrawer.stakeholder.id}
          projectId={projectId}
          initialData={stakeholderDrawer.stakeholder}
          onClose={() => setStakeholderDrawer({ open: false, stakeholder: null })}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
        />
      )}

      {/* Confidence Drawer */}
      {confidenceDrawer.open && (
        <ConfidenceDrawer
          entityType={confidenceDrawer.entityType}
          entityId={confidenceDrawer.entityId}
          entityName={confidenceDrawer.entityName}
          projectId={projectId}
          initialStatus={confidenceDrawer.initialStatus}
          onClose={() => setConfidenceDrawer((prev) => ({ ...prev, open: false }))}
          onConfirm={(entityType, entityId) => handleConfirm(entityType, entityId)}
          onNeedsReview={(entityType, entityId) => handleNeedsReview(entityType, entityId)}
        />
      )}
    </div>
  )
}

// ============================================================================
// Helper functions for optimistic updates
// ============================================================================

function applyConfirmationUpdate(
  data: BRDWorkspaceData,
  entityType: string,
  entityId: string,
  status: string,
): BRDWorkspaceData {
  const update = { ...data }

  if (entityType === 'business_driver') {
    update.business_context = {
      ...update.business_context,
      pain_points: update.business_context.pain_points.map((p) =>
        p.id === entityId ? { ...p, confirmation_status: status } : p
      ),
      goals: update.business_context.goals.map((g) =>
        g.id === entityId ? { ...g, confirmation_status: status } : g
      ),
      success_metrics: update.business_context.success_metrics.map((m) =>
        m.id === entityId ? { ...m, confirmation_status: status } : m
      ),
    }
  } else if (entityType === 'persona') {
    update.actors = update.actors.map((a) =>
      a.id === entityId ? { ...a, confirmation_status: status } : a
    )
  } else if (entityType === 'vp_step') {
    update.workflows = update.workflows.map((w) =>
      w.id === entityId ? { ...w, confirmation_status: status } : w
    )
  } else if (entityType === 'feature') {
    update.requirements = {
      must_have: update.requirements.must_have.map((f) =>
        f.id === entityId ? { ...f, confirmation_status: status } : f
      ),
      should_have: update.requirements.should_have.map((f) =>
        f.id === entityId ? { ...f, confirmation_status: status } : f
      ),
      could_have: update.requirements.could_have.map((f) =>
        f.id === entityId ? { ...f, confirmation_status: status } : f
      ),
      out_of_scope: update.requirements.out_of_scope.map((f) =>
        f.id === entityId ? { ...f, confirmation_status: status } : f
      ),
    }
  } else if (entityType === 'constraint') {
    update.constraints = update.constraints.map((c) =>
      c.id === entityId ? { ...c, confirmation_status: status } : c
    )
  } else if (entityType === 'workflow') {
    update.workflow_pairs = (update.workflow_pairs || []).map((wp) =>
      wp.id === entityId ? { ...wp, confirmation_status: status } : wp
    )
  } else if (entityType === 'data_entity') {
    update.data_entities = update.data_entities.map((d) =>
      d.id === entityId ? { ...d, confirmation_status: status } : d
    )
  } else if (entityType === 'stakeholder') {
    update.stakeholders = update.stakeholders.map((s) =>
      s.id === entityId ? { ...s, confirmation_status: status } : s
    )
  }

  return update
}

function moveFeatureToGroup(
  data: BRDWorkspaceData,
  featureId: string,
  targetGroup: MoSCoWGroup,
): BRDWorkspaceData {
  // Find and remove from current group
  let movedFeature = null
  const groups: MoSCoWGroup[] = ['must_have', 'should_have', 'could_have', 'out_of_scope']
  const newReqs = { ...data.requirements }

  for (const group of groups) {
    const idx = newReqs[group].findIndex((f) => f.id === featureId)
    if (idx !== -1) {
      movedFeature = { ...newReqs[group][idx], priority_group: targetGroup }
      newReqs[group] = [...newReqs[group].slice(0, idx), ...newReqs[group].slice(idx + 1)]
      break
    }
  }

  // Add to target group
  if (movedFeature) {
    newReqs[targetGroup] = [...newReqs[targetGroup], movedFeature]
  }

  return { ...data, requirements: newReqs }
}

function countEntities(data: BRDWorkspaceData): number {
  return (
    data.business_context.pain_points.length +
    data.business_context.goals.length +
    data.business_context.success_metrics.length +
    data.actors.length +
    data.workflows.length +
    data.requirements.must_have.length +
    data.requirements.should_have.length +
    data.requirements.could_have.length +
    data.constraints.length +
    data.data_entities.length +
    data.stakeholders.length
  )
}

function countConfirmed(data: BRDWorkspaceData): number {
  const isConfirmed = (s: string | null | undefined) =>
    s === 'confirmed_consultant' || s === 'confirmed_client'

  return (
    data.business_context.pain_points.filter((p) => isConfirmed(p.confirmation_status)).length +
    data.business_context.goals.filter((g) => isConfirmed(g.confirmation_status)).length +
    data.business_context.success_metrics.filter((m) => isConfirmed(m.confirmation_status)).length +
    data.actors.filter((a) => isConfirmed(a.confirmation_status)).length +
    data.workflows.filter((w) => isConfirmed(w.confirmation_status)).length +
    data.requirements.must_have.filter((f) => isConfirmed(f.confirmation_status)).length +
    data.requirements.should_have.filter((f) => isConfirmed(f.confirmation_status)).length +
    data.requirements.could_have.filter((f) => isConfirmed(f.confirmation_status)).length +
    data.constraints.filter((c) => isConfirmed(c.confirmation_status)).length +
    data.data_entities.filter((d) => isConfirmed(d.confirmation_status)).length +
    data.stakeholders.filter((s) => isConfirmed(s.confirmation_status)).length
  )
}

function countStale(data: BRDWorkspaceData): number {
  return (
    data.actors.filter((a) => a.is_stale).length +
    data.workflows.filter((w) => w.is_stale).length +
    data.requirements.must_have.filter((f) => f.is_stale).length +
    data.requirements.should_have.filter((f) => f.is_stale).length +
    data.requirements.could_have.filter((f) => f.is_stale).length +
    data.requirements.out_of_scope.filter((f) => f.is_stale).length +
    data.data_entities.filter((d) => d.is_stale).length
  )
}
