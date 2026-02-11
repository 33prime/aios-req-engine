'use client'

import { useState } from 'react'
import { Database, Plus, Trash2, ChevronRight, Link2, Layers } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import { StaleIndicator } from '../components/StaleIndicator'
import type { DataEntityBRDSummary } from '@/types/workspace'

interface DataEntitiesSectionProps {
  dataEntities: DataEntityBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onCreateEntity: () => void
  onDeleteEntity: (entityId: string, entityName: string) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}

const CATEGORY_CONFIG: Record<string, { label: string; icon: string }> = {
  domain: { label: 'Domain', icon: '◆' },
  reference: { label: 'Reference', icon: '◇' },
  transactional: { label: 'Transactional', icon: '⟡' },
  system: { label: 'System', icon: '⚙' },
}

function DataEntityAccordionCard({
  entity,
  onConfirm,
  onNeedsReview,
  onDeleteEntity,
  onRefreshEntity,
  onStatusClick,
}: {
  entity: DataEntityBRDSummary
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onDeleteEntity: (entityId: string, entityName: string) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const cat = CATEGORY_CONFIG[entity.entity_category] || CATEGORY_CONFIG.domain

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden group/card">
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <Database className="w-4 h-4 text-[#3FAF7A] shrink-0" />
        <span className="text-[14px] font-semibold text-[#333333] truncate">{entity.name}</span>
        <span className="text-[12px] text-[#999999] shrink-0 bg-[#F0F0F0] px-2 py-0.5 rounded-full">
          {cat.label}
        </span>
        {entity.field_count > 0 && (
          <span className="text-[12px] text-[#999999] shrink-0 flex items-center gap-1">
            <Layers className="w-3 h-3" />
            {entity.field_count} {entity.field_count === 1 ? 'field' : 'fields'}
          </span>
        )}
        {entity.workflow_step_count > 0 && (
          <span className="text-[12px] text-[#999999] shrink-0 flex items-center gap-1">
            <Link2 className="w-3 h-3" />
            {entity.workflow_step_count} {entity.workflow_step_count === 1 ? 'link' : 'links'}
          </span>
        )}
        <span onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge
            status={entity.confirmation_status}
            onClick={onStatusClick ? () => onStatusClick('data_entity', entity.id, entity.name, entity.confirmation_status) : undefined}
          />
        </span>
        {entity.is_stale && (
          <span className="ml-auto shrink-0">
            <StaleIndicator reason={entity.stale_reason || undefined} onRefresh={onRefreshEntity ? () => onRefreshEntity('data_entity', entity.id) : undefined} />
          </span>
        )}
      </button>

      {/* Expanded body */}
      <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-5 pb-5 pt-1">
          {/* Description */}
          {entity.description && (
            <p className="text-[13px] text-[#666666] leading-relaxed mb-4">{entity.description}</p>
          )}

          {/* Entity details */}
          <div className="flex gap-6">
            {/* Left: Category & Fields info */}
            <div className="flex-1 min-w-0">
              <div className="px-3 py-1.5 rounded-lg mb-3 bg-[#E8F5E9] text-[#25785A]">
                <span className="text-[11px] font-semibold uppercase tracking-wider">Entity Details</span>
              </div>
              <ul className="space-y-2">
                <li className="flex items-start gap-2 text-[13px] text-[#666666]">
                  <span className="text-[#3FAF7A] mt-0.5 shrink-0">&#8226;</span>
                  <span>Category: <span className="font-medium text-[#333333]">{cat.label}</span></span>
                </li>
                <li className="flex items-start gap-2 text-[13px] text-[#666666]">
                  <span className="text-[#3FAF7A] mt-0.5 shrink-0">&#8226;</span>
                  <span>{entity.field_count} {entity.field_count === 1 ? 'field' : 'fields'} defined</span>
                </li>
                {entity.workflow_step_count > 0 && (
                  <li className="flex items-start gap-2 text-[13px] text-[#666666]">
                    <span className="text-[#3FAF7A] mt-0.5 shrink-0">&#8226;</span>
                    <span>Linked to {entity.workflow_step_count} workflow {entity.workflow_step_count === 1 ? 'step' : 'steps'}</span>
                  </li>
                )}
              </ul>
            </div>

            {/* Right: Evidence summary */}
            {entity.evidence && entity.evidence.length > 0 && (
              <div className="flex-1 min-w-0">
                <div className="px-3 py-1.5 rounded-lg mb-3 bg-[#F0F0F0] text-[#666666]">
                  <span className="text-[11px] font-semibold uppercase tracking-wider">Evidence</span>
                </div>
                <ul className="space-y-2">
                  {entity.evidence.slice(0, 3).map((ev, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                      <span className="text-[#999999] mt-0.5 shrink-0">&#8226;</span>
                      <span className="line-clamp-2">{ev.rationale || ev.excerpt || 'Source evidence'}</span>
                    </li>
                  ))}
                  {entity.evidence.length > 3 && (
                    <li className="text-[12px] text-[#999999] ml-4">
                      +{entity.evidence.length - 3} more
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>

          {/* Actions row */}
          <div className="mt-4 pt-3 border-t border-[#E5E5E5] flex items-center justify-between">
            <ConfirmActions
              status={entity.confirmation_status}
              onConfirm={() => onConfirm('data_entity', entity.id)}
              onNeedsReview={() => onNeedsReview('data_entity', entity.id)}
            />
            <button
              onClick={() => onDeleteEntity(entity.id, entity.name)}
              className="p-1.5 rounded-md text-[#999999] hover:text-red-500 hover:bg-red-50 transition-colors"
              title="Delete data entity"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function DataEntitiesSection({
  dataEntities,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onCreateEntity,
  onDeleteEntity,
  onRefreshEntity,
  onStatusClick,
}: DataEntitiesSectionProps) {
  const confirmedCount = dataEntities.filter(
    (e) => e.confirmation_status === 'confirmed_consultant' || e.confirmation_status === 'confirmed_client'
  ).length

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader
          title="Data Entities"
          count={dataEntities.length}
          confirmedCount={confirmedCount}
          onConfirmAll={() => onConfirmAll('data_entity', dataEntities.map((e) => e.id))}
        />
        <button
          onClick={onCreateEntity}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-[#E8F5E9] hover:text-[#25785A] hover:border-[#3FAF7A] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Data Entity
        </button>
      </div>
      {dataEntities.length === 0 ? (
        <p className="text-[13px] text-[#999999] italic">No data entities identified yet</p>
      ) : (
        <div className="space-y-3">
          {dataEntities.map((entity) => (
            <DataEntityAccordionCard
              key={entity.id}
              entity={entity}
              onConfirm={onConfirm}
              onNeedsReview={onNeedsReview}
              onDeleteEntity={onDeleteEntity}
              onRefreshEntity={onRefreshEntity}
              onStatusClick={onStatusClick}
            />
          ))}
        </div>
      )}
    </section>
  )
}
