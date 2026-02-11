'use client'

import { useState } from 'react'
import { useDroppable, useDraggable } from '@dnd-kit/core'
import { GripVertical, ChevronRight, Package } from 'lucide-react'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import { StaleIndicator } from '../components/StaleIndicator'
import type { FeatureBRDSummary, MoSCoWGroup } from '@/types/workspace'

// Brand-appropriate priority colors — green intensity scale + neutrals
const GROUP_CONFIG: Record<MoSCoWGroup, {
  label: string
  dotColor: string
  headerBg: string
  headerText: string
  accentColor: string
  bgActive: string
}> = {
  must_have: {
    label: 'Must Have',
    dotColor: '#3FAF7A',
    headerBg: 'bg-[#3FAF7A]',
    headerText: 'text-white',
    accentColor: '#3FAF7A',
    bgActive: 'border-[#3FAF7A] bg-[#E8F5E9]/50',
  },
  should_have: {
    label: 'Should Have',
    dotColor: '#25785A',
    headerBg: 'bg-[#E8F5E9]',
    headerText: 'text-[#25785A]',
    accentColor: '#25785A',
    bgActive: 'border-[#25785A] bg-[#E8F5E9]/50',
  },
  could_have: {
    label: 'Could Have',
    dotColor: '#94A3B8',
    headerBg: 'bg-[#F0F4F8]',
    headerText: 'text-[#475569]',
    accentColor: '#64748B',
    bgActive: 'border-[#94A3B8] bg-[#F0F4F8]/50',
  },
  out_of_scope: {
    label: 'Out of Scope',
    dotColor: '#999999',
    headerBg: 'bg-[#F0F0F0]',
    headerText: 'text-[#999999]',
    accentColor: '#999999',
    bgActive: 'border-[#999999] bg-[#F0F0F0]/50',
  },
}

const MOVE_TARGETS: MoSCoWGroup[] = ['must_have', 'should_have', 'could_have', 'out_of_scope']

function FeatureAccordionCard({
  feature,
  group,
  onConfirm,
  onNeedsReview,
  onMove,
  onRefresh,
  onStatusClick,
}: {
  feature: FeatureBRDSummary
  group: MoSCoWGroup
  onConfirm: () => void
  onNeedsReview: () => void
  onMove: (featureId: string, targetGroup: MoSCoWGroup) => void
  onRefresh?: () => void
  onStatusClick?: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `feature-${feature.id}`,
    data: { feature, sourceGroup: group },
  })

  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`, opacity: isDragging ? 0.5 : 1 }
    : undefined

  const moveTargets = MOVE_TARGETS.filter((t) => t !== group)
  const config = GROUP_CONFIG[group]

  return (
    <div ref={setNodeRef} style={style}>
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
        {/* Header row */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
        >
          {/* Drag handle */}
          <div
            {...listeners}
            {...attributes}
            onClick={(e) => e.stopPropagation()}
            className="cursor-grab active:cursor-grabbing text-[#999999] hover:text-[#666666] -ml-1 shrink-0"
          >
            <GripVertical className="w-4 h-4" />
          </div>
          <ChevronRight
            className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
          />
          <Package className="w-4 h-4 shrink-0" style={{ color: config.accentColor }} />
          <span className="text-[14px] font-semibold text-[#333333] truncate">{feature.name}</span>
          {feature.category && (
            <span className="text-[12px] text-[#999999] shrink-0">({feature.category})</span>
          )}
          <span className="ml-auto shrink-0" onClick={(e) => e.stopPropagation()}>
            <BRDStatusBadge
              status={feature.confirmation_status}
              onClick={onStatusClick}
            />
          </span>
          {feature.is_stale && (
            <span className="shrink-0">
              <StaleIndicator reason={feature.stale_reason || undefined} onRefresh={onRefresh} />
            </span>
          )}
        </button>

        {/* Expanded body */}
        <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
          <div className="px-5 pb-5 pt-1">
            {/* Description */}
            {feature.description && (
              <p className="text-[13px] text-[#666666] leading-relaxed mb-4">{feature.description}</p>
            )}

            {/* Evidence */}
            {feature.evidence && feature.evidence.length > 0 && (
              <div className="mb-4">
                <div className="px-3 py-1.5 rounded-lg mb-3 bg-[#F0F0F0] text-[#666666]">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Evidence</span>
                </div>
                <ul className="space-y-2">
                  {feature.evidence.slice(0, 3).map((ev, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                      <span className="text-[#999999] mt-0.5 shrink-0">&#8226;</span>
                      <span className="line-clamp-2">{ev.rationale || ev.excerpt || 'Source evidence'}</span>
                    </li>
                  ))}
                  {feature.evidence.length > 3 && (
                    <li className="text-[12px] text-[#999999] ml-4">
                      +{feature.evidence.length - 3} more
                    </li>
                  )}
                </ul>
              </div>
            )}

            {/* Actions */}
            <div className="mt-4 pt-3 border-t border-[#E5E5E5] flex items-center justify-between">
              <ConfirmActions
                status={feature.confirmation_status}
                onConfirm={onConfirm}
                onNeedsReview={onNeedsReview}
              />
              <span onClick={(e) => e.stopPropagation()}>
                <select
                  value=""
                  onChange={(e) => {
                    if (e.target.value) onMove(feature.id, e.target.value as MoSCoWGroup)
                  }}
                  className="text-[11px] text-[#999999] bg-transparent border border-[#E5E5E5] rounded-md px-2 py-1 hover:text-[#666666] hover:border-[#999999] focus:outline-none focus:ring-1 focus:ring-[#3FAF7A] cursor-pointer"
                >
                  <option value="">Move to...</option>
                  {moveTargets.map((t) => (
                    <option key={t} value={t}>{GROUP_CONFIG[t].label}</option>
                  ))}
                </select>
              </span>
            </div>
          </div>
        </div>
      </div>
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
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}

export function PriorityGroup({ group, features, onConfirm, onNeedsReview, onMove, onRefreshEntity, onStatusClick }: PriorityGroupProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: `priority-group-${group}`,
    data: { group },
  })

  const config = GROUP_CONFIG[group]

  return (
    <div
      ref={setNodeRef}
      className={`rounded-xl border-2 border-dashed transition-colors duration-150 p-1 ${
        isOver ? config.bgActive : 'border-transparent'
      }`}
    >
      {/* Group header */}
      <div className="flex items-center gap-2.5 mb-3">
        <div
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg ${config.headerBg} ${config.headerText}`}
        >
          <span className="text-[12px] font-bold uppercase tracking-wider">{config.label}</span>
          <span className="text-[12px] font-medium opacity-75">({features.length})</span>
        </div>
      </div>

      {features.length === 0 ? (
        <div className="py-6 text-center text-[13px] text-[#999999] italic border border-dashed border-[#E5E5E5] rounded-xl bg-white/50">
          {isOver ? 'Drop here' : 'No features'}
        </div>
      ) : (
        <div className="space-y-3">
          {features.map((feature) => (
            <FeatureAccordionCard
              key={feature.id}
              feature={feature}
              group={group}
              onConfirm={() => onConfirm('feature', feature.id)}
              onNeedsReview={() => onNeedsReview('feature', feature.id)}
              onMove={onMove}
              onRefresh={onRefreshEntity ? () => onRefreshEntity('feature', feature.id) : undefined}
              onStatusClick={onStatusClick ? () => onStatusClick('feature', feature.id, feature.name, feature.confirmation_status) : undefined}
            />
          ))}
        </div>
      )}
    </div>
  )
}
