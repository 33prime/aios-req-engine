'use client'

import { useState, useEffect } from 'react'
import { User, FileText, Brain, Mail, Phone, Building2, Star } from 'lucide-react'
import { DrawerShell } from '@/components/ui/DrawerShell'
import { Spinner } from '@/components/ui/Spinner'
import { getStakeholder } from '@/lib/api'
import { EvidenceBlock } from './EvidenceBlock'
import { ConfirmActions } from './ConfirmActions'
import type { DrawerTab } from '@/components/ui/DrawerShell'
import type { StakeholderBRDSummary, StakeholderDetail } from '@/types/workspace'

interface StakeholderDetailDrawerProps {
  stakeholderId: string
  projectId: string
  initialData: StakeholderBRDSummary
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
}

type TabId = 'details' | 'evidence' | 'enrichment'

const TYPE_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  champion: { bg: 'bg-green-50', text: 'text-green-700', label: 'Champion' },
  sponsor: { bg: 'bg-blue-50', text: 'text-brand-primary-hover', label: 'Sponsor' },
  blocker: { bg: 'bg-red-50', text: 'text-red-700', label: 'Blocker' },
  influencer: { bg: 'bg-purple-50', text: 'text-purple-700', label: 'Influencer' },
  end_user: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]', label: 'End User' },
}

const DRAWER_TABS: DrawerTab[] = [
  { id: 'details', label: 'Details', icon: User },
  { id: 'evidence', label: 'Evidence', icon: FileText },
  { id: 'enrichment', label: 'Enrichment', icon: Brain },
]

export function StakeholderDetailDrawer({
  stakeholderId,
  projectId,
  initialData,
  onClose,
  onConfirm,
  onNeedsReview,
}: StakeholderDetailDrawerProps) {
  const [detail, setDetail] = useState<StakeholderDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<TabId>('details')

  useEffect(() => {
    setLoading(true)
    getStakeholder(projectId, stakeholderId)
      .then((data) => setDetail(data))
      .catch((err) => console.error('Failed to load stakeholder detail:', err))
      .finally(() => setLoading(false))
  }, [projectId, stakeholderId])

  const typeConfig = TYPE_CONFIG[initialData.stakeholder_type || 'influencer'] || TYPE_CONFIG.influencer

  return (
    <DrawerShell
      onClose={onClose}
      icon={User}
      entityLabel="Stakeholder"
      title={initialData.name}
      headerExtra={
        <div>
          {initialData.role && (
            <p className="text-[13px] text-text-placeholder truncate">
              {initialData.role}{initialData.organization ? ` @ ${initialData.organization}` : ''}
            </p>
          )}
          <div className="flex items-center gap-1.5 mt-1">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${typeConfig.bg} ${typeConfig.text}`}>
              {typeConfig.label}
            </span>
            {initialData.is_primary_contact && (
              <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
            )}
          </div>
        </div>
      }
      headerActions={
        <ConfirmActions
          status={initialData.confirmation_status || 'ai_generated'}
          onConfirm={() => onConfirm('stakeholder', stakeholderId)}
          onNeedsReview={() => onNeedsReview('stakeholder', stakeholderId)}
        />
      }
      tabs={DRAWER_TABS}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {loading ? (
        <Spinner />
      ) : activeTab === 'details' ? (
        <DetailsTab data={detail} />
      ) : activeTab === 'evidence' ? (
        <EvidenceBlock evidence={initialData.evidence || []} />
      ) : (
        <EnrichmentTab data={detail} />
      )}
    </DrawerShell>
  )
}

function DetailsTab({ data }: { data: StakeholderDetail | null }) {
  if (!data) return <p className="text-[13px] text-text-placeholder">No details available</p>

  return (
    <div className="space-y-5">
      {/* Contact */}
      <div>
        <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-2">Contact</h4>
        <div className="space-y-1.5">
          {data.email && (
            <div className="flex items-center gap-2 text-[13px] text-[#666666]">
              <Mail className="w-3.5 h-3.5 text-text-placeholder" />
              <span>{data.email}</span>
            </div>
          )}
          {data.phone && (
            <div className="flex items-center gap-2 text-[13px] text-[#666666]">
              <Phone className="w-3.5 h-3.5 text-text-placeholder" />
              <span>{data.phone}</span>
            </div>
          )}
          {data.organization && (
            <div className="flex items-center gap-2 text-[13px] text-[#666666]">
              <Building2 className="w-3.5 h-3.5 text-text-placeholder" />
              <span>{data.organization}</span>
            </div>
          )}
        </div>
      </div>

      {/* Domain Expertise */}
      {data.domain_expertise && data.domain_expertise.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-2">Domain Expertise</h4>
          <div className="flex flex-wrap gap-1.5">
            {data.domain_expertise.map((area, i) => (
              <span key={i} className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#E8F5E9] text-[#25785A]">{area}</span>
            ))}
          </div>
        </div>
      )}

      {/* Priorities */}
      {data.priorities && data.priorities.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-2">Priorities</h4>
          <ul className="space-y-1">
            {data.priorities.map((p, i) => (
              <li key={i} className="text-[13px] text-[#666666] flex items-start gap-2">
                <span className="text-brand-primary mt-1">•</span><span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Concerns */}
      {data.concerns && data.concerns.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-2">Concerns</h4>
          <ul className="space-y-1">
            {data.concerns.map((c, i) => (
              <li key={i} className="text-[13px] text-[#666666] flex items-start gap-2">
                <span className="text-text-placeholder mt-1">•</span><span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Notes */}
      {data.notes && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-2">Notes</h4>
          <p className="text-[13px] text-[#666666] leading-relaxed whitespace-pre-wrap">{data.notes}</p>
        </div>
      )}
    </div>
  )
}

function EnrichmentTab({ data }: { data: StakeholderDetail | null }) {
  if (!data) return <p className="text-[13px] text-text-placeholder">No enrichment data</p>

  const hasEnrichment = data.engagement_level || data.decision_authority || data.engagement_strategy ||
    data.risk_if_disengaged || (data.win_conditions && data.win_conditions.length > 0) ||
    (data.key_concerns && data.key_concerns.length > 0)

  if (!hasEnrichment) {
    return (
      <div className="text-center py-8">
        <Brain className="w-8 h-8 text-border mx-auto mb-2" />
        <p className="text-[13px] text-text-placeholder">No enrichment data available yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {data.engagement_level && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-1">Engagement Level</h4>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium bg-[#E8F5E9] text-[#25785A]">{data.engagement_level}</span>
        </div>
      )}
      {data.decision_authority && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-1">Decision Authority</h4>
          <p className="text-[13px] text-[#666666]">{data.decision_authority}</p>
        </div>
      )}
      {data.engagement_strategy && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-1">Engagement Strategy</h4>
          <p className="text-[13px] text-[#666666] leading-relaxed">{data.engagement_strategy}</p>
        </div>
      )}
      {data.risk_if_disengaged && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-1">Risk if Disengaged</h4>
          <p className="text-[13px] text-[#666666] leading-relaxed">{data.risk_if_disengaged}</p>
        </div>
      )}
      {data.win_conditions && data.win_conditions.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-1">Win Conditions</h4>
          <ul className="space-y-1">
            {data.win_conditions.map((wc, i) => (
              <li key={i} className="text-[13px] text-[#666666]">• {wc}</li>
            ))}
          </ul>
        </div>
      )}
      {data.key_concerns && data.key_concerns.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-text-placeholder uppercase tracking-wider mb-1">Key Concerns</h4>
          <ul className="space-y-1">
            {data.key_concerns.map((kc, i) => (
              <li key={i} className="text-[13px] text-[#666666]">• {kc}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
