import { useState, useCallback, useMemo } from 'react'
import {
  createWorkflow,
  updateWorkflow,
  deleteWorkflow,
  createWorkflowStep,
  updateWorkflowStep,
  deleteWorkflowStep,
  pairWorkflows,
  createDataEntity,
  deleteDataEntity,
  generateSolutionFlow,
} from '@/lib/api'
import type { BRDWorkspaceData, AutomationLevel } from '@/types/workspace'

interface WorkflowCRUDDeps {
  projectId: string
  data: BRDWorkspaceData | null
  loadData: () => Promise<void>
  showImpactPreview: (entityType: string, entityId: string, entityName: string, onDelete: () => void) => void
}

export function useBRDWorkflowCRUD({ projectId, data, loadData, showImpactPreview }: WorkflowCRUDDeps) {
  const [showCreateDataEntity, setShowCreateDataEntity] = useState(false)
  const [showCreateWorkflow, setShowCreateWorkflow] = useState(false)
  const [showSolutionFlowModal, setShowSolutionFlowModal] = useState(false)
  const [isGeneratingSolutionFlow, setIsGeneratingSolutionFlow] = useState(false)

  // Entity lookup for solution flow — resolves UUIDs to names
  const entityLookup = useMemo(() => {
    if (!data) return undefined
    const allFeatures = [
      ...(data.requirements?.must_have || []),
      ...(data.requirements?.should_have || []),
      ...(data.requirements?.could_have || []),
      ...(data.requirements?.out_of_scope || []),
    ]
    return {
      features: Object.fromEntries(allFeatures.map(f => [f.id, f.name])),
      workflows: Object.fromEntries((data.workflow_pairs || []).map(w => [w.id, w.name])),
      data_entities: Object.fromEntries((data.data_entities || []).map(d => [d.id, d.name])),
    }
  }, [data])

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
    const unpaired = data.workflow_pairs.filter(
      (wp) => wp.id !== workflowId && !wp.current_workflow_id && wp.future_workflow_id
    )
    if (unpaired.length === 0) {
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

  // Data Entity CRUD
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

  const handleGenerateSolutionFlow = useCallback(async () => {
    setIsGeneratingSolutionFlow(true)
    try {
      await generateSolutionFlow(projectId)
      await loadData()
    } catch (err) {
      console.error('Failed to generate solution flow:', err)
    } finally {
      setIsGeneratingSolutionFlow(false)
    }
  }, [projectId, loadData])

  return {
    // Modal state
    showCreateDataEntity,
    setShowCreateDataEntity,
    showCreateWorkflow,
    setShowCreateWorkflow,
    showSolutionFlowModal,
    setShowSolutionFlowModal,
    isGeneratingSolutionFlow,
    entityLookup,
    editWorkflowData,
    setEditWorkflowData,
    stepEditorState,
    setStepEditorState,
    // Workflow CRUD
    handleCreateWorkflow,
    handleEditWorkflow,
    handleUpdateWorkflow,
    handleDeleteWorkflow,
    handleEditStep,
    handleCreateStep,
    handleUpdateStep,
    handleDeleteStep,
    handlePairWorkflow,
    // Data Entity CRUD
    handleCreateDataEntity,
    handleDeleteDataEntity,
    handleDeleteDataEntityWithPreview,
    // Solution Flow
    handleGenerateSolutionFlow,
  }
}
