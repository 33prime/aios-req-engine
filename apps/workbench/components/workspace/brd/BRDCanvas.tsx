'use client'

import { useState, useEffect, useCallback } from 'react'
import { FileText, RefreshCw } from 'lucide-react'
import { BusinessContextSection } from './sections/BusinessContextSection'
import { ActorsSection } from './sections/ActorsSection'
import { WorkflowsSection } from './sections/WorkflowsSection'
import { RequirementsSection } from './sections/RequirementsSection'
import { ConstraintsSection } from './sections/ConstraintsSection'
import {
  getBRDWorkspaceData,
  updateProjectVision,
  updateFeaturePriority,
  batchConfirmEntities,
} from '@/lib/api'
import type { BRDWorkspaceData, MoSCoWGroup } from '@/types/workspace'

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

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto py-16 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#009b87] mx-auto mb-3" />
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
          className="px-4 py-2 text-sm text-white bg-[#009b87] rounded-md hover:bg-[#008474] transition-colors"
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
              className="h-full bg-[#009b87] rounded-full transition-all duration-300"
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
      </div>

      {/* BRD Sections */}
      <div className="space-y-10">
        <BusinessContextSection
          data={data.business_context}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onUpdateVision={handleUpdateVision}
        />

        <div className="border-t border-[#e9e9e7]" />

        <ActorsSection
          actors={data.actors}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
        />

        <div className="border-t border-[#e9e9e7]" />

        <WorkflowsSection
          workflows={data.workflows}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
        />

        <div className="border-t border-[#e9e9e7]" />

        <RequirementsSection
          requirements={data.requirements}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
          onMovePriority={handleMovePriority}
        />

        <div className="border-t border-[#e9e9e7]" />

        <ConstraintsSection
          constraints={data.constraints}
          onConfirm={handleConfirm}
          onNeedsReview={handleNeedsReview}
          onConfirmAll={handleConfirmAll}
        />
      </div>
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
    data.constraints.length
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
    data.constraints.filter((c) => isConfirmed(c.confirmation_status)).length
  )
}
