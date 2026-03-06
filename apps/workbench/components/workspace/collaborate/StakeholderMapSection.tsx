'use client'

import { useState } from 'react'
import { Users, Shield, Megaphone, UserCheck, AlertCircle } from 'lucide-react'
import { useBRDData, useProjectStakeholders } from '@/lib/hooks/use-api'
import type { StakeholderBRDSummary, StakeholderDetail, InfluenceLevel } from '@/types/workspace'

interface StakeholderMapSectionProps {
  projectId: string
}

// ============================================
// Group config
// ============================================
interface GroupConfig {
  type: string
  label: string
  accent: string
  badgeBg: string
  badgeText: string
  icon: React.ReactNode
  emptyMessage: string
}

const GROUPS: GroupConfig[] = [
  {
    type: 'champion',
    label: 'Champions',
    accent: 'border-l-green-400',
    badgeBg: 'bg-green-50',
    badgeText: 'text-green-700',
    icon: <Shield className="w-3.5 h-3.5 text-green-600" />,
    emptyMessage: 'No champion identified — critical for deal success',
  },
  {
    type: 'sponsor',
    label: 'Sponsors',
    accent: 'border-l-blue-400',
    badgeBg: 'bg-blue-50',
    badgeText: 'text-blue-700',
    icon: <UserCheck className="w-3.5 h-3.5 text-blue-600" />,
    emptyMessage: 'No sponsor identified — who controls budget?',
  },
  {
    type: 'influencer',
    label: 'Influencers',
    accent: 'border-l-amber-400',
    badgeBg: 'bg-amber-50',
    badgeText: 'text-amber-700',
    icon: <Megaphone className="w-3.5 h-3.5 text-amber-600" />,
    emptyMessage: 'No influencers mapped yet',
  },
  {
    type: 'end_user',
    label: 'End Users',
    accent: 'border-l-gray-300',
    badgeBg: 'bg-gray-100',
    badgeText: 'text-gray-600',
    icon: <Users className="w-3.5 h-3.5 text-gray-500" />,
    emptyMessage: 'No end users identified',
  },
  {
    type: 'blocker',
    label: 'Blockers',
    accent: 'border-l-red-400',
    badgeBg: 'bg-red-50',
    badgeText: 'text-red-700',
    icon: <AlertCircle className="w-3.5 h-3.5 text-red-600" />,
    emptyMessage: 'No blockers identified — good sign',
  },
]

// ============================================
// Influence dots
// ============================================
function InfluenceDots({ level }: { level?: InfluenceLevel | null }) {
  const count = level === 'high' ? 3 : level === 'medium' ? 2 : level === 'low' ? 1 : 0
  return (
    <div className="flex items-center gap-0.5" title={`Influence: ${level || 'unknown'}`}>
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i < count ? 'bg-text-secondary' : 'bg-border'}`}
        />
      ))}
    </div>
  )
}

// ============================================
// Stakeholder card
// ============================================
type MergedStakeholder = StakeholderBRDSummary & Partial<Omit<StakeholderDetail, keyof StakeholderBRDSummary>>

function StakeholderCard({ s, group }: { s: MergedStakeholder; group: GroupConfig }) {
  const statusBadge = s.confirmation_status === 'confirmed_client'
    ? 'bg-green-50 text-green-700'
    : s.confirmation_status === 'confirmed_consultant'
      ? 'bg-blue-50 text-blue-700'
      : null

  return (
    <div className={`border-l-3 ${group.accent} bg-white border border-border rounded-r-xl p-3 space-y-1`}>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-text-body">{s.name}</span>
        <InfluenceDots level={s.influence_level} />
        {s.is_primary_contact && (
          <span className="px-1.5 py-0.5 bg-brand-primary-light text-brand-primary text-[9px] font-semibold rounded-full">
            PRIMARY
          </span>
        )}
        {statusBadge && (
          <span className={`px-1.5 py-0.5 rounded-full text-[9px] font-semibold uppercase ${statusBadge}`}>
            Confirmed
          </span>
        )}
      </div>
      {s.role && (
        <p className="text-[12px] text-text-secondary">{s.role}</p>
      )}
      {s.win_conditions && s.win_conditions.length > 0 && (
        <p className="text-[11px] text-text-placeholder">
          Win: {s.win_conditions[0]}
        </p>
      )}
      {s.key_concerns && s.key_concerns.length > 0 && (
        <p className="text-[11px] text-text-placeholder">
          Concern: {s.key_concerns[0]}
        </p>
      )}
      {s.engagement_strategy && (
        <p className="text-[11px] text-text-placeholder italic">
          Strategy: {s.engagement_strategy}
        </p>
      )}
    </div>
  )
}

// ============================================
// Main component
// ============================================
export function StakeholderMapSection({ projectId }: StakeholderMapSectionProps) {
  const { data: brd } = useBRDData(projectId)
  const { data: stakeholderData } = useProjectStakeholders(projectId)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())

  // Merge BRD summary with enriched detail data
  const brdStakeholders = brd?.stakeholders ?? []
  const enrichedMap = new Map(
    (stakeholderData?.stakeholders ?? []).map(s => [s.id, s])
  )
  const merged: MergedStakeholder[] = brdStakeholders.map(s => ({
    ...s,
    ...enrichedMap.get(s.id),
  }))

  // Group by type
  const grouped = GROUPS.map(group => ({
    ...group,
    stakeholders: merged.filter(s => s.stakeholder_type === group.type),
  }))

  // Also collect ungrouped
  const knownTypes = new Set(GROUPS.map(g => g.type))
  const ungrouped = merged.filter(s => !s.stakeholder_type || !knownTypes.has(s.stakeholder_type))

  const totalStakeholders = merged.length

  if (totalStakeholders === 0 && ungrouped.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-border shadow-sm p-5">
        <h3 className="text-sm font-semibold text-text-body flex items-center gap-2">
          <Users className="w-4 h-4 text-text-placeholder" />
          Stakeholder Map
        </h3>
        <p className="text-sm text-text-placeholder mt-3">
          No stakeholders identified yet. Feed meeting transcripts or emails to map the client org.
        </p>
      </div>
    )
  }

  const toggleGroup = (type: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm p-5 space-y-3">
      <h3 className="text-sm font-semibold text-text-body flex items-center gap-2">
        <Users className="w-4 h-4 text-text-placeholder" />
        Stakeholder Map
        <span className="text-[11px] text-text-placeholder font-normal">({totalStakeholders})</span>
      </h3>

      {grouped.map(group => {
        const { stakeholders } = group
        const isExpanded = expandedGroups.has(group.type)
        const visible = isExpanded ? stakeholders : stakeholders.slice(0, 3)
        const hasMore = stakeholders.length > 3

        return (
          <div key={group.type}>
            {/* Group header */}
            <div className="flex items-center gap-2 mb-1.5">
              {group.icon}
              <span className="text-[12px] font-semibold text-text-body">{group.label}</span>
              {stakeholders.length > 0 && (
                <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${group.badgeBg} ${group.badgeText}`}>
                  {stakeholders.length}
                </span>
              )}
            </div>

            {stakeholders.length === 0 ? (
              <div className="border border-dashed border-border rounded-xl px-3 py-2 mb-2">
                <p className="text-[11px] text-text-placeholder">{group.emptyMessage}</p>
              </div>
            ) : (
              <div className="space-y-1.5 mb-2">
                {visible.map(s => (
                  <StakeholderCard key={s.id} s={s} group={group} />
                ))}
                {hasMore && !isExpanded && (
                  <button
                    onClick={() => toggleGroup(group.type)}
                    className="text-[12px] text-brand-primary hover:underline font-medium"
                  >
                    Show all {stakeholders.length}
                  </button>
                )}
                {hasMore && isExpanded && (
                  <button
                    onClick={() => toggleGroup(group.type)}
                    className="text-[12px] text-text-placeholder hover:underline font-medium"
                  >
                    Show less
                  </button>
                )}
              </div>
            )}
          </div>
        )
      })}

      {/* Ungrouped stakeholders */}
      {ungrouped.length > 0 && (
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <Users className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-[12px] font-semibold text-text-body">Uncategorized</span>
            <span className="px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-gray-100 text-gray-600">
              {ungrouped.length}
            </span>
          </div>
          <div className="space-y-1.5">
            {ungrouped.map(s => (
              <StakeholderCard
                key={s.id}
                s={s}
                group={{
                  type: 'unknown',
                  label: 'Unknown',
                  accent: 'border-l-gray-200',
                  badgeBg: 'bg-gray-100',
                  badgeText: 'text-gray-600',
                  icon: null,
                  emptyMessage: '',
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
