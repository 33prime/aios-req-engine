'use client'

import { Database, Plus, Trash2 } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { CollapsibleCard } from '../components/CollapsibleCard'
import { EvidenceBlock } from '../components/EvidenceBlock'
import type { DataEntityBRDSummary } from '@/types/workspace'

interface DataEntitiesSectionProps {
  dataEntities: DataEntityBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onCreateEntity: () => void
  onDeleteEntity: (entityId: string) => void
}

const CATEGORY_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  domain: { bg: 'bg-teal-50', text: 'text-teal-700', label: 'Domain' },
  reference: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Reference' },
  transactional: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'Transactional' },
  system: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'System' },
}

export function DataEntitiesSection({
  dataEntities,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onCreateEntity,
  onDeleteEntity,
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
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-teal-50 hover:text-teal-700 hover:border-teal-200 transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Data Entity
        </button>
      </div>
      {dataEntities.length === 0 ? (
        <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No data entities identified yet</p>
      ) : (
        <div className="space-y-2">
          {dataEntities.map((entity) => {
            const cat = CATEGORY_CONFIG[entity.entity_category] || CATEGORY_CONFIG.domain
            return (
              <CollapsibleCard
                key={entity.id}
                title={entity.name}
                subtitle={entity.description || undefined}
                icon={<Database className="w-4 h-4 text-teal-500" />}
                status={entity.confirmation_status}
                onConfirm={() => onConfirm('data_entity', entity.id)}
                onNeedsReview={() => onNeedsReview('data_entity', entity.id)}
                actions={
                  <button
                    onClick={() => onDeleteEntity(entity.id)}
                    className="p-1 rounded text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors opacity-0 group-hover/card:opacity-100"
                    title="Delete data entity"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                }
              >
                <div className="space-y-2 text-[13px] text-[rgba(55,53,47,0.65)]">
                  {entity.description && (
                    <p className="leading-relaxed">{entity.description}</p>
                  )}
                  <div className="flex items-center gap-3 text-[12px]">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${cat.bg} ${cat.text}`}>
                      {cat.label}
                    </span>
                    {entity.field_count > 0 && (
                      <span>
                        <span className="font-medium text-[#37352f]">{entity.field_count}</span>{' '}
                        {entity.field_count === 1 ? 'field' : 'fields'}
                      </span>
                    )}
                    {entity.workflow_step_count > 0 && (
                      <span>
                        <span className="font-medium text-[#37352f]">{entity.workflow_step_count}</span>{' '}
                        workflow {entity.workflow_step_count === 1 ? 'link' : 'links'}
                      </span>
                    )}
                  </div>
                </div>
                <EvidenceBlock evidence={entity.evidence || []} />
              </CollapsibleCard>
            )
          })}
        </div>
      )}
    </section>
  )
}
