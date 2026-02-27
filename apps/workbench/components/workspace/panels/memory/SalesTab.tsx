/**
 * SalesTab — Deal readiness score, client profile, stakeholder map, opportunities
 *
 * Requires client_id on project. Empty state with "Link a client" CTA if none.
 */

'use client'

import {
  Users,
  AlertTriangle,
  CheckCircle,
  Info,
  Shield,
  Star,
  User,
  Lightbulb,
} from 'lucide-react'
import type { IntelStakeholderMapEntry, IntelGapOrRisk } from '@/types/workspace'
import { useSalesIntel } from '@/lib/hooks/use-api'

interface SalesTabProps {
  projectId: string
}

export function SalesTab({ projectId }: SalesTabProps) {
  const { data, isLoading } = useSalesIntel(projectId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-brand-primary" />
      </div>
    )
  }

  if (!data || !data.has_client) {
    return (
      <div className="text-center py-12">
        <Users className="w-8 h-8 text-text-placeholder mx-auto mb-3" />
        <p className="text-sm text-[#666666] mb-1">No client linked to this project.</p>
        <p className="text-xs text-text-placeholder">Link a client organization to see sales intelligence.</p>
      </div>
    )
  }

  const score = data.deal_readiness_score

  return (
    <div className="space-y-6">
      {/* Deal Readiness Score */}
      <div className="bg-white rounded-2xl border border-border p-5 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-[12px] font-semibold text-text-body uppercase tracking-wide">
            Deal Readiness
          </h4>
          <span className="text-2xl font-bold text-text-body">{Math.round(score)}/100</span>
        </div>
        {/* Progress bar */}
        <div className="w-full bg-[#F0F0F0] rounded-full h-3 mb-4">
          <div
            className="h-3 rounded-full transition-all"
            style={{
              width: `${Math.min(score, 100)}%`,
              backgroundColor: score >= 70 ? '#3FAF7A' : score >= 40 ? '#E5E5E5' : '#E5E5E5',
            }}
          />
        </div>
        {/* Component breakdown */}
        <div className="grid grid-cols-4 gap-3">
          {data.components.map((c) => (
            <div key={c.name} className="bg-[#F4F4F4] rounded-lg px-3 py-2 text-center">
              <p className="text-[10px] text-text-placeholder mb-0.5">{c.name}</p>
              <p className="text-sm font-semibold text-text-body">{Math.round(c.score)}%</p>
              <p className="text-[9px] text-text-placeholder mt-0.5 truncate">{c.details}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Client Profile */}
        <div className="bg-white rounded-2xl border border-border p-5 shadow-sm">
          <h4 className="text-[12px] font-semibold text-text-body uppercase tracking-wide mb-3">
            Client Profile
          </h4>
          <div className="space-y-2">
            {data.client_name && (
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-text-body">{data.client_name}</span>
              </div>
            )}
            {data.client_industry && (
              <p className="text-[12px] text-[#666666]">
                Industry: <span className="font-medium text-text-body">{data.client_industry}</span>
              </p>
            )}
            {data.client_size && (
              <p className="text-[12px] text-[#666666]">
                Size: <span className="font-medium text-text-body">{data.client_size}</span>
              </p>
            )}
            {data.profile_completeness !== null && data.profile_completeness !== undefined && (
              <div className="mt-2">
                <div className="flex justify-between text-[11px] mb-1">
                  <span className="text-[#666666]">Profile completeness</span>
                  <span className="font-medium text-text-body">{Math.round(data.profile_completeness)}%</span>
                </div>
                <div className="w-full bg-[#F0F0F0] rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full bg-brand-primary"
                    style={{ width: `${Math.min(data.profile_completeness, 100)}%` }}
                  />
                </div>
              </div>
            )}
            {data.vision && (
              <div className="mt-3 pt-3 border-t border-border">
                <p className="text-[11px] font-medium text-text-body mb-1">Vision</p>
                <p className="text-[12px] text-[#666666] leading-relaxed line-clamp-3">{data.vision}</p>
              </div>
            )}
            {data.constraints_summary && (
              <div className="mt-2">
                <p className="text-[11px] font-medium text-text-body mb-1">Constraints</p>
                <p className="text-[12px] text-[#666666] leading-relaxed line-clamp-2">{data.constraints_summary}</p>
              </div>
            )}
          </div>
        </div>

        {/* Stakeholder Map */}
        <div className="bg-white rounded-2xl border border-border p-5 shadow-sm">
          <h4 className="text-[12px] font-semibold text-text-body uppercase tracking-wide mb-3">
            Stakeholder Map
          </h4>
          {data.stakeholder_map.length === 0 ? (
            <p className="text-[12px] text-text-placeholder">No stakeholders identified yet.</p>
          ) : (
            <div className="space-y-2">
              {data.stakeholder_map.map((s) => (
                <StakeholderRow key={s.id} stakeholder={s} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Opportunities & Next Steps (formerly "Gaps & Risks") */}
      {data.gaps_and_risks.length > 0 && (
        <div className="bg-white rounded-2xl border border-border p-5 shadow-sm">
          <h4 className="text-[12px] font-semibold text-text-body uppercase tracking-wide mb-3">
            Opportunities & Next Steps
          </h4>
          <div className="space-y-2">
            {data.gaps_and_risks.map((g, i) => (
              <GapRow key={i} gap={g} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function StakeholderRow({ stakeholder }: { stakeholder: IntelStakeholderMapEntry }) {
  const icon = getStakeholderIcon(stakeholder.stakeholder_type)
  const Icon = icon.component

  return (
    <div className="flex items-center gap-3 py-1.5">
      <div className={`p-1 rounded ${icon.bg}`}>
        <Icon className={`w-3.5 h-3.5 ${icon.color}`} />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[12px] font-medium text-text-body truncate">{stakeholder.name}</p>
        <div className="flex items-center gap-2 text-[10px] text-text-placeholder">
          {stakeholder.stakeholder_type && (
            <span className="capitalize">{stakeholder.stakeholder_type}</span>
          )}
          {stakeholder.role && <span>{stakeholder.role}</span>}
          {stakeholder.influence_level && (
            <span className="capitalize">{stakeholder.influence_level} influence</span>
          )}
        </div>
      </div>
      {!stakeholder.is_addressed && (
        <Lightbulb className="w-3.5 h-3.5 text-brand-primary shrink-0" />
      )}
    </div>
  )
}

function getStakeholderIcon(type: string | null) {
  switch (type) {
    case 'champion':
      return { component: Star, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' }
    case 'sponsor':
      return { component: Shield, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' }
    case 'blocker':
      return { component: AlertTriangle, bg: 'bg-gray-100', color: 'text-[#666666]' }
    default:
      return { component: User, bg: 'bg-gray-100', color: 'text-[#666666]' }
  }
}

function GapRow({ gap }: { gap: IntelGapOrRisk }) {
  const severityConfig = {
    warning: { icon: Lightbulb, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' },
    info: { icon: Info, bg: 'bg-gray-100', color: 'text-text-placeholder' },
    success: { icon: CheckCircle, bg: 'bg-[#E8F5E9]', color: 'text-[#25785A]' },
  }
  const config = severityConfig[gap.severity as keyof typeof severityConfig] || severityConfig.info
  const Icon = config.icon

  return (
    <div className="flex items-center gap-3 py-1">
      <Icon className={`w-3.5 h-3.5 ${config.color} shrink-0`} />
      <p className="text-[12px] text-text-body">{gap.message}</p>
    </div>
  )
}
