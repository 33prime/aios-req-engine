'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { FileText, RefreshCw } from 'lucide-react'
import { BusinessContextSection } from './sections/BusinessContextSection'
import { ActorsSection } from './sections/ActorsSection'
import { WorkflowsSection } from './sections/WorkflowsSection'
import { RequirementsSection } from './sections/RequirementsSection'
import { ConstraintsSection } from './sections/ConstraintsSection'
import { DataEntitiesSection } from './sections/DataEntitiesSection'
import { StakeholdersSection } from './sections/StakeholdersSection'
import { IntelligenceSection } from './sections/IntelligenceSection'
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
import {
  getBRDWorkspaceData,
  getBRDHealth,
  processCascades,
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
  updateCanvasRole,
  inferConstraints,
  listOpenQuestions,
} from '@/lib/api'
import type { NextAction } from '@/lib/api'
import { CompletenessRing } from './components/CompletenessRing'
import { ACTION_EXECUTION_MAP } from '@/lib/action-constants'
import type { BRDWorkspaceData, BRDHealthData, MoSCoWGroup, StakeholderBRDSummary, AutomationLevel, SectionScore, OpenQuestion } from '@/types/workspace'

interface BRDCanvasProps {
  projectId: string
  initialData?: BRDWorkspaceData | null
  initialNextActions?: NextAction[] | null
  onRefresh?: () => void
  onSendToChat?: (action: NextAction) => void
  pendingAction?: NextAction | null
  onPendingActionConsumed?: () => void
  onActiveSectionChange?: (sectionId: string) => void
}

export function BRDCanvas({ projectId, initialData, initialNextActions, onRefresh, onSendToChat, pendingAction, onPendingActionConsumed, onActiveSectionChange }: BRDCanvasProps) {
  const [data, setData] = useState<BRDWorkspaceData | null>(initialData ?? null)
  const [isLoading, setIsLoading] = useState(!initialData)
  const [error, setError] = useState<string | null>(null)

  // Sync from parent when SWR revalidates (e.g. triggered by Realtime)
  useEffect(() => {
    if (initialData) {
      setData(initialData)
    }
  }, [initialData])

  // Scroll tracking — report active BRD section via IntersectionObserver
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container || !onActiveSectionChange) return

    const sectionIds = [
      'brd-section-questions', 'brd-section-business-context', 'brd-section-personas',
      'brd-section-workflows', 'brd-section-features', 'brd-section-data-entities',
      'brd-section-stakeholders', 'brd-section-constraints',
    ]
    const visibleRatios = new Map<string, number>()
    let debounceTimer: ReturnType<typeof setTimeout> | null = null

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          visibleRatios.set(entry.target.id, entry.intersectionRatio)
        }
        if (debounceTimer) clearTimeout(debounceTimer)
        debounceTimer = setTimeout(() => {
          let maxRatio = 0
          let maxId = ''
          for (const [id, ratio] of visibleRatios) {
            if (ratio > maxRatio) { maxRatio = ratio; maxId = id }
          }
          if (maxId && maxRatio > 0) {
            onActiveSectionChange(maxId.replace('brd-section-', ''))
          }
        }, 200)
      },
      { root: container, threshold: [0, 0.1, 0.3, 0.5, 0.7, 1.0] }
    )

    for (const id of sectionIds) {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    }

    return () => {
      observer.disconnect()
      if (debounceTimer) clearTimeout(debounceTimer)
    }
  }, [onActiveSectionChange, data]) // re-observe when data loads

  // Health data (lifted from HealthPanel for IntelligenceSection)
  const [health, setHealth] = useState<BRDHealthData | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [isRefreshingHealth, setIsRefreshingHealth] = useState(false)

  // Next Best Actions — now handled by BrainPanel (separate API call)
  // Legacy: keep for pendingAction backward compat from OverviewPanel
  const nextActions: NextAction[] = data?.next_actions ?? initialNextActions ?? []

  // Open Questions
  const [openQuestions, setOpenQuestions] = useState<OpenQuestion[]>([])
  const [questionsLoading, setQuestionsLoading] = useState(true)

  const loadOpenQuestions = useCallback(async () => {
    try {
      setQuestionsLoading(true)
      const result = await listOpenQuestions(projectId, { status: 'open', limit: 20 })
      setOpenQuestions(result)
    } catch (err) {
      console.error('Failed to load open questions:', err)
    } finally {
      setQuestionsLoading(false)
    }
  }, [projectId])

  const loadHealth = useCallback(async () => {
    try {
      setHealthLoading(true)
      const result = await getBRDHealth(projectId)
      setHealth(result)
    } catch (err) {
      console.error('Failed to load BRD health:', err)
    } finally {
      setHealthLoading(false)
    }
  }, [projectId])

  const handleRefreshHealth = useCallback(async () => {
    setIsRefreshingHealth(true)
    try {
      await processCascades(projectId)
      await loadHealth()
    } catch (err) {
      console.error('Failed to process cascades:', err)
    } finally {
      setIsRefreshingHealth(false)
    }
  }, [projectId, loadHealth])

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
    // Skip BRD data fetch if parent already provided it (next_actions are included in BRD response)
    if (!initialData) loadData()
    // Health is always loaded fresh (lightweight, not duplicated by parent)
    loadHealth()
    loadOpenQuestions()
  }, [loadData, loadHealth, loadOpenQuestions, initialData])

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
      const result = await batchConfirmEntities(projectId, entityType, ids, 'confirmed_consultant')
      // If backend confirmed fewer than expected, reload to get truth
      if (result.updated_count < ids.length) {
        console.warn(`Batch confirm: only ${result.updated_count}/${ids.length} updated — reloading`)
        loadData()
      }
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

  // Helper to close all drawers
  const closeAllDrawers = useCallback(() => {
    setStakeholderDrawer({ open: false, stakeholder: null })
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setPersonaDrawer({ open: false, persona: null })
    setConstraintDrawer({ open: false, constraint: null })
    setFeatureDrawer({ open: false, feature: null })
    setDriverDrawer({ open: false, driverId: '', driverType: 'pain', initialData: null })
    setVisionDrawer(false)
    setClientIntelDrawer(false)
    setDataEntityDrawer({ open: false, entityId: '' })
  }, [])

  const handleOpenConfidence = useCallback((entityType: string, entityId: string, entityName: string, status?: string | null) => {
    if (!data) return

    // Route to entity-specific drawers
    if (entityType === 'workflow') {
      closeAllDrawers()
      setWorkflowDetailDrawer({ open: true, workflowId: entityId })
      return
    }
    if (entityType === 'business_driver') {
      // Find the driver in pain_points, goals, or success_metrics
      const allDrivers = [
        ...data.business_context.pain_points.map(d => ({ ...d, _type: 'pain' as const })),
        ...data.business_context.goals.map(d => ({ ...d, _type: 'goal' as const })),
        ...data.business_context.success_metrics.map(d => ({ ...d, _type: 'kpi' as const })),
      ]
      const driver = allDrivers.find(d => d.id === entityId)
      if (driver) {
        closeAllDrawers()
        setDriverDrawer({ open: true, driverId: entityId, driverType: driver._type, initialData: driver })
      }
      return
    }
    if (entityType === 'persona') {
      const persona = data.actors.find(a => a.id === entityId)
      if (persona) {
        closeAllDrawers()
        setPersonaDrawer({ open: true, persona })
        return
      }
    }
    if (entityType === 'constraint') {
      const constraint = data.constraints.find(c => c.id === entityId)
      if (constraint) {
        closeAllDrawers()
        setConstraintDrawer({ open: true, constraint })
        return
      }
    }
    if (entityType === 'feature') {
      const allFeatures = [
        ...data.requirements.must_have,
        ...data.requirements.should_have,
        ...data.requirements.could_have,
        ...data.requirements.out_of_scope,
      ]
      const feature = allFeatures.find(f => f.id === entityId)
      if (feature) {
        closeAllDrawers()
        setFeatureDrawer({ open: true, feature })
        return
      }
    }
    if (entityType === 'data_entity') {
      closeAllDrawers()
      setDataEntityDrawer({ open: true, entityId })
      return
    }
    if (entityType === 'stakeholder') {
      const stakeholder = data.stakeholders.find(s => s.id === entityId)
      if (stakeholder) {
        closeAllDrawers()
        setStakeholderDrawer({ open: true, stakeholder })
        return
      }
    }
    // Fallback to generic confidence drawer
    closeAllDrawers()
    setConfidenceDrawer({ open: true, entityType, entityId, entityName, initialStatus: status })
  }, [data, closeAllDrawers])

  // ============================================================================
  // Workflow Step Detail Drawer
  // ============================================================================

  const [stepDetailDrawer, setStepDetailDrawer] = useState<{
    open: boolean
    stepId: string
  }>({ open: false, stepId: '' })

  const handleViewStepDetail = useCallback((stepId: string) => {
    // Close other drawers
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setStepDetailDrawer({ open: true, stepId })
  }, [])

  // ============================================================================
  // Workflow Detail Drawer
  // ============================================================================

  const [workflowDetailDrawer, setWorkflowDetailDrawer] = useState<{
    open: boolean
    workflowId: string
  }>({ open: false, workflowId: '' })

  const handleViewWorkflowDetail = useCallback((workflowId: string) => {
    // Close other drawers
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: true, workflowId })
  }, [])

  // ============================================================================
  // Entity-Specific Drawers
  // ============================================================================

  const [personaDrawer, setPersonaDrawer] = useState<{
    open: boolean; persona: import('@/types/workspace').PersonaBRDSummary | null
  }>({ open: false, persona: null })

  const [constraintDrawer, setConstraintDrawer] = useState<{
    open: boolean; constraint: import('@/types/workspace').ConstraintItem | null
  }>({ open: false, constraint: null })

  const [featureDrawer, setFeatureDrawer] = useState<{
    open: boolean; feature: import('@/types/workspace').FeatureBRDSummary | null
  }>({ open: false, feature: null })

  const [driverDrawer, setDriverDrawer] = useState<{
    open: boolean; driverId: string; driverType: 'pain' | 'goal' | 'kpi'; initialData: import('@/types/workspace').BusinessDriver | null
  }>({ open: false, driverId: '', driverType: 'pain', initialData: null })

  // ============================================================================
  // Vision Detail Drawer
  // ============================================================================

  const [visionDrawer, setVisionDrawer] = useState(false)
  const [clientIntelDrawer, setClientIntelDrawer] = useState(false)

  const handleOpenVisionDetail = useCallback(() => {
    // Close other drawers
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setClientIntelDrawer(false)
    setVisionDrawer(true)
  }, [])

  const handleOpenBackgroundDetail = useCallback(() => {
    // Close other drawers
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setVisionDrawer(false)
    setClientIntelDrawer(true)
  }, [])

  // ============================================================================
  // Action Execution
  // ============================================================================

  const handleActionExecute = useCallback((action: NextAction) => {
    const execType = ACTION_EXECUTION_MAP[action.action_type]

    switch (action.action_type) {
      case 'confirm_critical': {
        if (!data) break
        const unconfirmed = data.requirements.must_have
          .filter(f => f.confirmation_status !== 'confirmed_consultant' && f.confirmation_status !== 'confirmed_client')
          .map(f => f.id)
        if (unconfirmed.length > 0) {
          handleConfirmAll('feature', unconfirmed)
        }
        // Scroll to requirements section so user sees the update
        document.getElementById('brd-section-features')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        break
      }

      case 'missing_vision':
        closeAllDrawers()
        setVisionDrawer(true)
        break

      case 'missing_evidence':
      case 'temporal_stale':
      case 'validate_pains':
        if (action.target_entity_id && action.target_entity_type) {
          handleOpenConfidence(action.target_entity_type, action.target_entity_id, action.title)
        }
        break

      case 'section_gap': {
        const sectionMap: Record<string, string> = {
          // Singular keys (entity types)
          feature: 'brd-section-features',
          persona: 'brd-section-personas',
          vp_step: 'brd-section-workflows',
          constraint: 'brd-section-constraints',
          data_entity: 'brd-section-data-entities',
          stakeholder: 'brd-section-stakeholders',
          // Plural keys (completeness section names from backend)
          features: 'brd-section-features',
          personas: 'brd-section-personas',
          workflows: 'brd-section-workflows',
          constraints: 'brd-section-constraints',
          data_entities: 'brd-section-data-entities',
          stakeholders: 'brd-section-stakeholders',
          vision: 'brd-section-business-context',
        }
        const sectionId = sectionMap[action.target_entity_type] || 'brd-section-business-context'
        document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        break
      }

      case 'stakeholder_gap':
      case 'cross_entity_gap':
        document.getElementById('brd-section-stakeholders')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        break

      case 'missing_metrics':
        document.getElementById('brd-section-business-context')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        break

      case 'open_question_critical':
      case 'open_question_blocking':
        document.getElementById('brd-section-questions')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
        break

      case 'stale_belief':
      case 'contradiction_unresolved':
      case 'revisit_decision':
        // These need AI reasoning — send to chat
        onSendToChat?.(action)
        break

      default:
        // Unknown action type — try chat fallback
        if (execType === 'chat') {
          onSendToChat?.(action)
        }
    }
  }, [data, handleConfirmAll, handleOpenConfidence, closeAllDrawers, onSendToChat])

  // Consume pending action from cross-view navigation (Overview → BRD)
  useEffect(() => {
    if (pendingAction && data) {
      handleActionExecute(pendingAction)
      onPendingActionConsumed?.()
    }
  }, [pendingAction, data, handleActionExecute, onPendingActionConsumed])

  // ============================================================================
  // Data Entity Detail Drawer
  // ============================================================================

  const [dataEntityDrawer, setDataEntityDrawer] = useState<{
    open: boolean
    entityId: string
  }>({ open: false, entityId: '' })

  const handleOpenDataEntityDetail = useCallback((entityId: string) => {
    setStakeholderDrawer({ open: false, stakeholder: null })
    setConfidenceDrawer((prev) => ({ ...prev, open: false }))
    setStepDetailDrawer({ open: false, stepId: '' })
    setWorkflowDetailDrawer({ open: false, workflowId: '' })
    setVisionDrawer(false)
    setClientIntelDrawer(false)
    setDataEntityDrawer({ open: true, entityId })
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

  // ============================================================================
  // Canvas Role
  // ============================================================================

  const handleCanvasRoleUpdate = useCallback(async (personaId: string, role: 'primary' | 'secondary' | null) => {
    if (!data) return

    // Optimistic update
    setData((prev) => {
      if (!prev) return prev
      return {
        ...prev,
        actors: prev.actors.map((a) =>
          a.id === personaId ? { ...a, canvas_role: role } : a
        ),
      }
    })

    try {
      await updateCanvasRole(projectId, personaId, role)
    } catch (err: unknown) {
      console.error('Failed to update canvas role:', err)
      // Show error message from backend (e.g., limit exceeded)
      const message = err instanceof Error ? err.message : 'Failed to update canvas role'
      alert(message)
      loadData()
    }
  }, [data, projectId, loadData])

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

  // Build section score map from completeness data
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
                <FileText className="w-6 h-6 text-[rgba(55,53,47,0.45)]" />
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

          {/* Intelligence Dashboard */}
          <IntelligenceSection
            data={data}
            health={health}
            healthLoading={healthLoading}
            onRefreshAll={handleRefreshHealth}
            isRefreshing={isRefreshingHealth}
          />

          {/* Open Questions (collapsed by default) */}
          <div id="brd-section-questions">
            <OpenQuestionsPanel
              projectId={projectId}
              questions={openQuestions}
              loading={questionsLoading}
              onMutate={loadOpenQuestions}
            />
          </div>

          {/* BRD Sections */}
          <div className="space-y-10">
        <div id="brd-section-business-context">
        <BusinessContextSection
          data={data.business_context}
          projectId={projectId}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onUpdateVision={handleUpdateVision}
          onUpdateBackground={handleUpdateBackground}
          onStatusClick={handleOpenConfidence}
          sectionScore={sectionScoreMap['vision'] || null}
          onOpenVisionDetail={handleOpenVisionDetail}
          onOpenBackgroundDetail={handleOpenBackgroundDetail}
          stakeholders={data.stakeholders}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-personas">
        <ActorsSection
          actors={data.actors}
          workflows={data.workflows}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onRefreshEntity={handleRefreshEntity}
          onStatusClick={handleOpenConfidence}
          onCanvasRoleUpdate={handleCanvasRoleUpdate}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-workflows">
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
          onViewStepDetail={handleViewStepDetail}
          onViewWorkflowDetail={handleViewWorkflowDetail}
          sectionScore={sectionScoreMap['workflows'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-features">
        <RequirementsSection
          requirements={data.requirements}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onMovePriority={handleMovePriority}
          onRefreshEntity={handleRefreshEntity}
          onStatusClick={handleOpenConfidence}
          sectionScore={sectionScoreMap['features'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-data-entities">
        <DataEntitiesSection
          projectId={projectId}
          dataEntities={data.data_entities}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onCreateEntity={() => setShowCreateDataEntity(true)}
          onDeleteEntity={handleDeleteDataEntityWithPreview}
          onRefreshEntity={handleRefreshEntity}
          onStatusClick={handleOpenConfidence}
          onOpenDetail={handleOpenDataEntityDetail}
          sectionScore={sectionScoreMap['data_entities'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-stakeholders">
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
          sectionScore={sectionScoreMap['stakeholders'] || null}
        />
        </div>

        <div className="border-t border-[#e9e9e7]" />

        <div id="brd-section-constraints">
        <ConstraintsSection
          constraints={data.constraints}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onStatusClick={handleOpenConfidence}
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

      {/* Workflow Step Detail Drawer */}
      {stepDetailDrawer.open && stepDetailDrawer.stepId && (
        <WorkflowStepDetailDrawer
          stepId={stepDetailDrawer.stepId}
          projectId={projectId}
          onClose={() => setStepDetailDrawer({ open: false, stepId: '' })}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
        />
      )}

      {/* Workflow Detail Drawer */}
      {workflowDetailDrawer.open && workflowDetailDrawer.workflowId && (
        <WorkflowDetailDrawer
          workflowId={workflowDetailDrawer.workflowId}
          projectId={projectId}
          stakeholders={data?.stakeholders}
          onClose={() => setWorkflowDetailDrawer({ open: false, workflowId: '' })}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onViewStepDetail={(stepId) => {
            setWorkflowDetailDrawer({ open: false, workflowId: '' })
            setStepDetailDrawer({ open: true, stepId })
          }}
        />
      )}

      {/* Vision Detail Drawer */}
      {visionDrawer && (
        <VisionDetailDrawer
          projectId={projectId}
          initialVision={data.business_context.vision}
          onClose={() => setVisionDrawer(false)}
          onVisionUpdated={(vision) => {
            setData((prev) => prev ? {
              ...prev,
              business_context: { ...prev.business_context, vision },
            } : prev)
          }}
        />
      )}

      {/* Client Intelligence Drawer */}
      {clientIntelDrawer && (
        <ClientIntelligenceDrawer
          projectId={projectId}
          onClose={() => setClientIntelDrawer(false)}
        />
      )}

      {/* Data Entity Detail Drawer */}
      {dataEntityDrawer.open && dataEntityDrawer.entityId && (
        <DataEntityDetailDrawer
          entityId={dataEntityDrawer.entityId}
          projectId={projectId}
          onClose={() => setDataEntityDrawer({ open: false, entityId: '' })}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
        />
      )}

      {/* Confidence Drawer (fallback) */}
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

      {/* Persona Drawer */}
      {personaDrawer.open && personaDrawer.persona && (
        <PersonaDrawer
          persona={personaDrawer.persona}
          projectId={projectId}
          stakeholders={data?.stakeholders}
          features={data ? [
            ...data.requirements.must_have,
            ...data.requirements.should_have,
            ...data.requirements.could_have,
            ...data.requirements.out_of_scope,
          ] : []}
          onClose={() => setPersonaDrawer({ open: false, persona: null })}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
        />
      )}

      {/* Constraint Drawer */}
      {constraintDrawer.open && constraintDrawer.constraint && (
        <ConstraintDrawer
          constraint={constraintDrawer.constraint}
          projectId={projectId}
          features={data ? [
            ...data.requirements.must_have,
            ...data.requirements.should_have,
            ...data.requirements.could_have,
            ...data.requirements.out_of_scope,
          ] : []}
          onClose={() => setConstraintDrawer({ open: false, constraint: null })}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
        />
      )}

      {/* Feature Drawer */}
      {featureDrawer.open && featureDrawer.feature && (
        <FeatureDrawer
          feature={featureDrawer.feature}
          projectId={projectId}
          onClose={() => setFeatureDrawer({ open: false, feature: null })}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
        />
      )}

      {/* Business Driver Detail Drawer */}
      {driverDrawer.open && driverDrawer.initialData && (
        <BusinessDriverDetailDrawer
          driverId={driverDrawer.driverId}
          driverType={driverDrawer.driverType}
          projectId={projectId}
          initialData={driverDrawer.initialData}
          stakeholders={data?.stakeholders}
          onClose={() => setDriverDrawer({ open: false, driverId: '', driverType: 'pain', initialData: null })}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
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
