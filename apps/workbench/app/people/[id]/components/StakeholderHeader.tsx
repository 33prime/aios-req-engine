'use client'

import { ArrowLeft, Mail, Linkedin, FileText, Clock } from 'lucide-react'
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

      {/* Name + inline badge */}
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-[28px] font-bold text-[#333] leading-tight">{s.name}</h1>
        {s.stakeholder_type && (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] font-medium bg-[#3FAF7A]/10 text-[#25785A]">
            {formatType(s.stakeholder_type)}
          </span>
        )}
      </div>

      {/* Role */}
      {(s.role || s.organization) && (
        <p className="text-[14px] text-[#666] mb-2.5">
          {s.role}{s.role && s.organization ? ' @ ' : ''}{s.organization}
        </p>
      )}

      {/* Meta row */}
      <div className="flex items-center gap-4 mb-6 flex-wrap text-[12px] text-[#999]">
        {s.email && (
          <span className="inline-flex items-center gap-1">
            <Mail className="w-[13px] h-[13px]" />
            {s.email}
          </span>
        )}
        {s.project_name && (
          <span className="inline-flex items-center gap-1">
            <FileText className="w-[13px] h-[13px]" />
            <span className="text-[#3FAF7A]">{s.project_name}</span>
          </span>
        )}
        {s.linkedin_profile && (
          <span className="inline-flex items-center gap-1">
            <Linkedin className="w-[13px] h-[13px]" />
            <span className="text-[#999]">&bull;</span>
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
        {lastActivity && (
          <span className="inline-flex items-center gap-1">
            <Clock className="w-[13px] h-[13px]" />
            Last activity: {lastActivity}
          </span>
        )}
      </div>
    </div>
  )
}
