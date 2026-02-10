'use client'

import { useDroppable } from '@dnd-kit/core'
import { GripVertical } from 'lucide-react'
import { useDraggable } from '@dnd-kit/core'
import { CollapsibleCard } from '../components/CollapsibleCard'
import { EvidenceBlock } from '../components/EvidenceBlock'
import type { FeatureBRDSummary, MoSCoWGroup } from '@/types/workspace'

const GROUP_CONFIG: Record<MoSCoWGroup, { label: string; color: string; bgActive: string }> = {
  must_have: { label: 'Must Have', color: '#dc2626', bgActive: 'border-red-300 bg-red-50/50' },
  should_have: { label: 'Should Have', color: '#d97706', bgActive: 'border-amber-300 bg-amber-50/50' },
  could_have: { label: 'Could Have', color: '#2563eb', bgActive: 'border-blue-300 bg-blue-50/50' },
  out_of_scope: { label: 'Out of Scope', color: '#6b7280', bgActive: 'border-gray-300 bg-gray-50/50' },
}

const MOVE_TARGETS: MoSCoWGroup[] = ['must_have', 'should_have', 'could_have', 'out_of_scope']

// Draggable feature card wrapper
function DraggableFeatureCard({
  feature,
  group,
  onConfirm,
  onNeedsReview,
  onMove,
  onRefresh,
}: {
  feature: FeatureBRDSummary
  group: MoSCoWGroup
  onConfirm: () => void
  onNeedsReview: () => void
  onMove: (featureId: string, targetGroup: MoSCoWGroup) => void
  onRefresh?: () => void
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `feature-${feature.id}`,
    data: { feature, sourceGroup: group },
  })

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, opacity: isDragging ? 0.5 : 1 }
    : undefined

  const moveTargets = MOVE_TARGETS.filter((t) => t !== group)

  return (
    <div ref={setNodeRef} style={style}>
      <CollapsibleCard
        title={feature.name}
        subtitle={feature.category || undefined}
        status={feature.confirmation_status}
        isStale={feature.is_stale}
        staleReason={feature.stale_reason}
        onRefresh={onRefresh}
        onConfirm={onConfirm}
        onNeedsReview={onNeedsReview}
        dragHandle={
          <div
            {...listeners}
            {...attributes}
            className="cursor-grab active:cursor-grabbing text-gray-300 hover:text-gray-500 -ml-1"
          >
            <GripVertical className="w-4 h-4" />
          </div>
        }
        actions={
          <select
            value=""
            onChange={(e) => {
              if (e.target.value) onMove(feature.id, e.target.value as MoSCoWGroup)
            }}
            className="text-[11px] text-gray-400 bg-transparent border border-gray-200 rounded px-1.5 py-0.5 hover:text-gray-600 hover:border-gray-300 focus:outline-none focus:ring-1 focus:ring-teal-200 cursor-pointer"
          >
            <option value="">Move to...</option>
            {moveTargets.map((t) => (
              <option key={t} value={t}>{GROUP_CONFIG[t].label}</option>
            ))}
          </select>
        }
      >
        {feature.description && (
          <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed">
            {feature.description}
          </p>
        )}
        <EvidenceBlock evidence={feature.evidence || []} />
      </CollapsibleCard>
    </div>
  )
}

interface PriorityGroupProps {
  group: MoSCoWGroup
  features: FeatureBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onMove: (featureId: string, targetGroup: MoSCoWGroup) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
}

export function PriorityGroup({ group, features, onConfirm, onNeedsReview, onMove, onRefreshEntity }: PriorityGroupProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `priority-group-${group}`,
    data: { group },
  })

  const config = GROUP_CONFIG[group]

  return (
    <div
      ref={setNodeRef}
      className={`rounded-md border-2 border-dashed transition-colors duration-150 ${
        isOver ? config.bgActive : 'border-transparent'
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: config.color }} />
        <h3 className="text-[14px] font-semibold text-[#37352f]">{config.label}</h3>
        <span className="text-[12px] text-[rgba(55,53,47,0.45)]">({features.length})</span>
      </div>

      {features.length === 0 ? (
        <div className="py-4 text-center text-[13px] text-[rgba(55,53,47,0.35)] italic border border-dashed border-gray-200 rounded-[3px]">
          {isOver ? 'Drop here' : 'No features'}
        </div>
      ) : (
        <div className="space-y-2">
          {features.map((feature) => (
            <DraggableFeatureCard
              key={feature.id}
              feature={feature}
              group={group}
              onConfirm={() => onConfirm('feature', feature.id)}
              onNeedsReview={() => onNeedsReview('feature', feature.id)}
              onMove={onMove}
              onRefresh={onRefreshEntity ? () => onRefreshEntity('feature', feature.id) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  )
}
