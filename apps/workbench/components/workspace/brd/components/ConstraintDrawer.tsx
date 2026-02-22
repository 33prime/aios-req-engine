'use client'

import { useState } from 'react'
import {
  DollarSign,
  Clock,
  Scale,
  Building2,
  Server,
  Target,
  FileText,
  Puzzle,
  Link2,
} from 'lucide-react'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { EmptyState } from '@/components/ui/EmptyState'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import type { ConstraintItem, FeatureBRDSummary } from '@/types/workspace'

type TabId = 'detail' | 'evidence'

interface ConstraintDrawerProps {
  constraint: ConstraintItem
  projectId: string
  features?: FeatureBRDSummary[]
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

const BASE_TABS: { id: TabId; label: string; icon: typeof FileText }[] = [
  { id: 'detail', label: 'Detail', icon: FileText },
  { id: 'evidence', label: 'Evidence', icon: Link2 },
]

const CONSTRAINT_TYPE_ICONS: Record<string, typeof DollarSign> = {
  budget: DollarSign,
  timeline: Clock,
  regulatory: Scale,
  organizational: Building2,
  technical: Server,
  strategic: Target,
}

const SEVERITY_STYLES: Record<string, string> = {
  critical: 'bg-[#0A1E2F] text-white',
  high: 'bg-[#25785A] text-white',
  medium: 'bg-[#E8F5E9] text-[#25785A]',
  low: 'bg-[#F0F0F0] text-[#666666]',
}

const SOURCE_LABELS: Record<string, string> = {
  extracted: 'Extracted',
  manual: 'Manual',
  ai_inferred: 'AI Inferred',
}

export function ConstraintDrawer({
  constraint,
  projectId,
  features,
  onClose,
  onConfirm,
  onNeedsReview,
}: ConstraintDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('detail')

  const TypeIcon = CONSTRAINT_TYPE_ICONS[constraint.constraint_type] || Target
  const severityStyle = SEVERITY_STYLES[constraint.severity] || SEVERITY_STYLES.low
  const evidenceCount = constraint.evidence?.length || 0

  // Resolve linked features
  const linkedFeatures = (constraint.linked_feature_ids || [])
    .map((fid) => (features || []).find((f) => f.id === fid))
    .filter(Boolean) as FeatureBRDSummary[]

  const linkedStepCount = constraint.linked_vp_step_ids?.length || 0
  const linkedDataEntityCount = constraint.linked_data_entity_ids?.length || 0

  // Build tabs with dynamic evidence badge
  const tabs: DrawerTab[] = BASE_TABS.map((tab) => ({
    ...tab,
    badge:
      tab.id === 'evidence' && evidenceCount > 0 ? (
        <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
          {evidenceCount}
        </span>
      ) : undefined,
  }))

  const entityLabel =
    constraint.constraint_type.charAt(0).toUpperCase() +
    constraint.constraint_type.slice(1)

  return (
    <DrawerShell
      onClose={onClose}
      icon={TypeIcon}
      entityLabel={entityLabel}
      title={constraint.title}
      headerExtra={
        <div className="flex items-center gap-2 mt-1.5">
          <span
            className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${severityStyle}`}
          >
            {constraint.severity.charAt(0).toUpperCase() +
              constraint.severity.slice(1)}
          </span>
          {constraint.source && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
              {SOURCE_LABELS[constraint.source] || constraint.source}
            </span>
          )}
        </div>
      }
      headerRight={<BRDStatusBadge status={constraint.confirmation_status} />}
      headerActions={
        <ConfirmActions
          status={constraint.confirmation_status}
          onConfirm={() => onConfirm('constraint', constraint.id)}
          onNeedsReview={() => onNeedsReview('constraint', constraint.id)}
          size="md"
        />
      }
      tabs={tabs}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {activeTab === 'detail' && (
        <DetailTab
          constraint={constraint}
          linkedFeatures={linkedFeatures}
          linkedStepCount={linkedStepCount}
          linkedDataEntityCount={linkedDataEntityCount}
        />
      )}
      {activeTab === 'evidence' && (
        <EvidenceTab evidence={constraint.evidence || []} />
      )}
    </DrawerShell>
  )
}

// ============================================================================
// Detail Tab
// ============================================================================

function DetailTab({
  constraint,
  linkedFeatures,
  linkedStepCount,
  linkedDataEntityCount,
}: {
  constraint: ConstraintItem
  linkedFeatures: FeatureBRDSummary[]
  linkedStepCount: number
  linkedDataEntityCount: number
}) {
  const hasLinks =
    linkedFeatures.length > 0 || linkedStepCount > 0 || linkedDataEntityCount > 0

  return (
    <div className="space-y-6">
      {/* Description */}
      {constraint.description && (
        <div className="border border-[#E5E5E5] rounded-xl px-4 py-3">
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">
            Description
          </h4>
          <p className="text-[13px] text-[#333333] leading-relaxed">
            {constraint.description}
          </p>
        </div>
      )}

      {/* Impact description */}
      {constraint.impact_description && (
        <div className="border border-[#E5E5E5] rounded-xl px-4 py-3">
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2">
            Impact
          </h4>
          <p className="text-[13px] text-[#333333] leading-relaxed">
            {constraint.impact_description}
          </p>
        </div>
      )}

      {/* Severity + Confidence */}
      <div className="border border-[#E5E5E5] rounded-xl px-4 py-3">
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-3">
          Assessment
        </h4>
        <div className="space-y-3">
          {/* Severity */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[12px] text-[#666666]">Severity</span>
              <span
                className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                  SEVERITY_STYLES[constraint.severity] || SEVERITY_STYLES.low
                }`}
              >
                {constraint.severity.charAt(0).toUpperCase() +
                  constraint.severity.slice(1)}
              </span>
            </div>
          </div>

          {/* Confidence meter */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[12px] text-[#666666]">Confidence</span>
              <span className="text-[12px] font-medium text-[#333333]">
                {constraint.confidence != null
                  ? `${Math.round(constraint.confidence * 100)}%`
                  : 'N/A'}
              </span>
            </div>
            {constraint.confidence != null && (
              <div className="h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#3FAF7A] rounded-full transition-all"
                  style={{ width: `${Math.round(constraint.confidence * 100)}%` }}
                />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Linked Entities */}
      {hasLinks && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Link2 className="w-3.5 h-3.5" />
            Linked Entities
          </h4>
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
            {/* Linked features */}
            {linkedFeatures.length > 0 && (
              <>
                <div className="px-3 py-1.5 bg-[#F4F4F4] border-b border-[#E5E5E5]">
                  <div className="flex items-center gap-1.5">
                    <Puzzle className="w-3 h-3 text-[#666666]" />
                    <span className="text-[10px] font-medium text-[#666666] uppercase">
                      Features ({linkedFeatures.length})
                    </span>
                  </div>
                </div>
                {linkedFeatures.map((f) => (
                  <div
                    key={f.id}
                    className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0 flex items-center gap-2"
                  >
                    <Puzzle className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
                    <span className="text-[13px] text-[#333333] font-medium truncate">
                      {f.name}
                    </span>
                    {f.priority_group && (
                      <span className="text-[10px] text-[#999999] bg-[#F0F0F0] px-1.5 py-0.5 rounded flex-shrink-0">
                        {f.priority_group.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                ))}
              </>
            )}

            {/* Linked workflow steps */}
            {linkedStepCount > 0 && (
              <div className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0 flex items-center gap-2 bg-white">
                <Clock className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
                <span className="text-[13px] text-[#333333]">
                  {linkedStepCount} workflow step{linkedStepCount !== 1 ? 's' : ''}
                </span>
              </div>
            )}

            {/* Linked data entities */}
            {linkedDataEntityCount > 0 && (
              <div className="px-3 py-2.5 border-b border-[#F0F0F0] last:border-0 flex items-center gap-2 bg-white">
                <Server className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
                <span className="text-[13px] text-[#333333]">
                  {linkedDataEntityCount} data entit{linkedDataEntityCount !== 1 ? 'ies' : 'y'}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Empty links state */}
      {!hasLinks && (
        <EmptyState
          icon={<Link2 className="w-8 h-8 text-[#E5E5E5]" />}
          title="No linked entities"
          description="Process more signals to discover connections."
        />
      )}
    </div>
  )
}

// ============================================================================
// Evidence Tab
// ============================================================================

function EvidenceTab({ evidence }: { evidence: ConstraintItem['evidence'] }) {
  const items = evidence || []

  if (items.length === 0) {
    return (
      <EmptyState
        icon={<FileText className="w-8 h-8 text-[#E5E5E5]" />}
        title="No evidence available"
        description="Evidence will appear here as signals are processed."
      />
    )
  }

  return (
    <div>
      <EvidenceBlock evidence={items} maxItems={100} />
    </div>
  )
}
