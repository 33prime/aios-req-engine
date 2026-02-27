'use client'

import { User, Mail, Star } from 'lucide-react'
import type { StakeholderDetail } from '@/types/workspace'

interface PeopleTableProps {
  stakeholders: StakeholderDetail[]
  onRowClick: (stakeholder: StakeholderDetail) => void
}

const TYPE_BADGE: Record<string, { bg: string; text: string }> = {
  champion: { bg: 'bg-green-50', text: 'text-green-700' },
  sponsor: { bg: 'bg-blue-50', text: 'text-brand-primary-hover' },
  blocker: { bg: 'bg-red-50', text: 'text-red-700' },
  influencer: { bg: 'bg-purple-50', text: 'text-purple-700' },
  end_user: { bg: 'bg-gray-100', text: 'text-gray-600' },
}

const INFLUENCE_BADGE: Record<string, { bg: string; text: string }> = {
  high: { bg: 'bg-orange-50', text: 'text-orange-700' },
  medium: { bg: 'bg-yellow-50', text: 'text-yellow-700' },
  low: { bg: 'bg-gray-100', text: 'text-gray-500' },
}

function formatType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  const diff = Date.now() - new Date(dateStr).getTime()
  const days = Math.floor(diff / 86400000)
  if (days === 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 30) return `${days}d ago`
  const months = Math.floor(days / 30)
  return `${months}mo ago`
}

export function PeopleTable({ stakeholders, onRowClick }: PeopleTableProps) {
  if (stakeholders.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
        <User className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-[14px] font-medium text-[#37352f] mb-1">No stakeholders found</p>
        <p className="text-[13px] text-text-placeholder">
          Stakeholders are extracted from signals or can be added manually.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50/50">
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-placeholder uppercase tracking-wider">Name</th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-placeholder uppercase tracking-wider">Role</th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-placeholder uppercase tracking-wider">Type</th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-placeholder uppercase tracking-wider">Influence</th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-placeholder uppercase tracking-wider">Project</th>
            <th className="text-left px-4 py-2.5 text-[11px] font-semibold text-text-placeholder uppercase tracking-wider">Updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-50">
          {stakeholders.map((s) => {
            const typeBadge = TYPE_BADGE[s.stakeholder_type || 'influencer'] || TYPE_BADGE.influencer
            const influenceBadge = INFLUENCE_BADGE[s.influence_level || 'medium'] || INFLUENCE_BADGE.medium
            return (
              <tr
                key={s.id}
                onClick={() => onRowClick(s)}
                className="hover:bg-gray-50/50 cursor-pointer transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-teal-400 to-emerald-500 flex items-center justify-center text-white text-[12px] font-medium flex-shrink-0">
                      {(s.first_name || s.name)?.[0]?.toUpperCase() || '?'}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[13px] font-medium text-[#37352f] truncate">{s.name}</span>
                        {s.is_primary_contact && (
                          <Star className="w-3 h-3 text-amber-400 fill-amber-400 flex-shrink-0" />
                        )}
                      </div>
                      {s.email && (
                        <div className="flex items-center gap-1 text-[11px] text-text-placeholder">
                          <Mail className="w-3 h-3" />
                          <span className="truncate">{s.email}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-[13px] text-[#666666]">
                  {s.role || '—'}
                </td>
                <td className="px-4 py-3">
                  {s.stakeholder_type && (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${typeBadge.bg} ${typeBadge.text}`}>
                      {formatType(s.stakeholder_type)}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {s.influence_level && (
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${influenceBadge.bg} ${influenceBadge.text}`}>
                      {s.influence_level.charAt(0).toUpperCase() + s.influence_level.slice(1)}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-[13px] text-[#666666]">
                  {s.project_name || '—'}
                </td>
                <td className="px-4 py-3 text-[12px] text-text-placeholder">
                  {timeAgo(s.updated_at || s.created_at)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
