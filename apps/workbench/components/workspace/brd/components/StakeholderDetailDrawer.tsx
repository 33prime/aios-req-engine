'use client'

import { useState, useEffect } from 'react'
import { X, User, FileText, Brain, Mail, Phone, Building2, Star, Shield, Target, AlertTriangle, Trophy } from 'lucide-react'
import { getStakeholder } from '@/lib/api'
import { EvidenceBlock } from './EvidenceBlock'
import { ConfirmActions } from './ConfirmActions'
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
  sponsor: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Sponsor' },
  blocker: { bg: 'bg-red-50', text: 'text-red-700', label: 'Blocker' },
  influencer: { bg: 'bg-purple-50', text: 'text-purple-700', label: 'Influencer' },
  end_user: { bg: 'bg-gray-100', text: 'text-gray-600', label: 'End User' },
}

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

  const tabs: { id: TabId; label: string; icon: React.ReactNode }[] = [
    { id: 'details', label: 'Details', icon: <User className="w-3.5 h-3.5" /> },
    { id: 'evidence', label: 'Evidence', icon: <FileText className="w-3.5 h-3.5" /> },
    { id: 'enrichment', label: 'Enrichment', icon: <Brain className="w-3.5 h-3.5" /> },
  ]

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/20 z-40" onClick={onClose} />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-screen w-[560px] max-w-[90vw] bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-start gap-3 min-w-0">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-400 to-indigo-500 flex items-center justify-center text-white text-[14px] font-medium flex-shrink-0 mt-0.5">
              {(initialData.first_name || initialData.name)?.[0]?.toUpperCase() || '?'}
            </div>
            <div className="min-w-0">
              <h2 className="text-[16px] font-semibold text-[#37352f] truncate">{initialData.name}</h2>
              {initialData.role && (
                <p className="text-[13px] text-[rgba(55,53,47,0.45)] truncate">
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
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0">
            <X className="w-4 h-4 text-gray-400" />
          </button>
        </div>

        {/* Confirmation actions */}
        <div className="px-6 py-2 border-b border-gray-50">
          <ConfirmActions
            status={initialData.confirmation_status || 'ai_generated'}
            onConfirm={() => onConfirm('stakeholder', stakeholderId)}
            onNeedsReview={() => onNeedsReview('stakeholder', stakeholderId)}
          />
        </div>

        {/* Tabs */}
        <div className="flex gap-0 border-b border-gray-100 px-6">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-2.5 text-[12px] font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'text-[#009b87] border-[#009b87]'
                  : 'text-[rgba(55,53,47,0.45)] border-transparent hover:text-[rgba(55,53,47,0.65)]'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#009b87]" />
            </div>
          ) : activeTab === 'details' ? (
            <DetailsTab data={detail} />
          ) : activeTab === 'evidence' ? (
            <EvidenceBlock evidence={initialData.evidence || []} />
          ) : (
            <EnrichmentTab data={detail} />
          )}
        </div>
      </div>
    </>
  )
}

function DetailsTab({ data }: { data: StakeholderDetail | null }) {
  if (!data) return <p className="text-[13px] text-gray-400">No details available</p>

  return (
    <div className="space-y-5">
      {/* Contact */}
      <div>
        <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-2">Contact</h4>
        <div className="space-y-1.5">
          {data.email && (
            <div className="flex items-center gap-2 text-[13px] text-[rgba(55,53,47,0.65)]">
              <Mail className="w-3.5 h-3.5 text-gray-400" />
              <span>{data.email}</span>
            </div>
          )}
          {data.phone && (
            <div className="flex items-center gap-2 text-[13px] text-[rgba(55,53,47,0.65)]">
              <Phone className="w-3.5 h-3.5 text-gray-400" />
              <span>{data.phone}</span>
            </div>
          )}
          {data.organization && (
            <div className="flex items-center gap-2 text-[13px] text-[rgba(55,53,47,0.65)]">
              <Building2 className="w-3.5 h-3.5 text-gray-400" />
              <span>{data.organization}</span>
            </div>
          )}
        </div>
      </div>

      {/* Domain Expertise */}
      {data.domain_expertise && data.domain_expertise.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-2">Domain Expertise</h4>
          <div className="flex flex-wrap gap-1.5">
            {data.domain_expertise.map((area, i) => (
              <span key={i} className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-teal-50 text-teal-700">{area}</span>
            ))}
          </div>
        </div>
      )}

      {/* Priorities */}
      {data.priorities && data.priorities.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-2">Priorities</h4>
          <ul className="space-y-1">
            {data.priorities.map((p, i) => (
              <li key={i} className="text-[13px] text-[rgba(55,53,47,0.65)] flex items-start gap-2">
                <span className="text-[#009b87] mt-1">•</span><span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Concerns */}
      {data.concerns && data.concerns.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-2">Concerns</h4>
          <ul className="space-y-1">
            {data.concerns.map((c, i) => (
              <li key={i} className="text-[13px] text-[rgba(55,53,47,0.65)] flex items-start gap-2">
                <span className="text-orange-500 mt-1">•</span><span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Notes */}
      {data.notes && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-2">Notes</h4>
          <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed whitespace-pre-wrap">{data.notes}</p>
        </div>
      )}
    </div>
  )
}

function EnrichmentTab({ data }: { data: StakeholderDetail | null }) {
  if (!data) return <p className="text-[13px] text-gray-400">No enrichment data</p>

  const hasEnrichment = data.engagement_level || data.decision_authority || data.engagement_strategy ||
    data.risk_if_disengaged || (data.win_conditions && data.win_conditions.length > 0) ||
    (data.key_concerns && data.key_concerns.length > 0)

  if (!hasEnrichment) {
    return (
      <div className="text-center py-8">
        <Brain className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-[13px] text-[rgba(55,53,47,0.45)]">No enrichment data available yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {data.engagement_level && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-1">Engagement Level</h4>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[12px] font-medium bg-teal-50 text-teal-700">{data.engagement_level}</span>
        </div>
      )}
      {data.decision_authority && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-1">Decision Authority</h4>
          <p className="text-[13px] text-[rgba(55,53,47,0.65)]">{data.decision_authority}</p>
        </div>
      )}
      {data.engagement_strategy && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-1">Engagement Strategy</h4>
          <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed">{data.engagement_strategy}</p>
        </div>
      )}
      {data.risk_if_disengaged && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-1">Risk if Disengaged</h4>
          <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed">{data.risk_if_disengaged}</p>
        </div>
      )}
      {data.win_conditions && data.win_conditions.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-1">Win Conditions</h4>
          <ul className="space-y-1">
            {data.win_conditions.map((wc, i) => (
              <li key={i} className="text-[13px] text-[rgba(55,53,47,0.65)]">• {wc}</li>
            ))}
          </ul>
        </div>
      )}
      {data.key_concerns && data.key_concerns.length > 0 && (
        <div>
          <h4 className="text-[12px] font-semibold text-[rgba(55,53,47,0.45)] uppercase tracking-wider mb-1">Key Concerns</h4>
          <ul className="space-y-1">
            {data.key_concerns.map((kc, i) => (
              <li key={i} className="text-[13px] text-[rgba(55,53,47,0.65)]">• {kc}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
