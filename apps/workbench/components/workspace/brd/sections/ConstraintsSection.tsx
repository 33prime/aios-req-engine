'use client'

import { Shield } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { CollapsibleCard } from '../components/CollapsibleCard'
import { EvidenceBlock } from '../components/EvidenceBlock'
import type { ConstraintItem } from '@/types/workspace'

interface ConstraintsSectionProps {
  constraints: ConstraintItem[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-500',
  high: 'text-orange-500',
  medium: 'text-yellow-600',
  low: 'text-gray-500',
}

export function ConstraintsSection({ constraints, onConfirm, onNeedsReview, onConfirmAll, onStatusClick }: ConstraintsSectionProps) {
  const confirmedCount = constraints.filter(
    (c) => c.confirmation_status === 'confirmed_consultant' || c.confirmation_status === 'confirmed_client'
  ).length

  return (
    <section>
      <SectionHeader
        title="Constraints"
        count={constraints.length}
        confirmedCount={confirmedCount}
        onConfirmAll={() => onConfirmAll('constraint', constraints.map((c) => c.id))}
      />
      {constraints.length === 0 ? (
        <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No constraints identified yet</p>
      ) : (
        <div className="space-y-2">
          {constraints.map((constraint) => (
            <CollapsibleCard
              key={constraint.id}
              title={constraint.title}
              subtitle={constraint.constraint_type || undefined}
              icon={<Shield className={`w-4 h-4 ${SEVERITY_COLORS[constraint.severity] || 'text-gray-400'}`} />}
              status={constraint.confirmation_status}
              onConfirm={() => onConfirm('constraint', constraint.id)}
              onNeedsReview={() => onNeedsReview('constraint', constraint.id)}
              onStatusClick={onStatusClick ? () => onStatusClick('constraint', constraint.id, constraint.title, constraint.confirmation_status) : undefined}
            >
              <div className="space-y-2 text-[13px] text-[rgba(55,53,47,0.65)]">
                {constraint.description && (
                  <p className="leading-relaxed">{constraint.description}</p>
                )}
                <div className="flex items-center gap-3 text-[12px]">
                  <span>
                    <span className="font-medium text-[#37352f]">Severity:</span>{' '}
                    <span className={SEVERITY_COLORS[constraint.severity] || ''}>
                      {constraint.severity}
                    </span>
                  </span>
                  {constraint.constraint_type && (
                    <span>
                      <span className="font-medium text-[#37352f]">Type:</span> {constraint.constraint_type}
                    </span>
                  )}
                </div>
              </div>
              <EvidenceBlock evidence={constraint.evidence || []} />
            </CollapsibleCard>
          ))}
        </div>
      )}
    </section>
  )
}
