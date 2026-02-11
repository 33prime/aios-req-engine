'use client'

import { Users, Star, Mail } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { CollapsibleCard } from '../components/CollapsibleCard'
import { EvidenceBlock } from '../components/EvidenceBlock'
import type { StakeholderBRDSummary } from '@/types/workspace'

interface StakeholdersSectionProps {
  stakeholders: StakeholderBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onOpenDetail: (stakeholder: StakeholderBRDSummary) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
}

const TYPE_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  champion: { bg: 'bg-green-50', text: 'text-green-700', label: 'Champion' },
  sponsor: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Sponsor' },
  blocker: { bg: 'bg-red-50', text: 'text-red-700', label: 'Blocker' },
  influencer: { bg: 'bg-purple-50', text: 'text-purple-700', label: 'Influencer' },
  end_user: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'End User' },
}

const INFLUENCE_CONFIG: Record<string, { bg: string; text: string }> = {
  high: { bg: 'bg-orange-50', text: 'text-orange-700' },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-700' },
  low: { bg: 'bg-gray-100', text: 'text-gray-500' },
}

export function StakeholdersSection({
  stakeholders,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onOpenDetail,
  onRefreshEntity,
}: StakeholdersSectionProps) {
  const confirmedCount = stakeholders.filter(
    (s) => s.confirmation_status === 'confirmed_consultant' || s.confirmation_status === 'confirmed_client'
  ).length

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <SectionHeader
          title="Stakeholders"
          count={stakeholders.length}
          confirmedCount={confirmedCount}
          onConfirmAll={() => onConfirmAll('stakeholder', stakeholders.map((s) => s.id))}
        />
      </div>
      {stakeholders.length === 0 ? (
        <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No stakeholders identified yet</p>
      ) : (
        <div className="space-y-2">
          {stakeholders.map((stakeholder) => {
            const typeConfig = TYPE_CONFIG[stakeholder.stakeholder_type || 'influencer'] || TYPE_CONFIG.influencer
            const influenceConfig = INFLUENCE_CONFIG[stakeholder.influence_level || 'medium'] || INFLUENCE_CONFIG.medium
            const subtitle = stakeholder.role
              ? (stakeholder.organization ? `${stakeholder.role} @ ${stakeholder.organization}` : stakeholder.role)
              : stakeholder.organization || undefined

            return (
              <CollapsibleCard
                key={stakeholder.id}
                title={stakeholder.name}
                subtitle={subtitle}
                icon={<Users className="w-4 h-4 text-purple-500" />}
                status={stakeholder.confirmation_status}
                onConfirm={() => onConfirm('stakeholder', stakeholder.id)}
                onNeedsReview={() => onNeedsReview('stakeholder', stakeholder.id)}
                onDetailClick={() => onOpenDetail(stakeholder)}
              >
                <div className="space-y-2 text-[13px] text-[rgba(55,53,47,0.65)]">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${typeConfig.bg} ${typeConfig.text}`}>
                      {typeConfig.label}
                    </span>
                    {stakeholder.influence_level && (
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${influenceConfig.bg} ${influenceConfig.text}`}>
                        {stakeholder.influence_level.charAt(0).toUpperCase() + stakeholder.influence_level.slice(1)}
                      </span>
                    )}
                    {stakeholder.is_primary_contact && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700">
                        <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                        Primary
                      </span>
                    )}
                  </div>

                  {stakeholder.email && (
                    <div className="flex items-center gap-1.5 text-[12px]">
                      <Mail className="w-3 h-3 text-gray-400" />
                      <span>{stakeholder.email}</span>
                    </div>
                  )}

                  {stakeholder.domain_expertise && stakeholder.domain_expertise.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {stakeholder.domain_expertise.slice(0, 4).map((area, i) => (
                        <span key={i} className="px-1.5 py-0.5 rounded text-[11px] bg-gray-100 text-gray-600">
                          {area}
                        </span>
                      ))}
                      {stakeholder.domain_expertise.length > 4 && (
                        <span className="text-[11px] text-gray-400">+{stakeholder.domain_expertise.length - 4} more</span>
                      )}
                    </div>
                  )}
                </div>
                <EvidenceBlock evidence={stakeholder.evidence || []} />
              </CollapsibleCard>
            )
          })}
        </div>
      )}
    </section>
  )
}
