'use client'

import { Star, ArrowLeft } from 'lucide-react'
import type { StakeholderDetail } from '@/types/workspace'

interface StakeholderHeaderProps {
  stakeholder: StakeholderDetail
  onBack: () => void
}

const TYPE_BADGE: Record<string, { bg: string; text: string }> = {
  champion: { bg: 'bg-green-50', text: 'text-green-700' },
  sponsor: { bg: 'bg-blue-50', text: 'text-blue-700' },
  blocker: { bg: 'bg-red-50', text: 'text-red-700' },
  influencer: { bg: 'bg-purple-50', text: 'text-purple-700' },
  end_user: { bg: 'bg-gray-100', text: 'text-gray-600' },
}

const INFLUENCE_BADGE: Record<string, { bg: string; text: string }> = {
  high: { bg: 'bg-orange-50', text: 'text-orange-700' },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-700' },
  low: { bg: 'bg-gray-100', text: 'text-gray-500' },
}

const STATUS_BADGE: Record<string, { bg: string; text: string; label: string }> = {
  confirmed_consultant: { bg: 'bg-teal-50', text: 'text-teal-700', label: 'Confirmed' },
  confirmed_client: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Client Confirmed' },
  ai_generated: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'AI Generated' },
  needs_client: { bg: 'bg-orange-50', text: 'text-orange-700', label: 'Needs Review' },
}

function formatType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

export function StakeholderHeader({ stakeholder, onBack }: StakeholderHeaderProps) {
  const s = stakeholder
  const typeBadge = TYPE_BADGE[s.stakeholder_type || 'influencer'] || TYPE_BADGE.influencer
  const influenceBadge = INFLUENCE_BADGE[s.influence_level || 'medium'] || INFLUENCE_BADGE.medium
  const statusBadge = STATUS_BADGE[s.confirmation_status || 'ai_generated'] || STATUS_BADGE.ai_generated

  return (
    <div className="mb-8">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-[13px] text-[rgba(55,53,47,0.45)] hover:text-[#37352f] mb-4 transition-colors"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to People
      </button>

      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-gradient-to-br from-teal-400 to-emerald-500 flex items-center justify-center text-white text-[18px] font-medium flex-shrink-0">
          {(s.first_name || s.name)?.[0]?.toUpperCase() || '?'}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-[28px] font-bold text-[#37352f] leading-tight">{s.name}</h1>
          {(s.role || s.organization) && (
            <p className="text-[14px] text-[rgba(55,53,47,0.65)] mt-0.5">
              {s.role}{s.role && s.organization ? ' @ ' : ''}{s.organization}
            </p>
          )}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {s.stakeholder_type && (
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${typeBadge.bg} ${typeBadge.text}`}>
                {formatType(s.stakeholder_type)}
              </span>
            )}
            {s.influence_level && (
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${influenceBadge.bg} ${influenceBadge.text}`}>
                {s.influence_level.charAt(0).toUpperCase() + s.influence_level.slice(1)} Influence
              </span>
            )}
            {s.is_primary_contact && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-amber-50 text-amber-700">
                <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                Primary Contact
              </span>
            )}
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${statusBadge.bg} ${statusBadge.text}`}>
              {statusBadge.label}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
