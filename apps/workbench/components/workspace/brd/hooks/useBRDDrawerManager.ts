import { useState, useCallback } from 'react'
import type {
  BRDWorkspaceData,
} from '@/types/workspace'

/**
 * Drawer manager — drawers have been removed from BRD.
 * Entity detail is now inline on cards; deep-dive is via chat assistant.
 *
 * This hook is kept as a thin shim so callers (useBRDEntityActions,
 * BRDCanvas) don't need sweeping signature changes.
 */
export function useBRDDrawerManager(_data: BRDWorkspaceData | null) {
  // Impact Preview modal is NOT a drawer — keep it
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

  // No-op: drawers removed — entity clicks do nothing now
  const closeAllDrawers = useCallback(() => {}, [])

  const handleOpenConfidence = useCallback(
    (_entityType: string, _entityId: string, _entityName: string, _status?: string | null) => {
      // Drawers removed. Entity detail available via chat assistant.
    },
    [],
  )

  const handleViewStepDetail = useCallback((_stepId: string) => {}, [])
  const handleViewWorkflowDetail = useCallback((_workflowId: string) => {}, [])
  const handleOpenDataEntityDetail = useCallback((_entityId: string) => {}, [])

  return {
    // Impact Preview (modal, not drawer — kept)
    impactPreview,
    setImpactPreview,
    // No-op shims for callers
    showImpactPreview,
    closeAllDrawers,
    handleOpenConfidence,
    handleViewStepDetail,
    handleViewWorkflowDetail,
    handleOpenDataEntityDetail,
  }
}
