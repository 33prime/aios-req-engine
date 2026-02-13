'use client'

import { useMemo, useState } from 'react'
import { Database, Plus, Trash2, LayoutGrid, GitBranch } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import { StaleIndicator } from '../components/StaleIndicator'
import { DataEntityERD } from '../components/DataEntityERD'
import type { DataEntityBRDSummary, DataEntityField } from '@/types/workspace'

interface DataEntitiesSectionProps {
  projectId: string
  dataEntities: DataEntityBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onCreateEntity: () => void
  onDeleteEntity: (entityId: string, entityName: string) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}

/** Group fields by their `group` property. Ungrouped fields go under null key. */
function groupFields(fields: DataEntityField[]): Map<string | null, DataEntityField[]> {
  const groups = new Map<string | null, DataEntityField[]>()
  for (const f of fields) {
    const key = f.group || null
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(f)
  }
  return groups
}

function DataEntityCard({
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
  const fieldGroups = useMemo(() => groupFields(entity.fields || []), [entity.fields])
  const hasGroups = fieldGroups.size > 1 || (fieldGroups.size === 1 && !fieldGroups.has(null))

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden group/card">
      {/* Card content — always visible */}
      <div className="px-6 py-5">
        {/* Title row */}
        <div className="flex items-start gap-3 mb-1">
          <div className="flex-1 min-w-0">
            <h4 className="text-[15px] font-bold text-[#333333]">
              {entity.name}
            </h4>
          </div>
          <span className="shrink-0" onClick={(e) => e.stopPropagation()}>
            <BRDStatusBadge
              status={entity.confirmation_status}
              onClick={onStatusClick ? () => onStatusClick('data_entity', entity.id, entity.name, entity.confirmation_status) : undefined}
            />
          </span>
          {entity.is_stale && (
            <span className="shrink-0">
              <StaleIndicator reason={entity.stale_reason || undefined} onRefresh={onRefreshEntity ? () => onRefreshEntity('data_entity', entity.id) : undefined} />
            </span>
          )}
        </div>

        {/* Fields display */}
        {entity.fields && entity.fields.length > 0 ? (
          hasGroups ? (
            // Grouped fields — each group on its own line
            <div className="mt-3 space-y-1.5">
              {Array.from(fieldGroups.entries()).map(([group, fields]) => (
                <p key={group || '_ungrouped'} className="text-[13px] text-[#666666] leading-relaxed">
                  {group && (
                    <span className="font-semibold text-[#333333]">{group}: </span>
                  )}
                  {fields.map(f => f.name).join(', ')}
                </p>
              ))}
            </div>
          ) : (
            // Flat field list — comma-separated
            <p className="mt-2 text-[13px] text-[#666666] leading-relaxed">
              {entity.fields.map(f => f.name).join(', ')}
            </p>
          )
        ) : entity.description ? (
          <p className="mt-2 text-[13px] text-[#666666] leading-relaxed">{entity.description}</p>
        ) : null}

        {/* Workflow links note */}
        {entity.workflow_step_count > 0 && (
          <p className="mt-2 text-[12px] text-[#999999]">
            Linked to {entity.workflow_step_count} workflow {entity.workflow_step_count === 1 ? 'step' : 'steps'}
          </p>
        )}

        {/* Actions row */}
        <div className="mt-4 pt-3 border-t border-[#E5E5E5] flex items-center justify-between">
          <ConfirmActions
            status={entity.confirmation_status}
            onConfirm={() => onConfirm('data_entity', entity.id)}
            onNeedsReview={() => onNeedsReview('data_entity', entity.id)}
          />
          <button
            onClick={() => onDeleteEntity(entity.id, entity.name)}
            className="p-1.5 rounded-md text-[#999999] hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover/card:opacity-100"
            title="Delete data entity"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}

type ViewMode = 'cards' | 'diagram'

export function DataEntitiesSection({
  projectId,
  dataEntities,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onCreateEntity,
  onDeleteEntity,
  onRefreshEntity,
  onStatusClick,
}: DataEntitiesSectionProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('cards')

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
        <div className="flex items-center gap-2">
          {/* Cards/Diagram toggle */}
          {dataEntities.length > 0 && (
            <div className="flex rounded-lg border border-[#E5E5E5] overflow-hidden">
              <button
                onClick={() => setViewMode('cards')}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                  viewMode === 'cards'
                    ? 'bg-[#E8F5E9] text-[#25785A]'
                    : 'bg-white text-[#666666] hover:bg-gray-50'
                }`}
              >
                <LayoutGrid className="w-3 h-3" />
                Cards
              </button>
              <button
                onClick={() => setViewMode('diagram')}
                className={`inline-flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-medium transition-colors ${
                  viewMode === 'diagram'
                    ? 'bg-[#E8F5E9] text-[#25785A]'
                    : 'bg-white text-[#666666] hover:bg-gray-50'
                }`}
              >
                <GitBranch className="w-3 h-3" />
                Diagram
              </button>
            </div>
          )}
          <button
            onClick={onCreateEntity}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-[#E8F5E9] hover:text-[#25785A] hover:border-[#3FAF7A] transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Data Entity
          </button>
        </div>
      </div>

      {dataEntities.length === 0 ? (
        <p className="text-[13px] text-[#999999] italic">No data entities identified yet</p>
      ) : viewMode === 'diagram' ? (
        <DataEntityERD projectId={projectId} />
      ) : (
        <div className="space-y-3">
          {dataEntities.map((entity) => (
            <DataEntityCard
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
