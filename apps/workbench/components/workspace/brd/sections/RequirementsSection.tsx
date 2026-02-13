'use client'

import { DndContext, DragOverlay, PointerSensor, useSensor, useSensors, type DragEndEvent, type DragStartEvent } from '@dnd-kit/core'
import { useState } from 'react'
import { Package } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { KeyFeaturesBar } from '../components/KeyFeaturesBar'
import { PriorityGroup } from './PriorityGroup'
import type { BRDWorkspaceData, FeatureBRDSummary, MoSCoWGroup } from '@/types/workspace'

interface RequirementsSectionProps {
  requirements: BRDWorkspaceData['requirements']
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onMovePriority: (featureId: string, targetGroup: MoSCoWGroup) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}

export function RequirementsSection({
  requirements,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onMovePriority,
  onRefreshEntity,
  onStatusClick,
}: RequirementsSectionProps) {
  const [activeDragFeature, setActiveDragFeature] = useState<FeatureBRDSummary | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  const allFeatures = [
    ...requirements.must_have,
    ...requirements.should_have,
    ...requirements.could_have,
    ...requirements.out_of_scope,
  ]

  const allConfirmed = allFeatures.filter(
    (f) => f.confirmation_status === 'confirmed_consultant' || f.confirmation_status === 'confirmed_client'
  ).length

  const handleDragStart = (event: DragStartEvent) => {
    const { feature } = event.active.data.current || {}
    if (feature) setActiveDragFeature(feature)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    setActiveDragFeature(null)
    const { over, active } = event
    if (!over) return

    const targetGroup = over.data.current?.group as MoSCoWGroup | undefined
    const sourceGroup = active.data.current?.sourceGroup as MoSCoWGroup | undefined
    const feature = active.data.current?.feature as FeatureBRDSummary | undefined

    if (targetGroup && sourceGroup && feature && targetGroup !== sourceGroup) {
      onMovePriority(feature.id, targetGroup)
    }
  }

  // Compute non-out-of-scope features for "Confirm All"
  const confirmableFeatures = [
    ...requirements.must_have,
    ...requirements.should_have,
    ...requirements.could_have,
  ]

  return (
    <section>
      <SectionHeader
        title="Requirements"
        count={allFeatures.length}
        confirmedCount={allConfirmed}
        onConfirmAll={() => onConfirmAll('feature', confirmableFeatures.map((f) => f.id))}
      />

      <KeyFeaturesBar mustHaveFeatures={requirements.must_have} />

      <DndContext
        sensors={sensors}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="space-y-6">
          <PriorityGroup
            group="must_have"
            features={requirements.must_have}
            onConfirm={onConfirm}
            onNeedsReview={onNeedsReview}
            onMove={onMovePriority}
            onRefreshEntity={onRefreshEntity}
            onStatusClick={onStatusClick}
          />
          <PriorityGroup
            group="should_have"
            features={requirements.should_have}
            onConfirm={onConfirm}
            onNeedsReview={onNeedsReview}
            onMove={onMovePriority}
            onRefreshEntity={onRefreshEntity}
            onStatusClick={onStatusClick}
          />
          <PriorityGroup
            group="could_have"
            features={requirements.could_have}
            onConfirm={onConfirm}
            onNeedsReview={onNeedsReview}
            onMove={onMovePriority}
            onRefreshEntity={onRefreshEntity}
            onStatusClick={onStatusClick}
          />
          <PriorityGroup
            group="out_of_scope"
            features={requirements.out_of_scope}
            onConfirm={onConfirm}
            onNeedsReview={onNeedsReview}
            onMove={onMovePriority}
            onRefreshEntity={onRefreshEntity}
            onStatusClick={onStatusClick}
          />
        </div>

        <DragOverlay>
          {activeDragFeature ? (
            <div className="bg-white border border-[#3FAF7A] rounded-2xl shadow-lg px-4 py-3 max-w-md opacity-90">
              <div className="flex items-center gap-2">
                <Package className="w-4 h-4 text-[#3FAF7A]" />
                <span className="text-[14px] font-medium text-[#333333]">{activeDragFeature.name}</span>
              </div>
              {activeDragFeature.description && (
                <p className="text-[12px] text-[#666666] mt-1 truncate">
                  {activeDragFeature.description}
                </p>
              )}
            </div>
          ) : null}
        </DragOverlay>
      </DndContext>
    </section>
  )
}
