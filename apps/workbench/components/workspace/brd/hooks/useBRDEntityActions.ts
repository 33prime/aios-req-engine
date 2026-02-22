import { useCallback, useEffect } from 'react'
import type { Dispatch, SetStateAction } from 'react'
import {
  batchConfirmEntities,
  updateFeaturePriority,
  updateProjectVision,
  updateProjectBackground,
  refreshStaleEntity,
  updateCanvasRole,
} from '@/lib/api'
import type { NextAction } from '@/lib/api'
import type { BRDWorkspaceData, MoSCoWGroup } from '@/types/workspace'
import { ACTION_EXECUTION_MAP } from '@/lib/action-constants'
import { applyConfirmationUpdate, moveFeatureToGroup } from './brd-canvas-utils'

interface EntityActionsDeps {
  projectId: string
  data: BRDWorkspaceData | null
  setData: Dispatch<SetStateAction<BRDWorkspaceData | null>>
  loadData: () => Promise<void>
  closeAllDrawers: () => void
  handleOpenConfidence: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  setVisionDrawer: Dispatch<SetStateAction<boolean>>
  onSendToChat?: (action: NextAction) => void
  pendingAction?: NextAction | null
  onPendingActionConsumed?: () => void
}

export function useBRDEntityActions({
  projectId,
  data,
  setData,
  loadData,
  closeAllDrawers,
  handleOpenConfidence,
  setVisionDrawer,
  onSendToChat,
  pendingAction,
  onPendingActionConsumed,
}: EntityActionsDeps) {
  // Optimistic confirm: update local state immediately, then sync
  const handleConfirm = useCallback(async (entityType: string, entityId: string) => {
    if (!data) return

    setData((prev) => {
      if (!prev) return prev
      return applyConfirmationUpdate(prev, entityType, entityId, 'confirmed_consultant')
    })

    try {
      await batchConfirmEntities(projectId, entityType, [entityId], 'confirmed_consultant')
    } catch (err) {
      console.error('Failed to confirm entity:', err)
      loadData()
    }
  }, [data, projectId, loadData, setData])

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
  }, [data, projectId, loadData, setData])

  const handleConfirmAll = useCallback(async (entityType: string, ids: string[]) => {
    if (!data || ids.length === 0) return

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
      if (result.updated_count < ids.length) {
        console.warn(`Batch confirm: only ${result.updated_count}/${ids.length} updated — reloading`)
        loadData()
      }
    } catch (err) {
      console.error('Failed to batch confirm:', err)
      loadData()
    }
  }, [data, projectId, loadData, setData])

  const handleMovePriority = useCallback(async (featureId: string, targetGroup: MoSCoWGroup) => {
    if (!data) return

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
  }, [data, projectId, loadData, setData])

  const handleUpdateVision = useCallback(async (vision: string) => {
    if (!data) return

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
  }, [data, projectId, loadData, setData])

  const handleUpdateBackground = useCallback(async (background: string) => {
    if (!data) return

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
  }, [data, projectId, loadData, setData])

  const handleRefreshEntity = useCallback(async (entityType: string, entityId: string) => {
    try {
      await refreshStaleEntity(projectId, entityType, entityId)
      loadData()
    } catch (err) {
      console.error('Failed to refresh entity:', err)
    }
  }, [projectId, loadData])

  const handleCanvasRoleUpdate = useCallback(async (personaId: string, role: 'primary' | 'secondary' | null) => {
    if (!data) return

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
      const message = err instanceof Error ? err.message : 'Failed to update canvas role'
      alert(message)
      loadData()
    }
  }, [data, projectId, loadData, setData])

  // Action Execution
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
          feature: 'brd-section-features',
          persona: 'brd-section-personas',
          vp_step: 'brd-section-workflows',
          constraint: 'brd-section-constraints',
          data_entity: 'brd-section-data-entities',
          stakeholder: 'brd-section-stakeholders',
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
        onSendToChat?.(action)
        break

      default:
        if (execType === 'chat') {
          onSendToChat?.(action)
        }
    }
  }, [data, handleConfirmAll, handleOpenConfidence, closeAllDrawers, setVisionDrawer, onSendToChat])

  // Consume pending action from cross-view navigation (Overview -> BRD)
  useEffect(() => {
    if (pendingAction && data) {
      handleActionExecute(pendingAction)
      onPendingActionConsumed?.()
    }
  }, [pendingAction, data, handleActionExecute, onPendingActionConsumed])

  return {
    handleConfirm,
    handleNeedsReview,
    handleConfirmAll,
    handleMovePriority,
    handleUpdateVision,
    handleUpdateBackground,
    handleRefreshEntity,
    handleCanvasRoleUpdate,
    handleActionExecute,
  }
}
