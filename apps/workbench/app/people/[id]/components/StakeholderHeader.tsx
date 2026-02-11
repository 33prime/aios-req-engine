'use client'

import { ArrowLeft, Mail, Linkedin, FileText, Clock, Star } from 'lucide-react'
import type { StakeholderDetail } from '@/types/workspace'

interface StakeholderHeaderProps {
  stakeholder: StakeholderDetail
  onBack: () => void
}

function formatType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function formatTimeAgo(dateStr: string | null | undefined): string | null {
  if (!dateStr) return null
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return '1 day ago'
  if (diffDays < 30) return `${diffDays} days ago`
  const diffMonths = Math.floor(diffDays / 30)
  return `${diffMonths}mo ago`
}

export function StakeholderHeader({ stakeholder, onBack }: StakeholderHeaderProps) {
  const s = stakeholder
  const initial = (s.first_name || s.name)?.[0]?.toUpperCase() || '?'
  const hasEnrichment = s.engagement_level || s.decision_authority || s.engagement_strategy
  const isConfirmed = s.confirmation_status === 'confirmed_consultant' || s.confirmation_status === 'confirmed_client'
  const lastActivity = formatTimeAgo(s.updated_at || s.created_at)

  return (
    <div className="mb-6">
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-[13px] text-[#999] hover:text-[#333] mb-5 transition-colors duration-200"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to People
      </button>

      <div className="flex items-start gap-4 mb-3">
        <div className="w-14 h-14 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center text-white text-[22px] font-semibold flex-shrink-0 shadow-sm">
          {initial}
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-[28px] font-bold text-[#333] leading-tight">{s.name}</h1>
          {(s.role || s.organization) && (
            <p className="text-[14px] text-[#666] mt-0.5">
              {s.role}{s.role && s.organization ? ' @ ' : ''}{s.organization}
            </p>
          )}

          {/* Meta row */}
          <div className="flex items-center gap-4 mt-2.5 flex-wrap text-[12px] text-[#999]">
            {s.email && (
              <span className="inline-flex items-center gap-1">
                <Mail className="w-[13px] h-[13px]" />
                {s.email}
              </span>
            )}
            {s.linkedin_profile && (
              <span className="inline-flex items-center gap-1">
                <Linkedin className="w-[13px] h-[13px]" />
                <a
                  href={s.linkedin_profile}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[#3FAF7A] hover:text-[#25785A] hover:underline transition-colors"
                >
                  LinkedIn
                </a>
              </span>
            )}
            {s.project_name && (
              <span className="inline-flex items-center gap-1">
                <FileText className="w-[13px] h-[13px]" />
                <span className="text-[#3FAF7A]">{s.project_name}</span>
              </span>
            )}
            {lastActivity && (
              <span className="inline-flex items-center gap-1">
                <Clock className="w-[13px] h-[13px]" />
                Last activity: {lastActivity}
              </span>
            )}
          </div>

          {/* Badges */}
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {s.stakeholder_type && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-medium bg-[#3FAF7A]/10 text-[#25785A]">
                {formatType(s.stakeholder_type)}
              </span>
            )}
            {s.influence_level && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-medium bg-[#3FAF7A]/10 text-[#25785A]">
                {s.influence_level.charAt(0).toUpperCase() + s.influence_level.slice(1)} Influence
              </span>
            )}
            {s.is_primary_contact && (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-medium bg-[#3FAF7A]/10 text-[#25785A]">
                <Star className="w-2.5 h-2.5 fill-current" />
                Primary Contact
              </span>
            )}
            {isConfirmed && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-medium bg-[#3FAF7A]/10 text-[#3FAF7A]">
                Confirmed
              </span>
            )}
            {hasEnrichment && (
              <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-medium bg-[#3FAF7A]/10 text-[#25785A]">
                Enriched
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
