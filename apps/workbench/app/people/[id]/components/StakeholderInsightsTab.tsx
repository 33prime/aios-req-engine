'use client'

import { Brain } from 'lucide-react'
import type { StakeholderDetail, ResolvedStakeholderRef } from '@/types/workspace'

interface StakeholderInsightsTabProps {
  stakeholder: StakeholderDetail
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-4">
      {children}
    </h3>
  )
}

const ENGAGEMENT_STYLE: Record<string, { bg: string; text: string }> = {
  high: { bg: 'bg-[#3FAF7A]/10', text: 'text-[#3FAF7A]' },
  medium: { bg: 'bg-[#3FAF7A]/10', text: 'text-[#25785A]' },
  low: { bg: 'bg-[#0A1E2F]/10', text: 'text-[#0A1E2F]' },
}

function PersonCard({ person, variant = 'default' }: { person: ResolvedStakeholderRef; variant?: 'default' | 'blocker' }) {
  const initial = person.name[0]?.toUpperCase() || '?'
  const isBlocker = variant === 'blocker'
  return (
    <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-[#F4F4F4]">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-medium flex-shrink-0 ${
        isBlocker ? 'bg-gradient-to-br from-gray-400 to-gray-500' : 'bg-gradient-to-br from-[#3FAF7A] to-[#25785A]'
      }`}>
        {initial}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-[#333] truncate">{person.name}</p>
        {person.role && <p className="text-[11px] text-[#999] truncate">{person.role}</p>}
      </div>
    </div>
  )
}

export function StakeholderInsightsTab({ stakeholder }: StakeholderInsightsTabProps) {
  const s = stakeholder
  const hasEnrichment = s.engagement_level || s.decision_authority || s.engagement_strategy ||
    s.risk_if_disengaged || (s.win_conditions && s.win_conditions.length > 0) ||
    (s.key_concerns && s.key_concerns.length > 0)

  if (!hasEnrichment) {
    return (
      <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-12 text-center">
        <div className="w-16 h-16 rounded-2xl bg-[#F4F4F4] flex items-center justify-center mx-auto mb-4">
          <Brain className="w-7 h-7 text-[#BBB]" />
        </div>
        <h3 className="text-[18px] font-semibold text-[#333] mb-1">AI Insights</h3>
        <p className="text-[14px] text-[#666] max-w-md mx-auto">
          No enrichment data available yet. Insights are generated when the AI analyzes signals mentioning this stakeholder.
        </p>
      </div>
    )
  }

  const engStyle = ENGAGEMENT_STYLE[s.engagement_level?.toLowerCase() || ''] || ENGAGEMENT_STYLE.medium

  return (
    <div className="space-y-6">
      {/* 2x2 Grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Engagement Assessment */}
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <SectionLabel>Engagement Assessment</SectionLabel>
          {s.engagement_level ? (
            <div>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-[12px] font-semibold ${engStyle.bg} ${engStyle.text}`}>
                {s.engagement_level.charAt(0).toUpperCase() + s.engagement_level.slice(1)}
              </span>
              {s.last_interaction_date && (
                <p className="text-[12px] text-[#999] mt-3">
                  Last interaction: {new Date(s.last_interaction_date).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </p>
              )}
            </div>
          ) : (
            <p className="text-[13px] text-[#BBB] italic">Not assessed</p>
          )}
        </div>

        {/* Engagement Strategy */}
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <SectionLabel>Engagement Strategy</SectionLabel>
          {s.engagement_strategy ? (
            <p className="text-[13px] text-[#666] leading-relaxed">{s.engagement_strategy}</p>
          ) : (
            <p className="text-[13px] text-[#BBB] italic">No strategy defined</p>
          )}
        </div>

        {/* Risk if Disengaged */}
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <SectionLabel>Risk if Disengaged</SectionLabel>
          {s.risk_if_disengaged ? (
            <div>
              <p className="text-[14px] font-semibold text-[#0A1E2F] mb-1.5">High risk.</p>
              <p className="text-[13px] text-[#666] leading-relaxed">{s.risk_if_disengaged}</p>
            </div>
          ) : (
            <p className="text-[13px] text-[#BBB] italic">Not assessed</p>
          )}
        </div>

        {/* Decision Power */}
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <SectionLabel>Decision Power</SectionLabel>
          {s.decision_authority ? (
            <div className="space-y-3">
              <p className="text-[13px] text-[#666]">{s.decision_authority}</p>
              {s.approval_required_for && s.approval_required_for.length > 0 && (
                <div>
                  <p className="text-[11px] text-[#BBB] mb-1.5">Approval Required</p>
                  <div className="flex flex-wrap gap-1.5">
                    {s.approval_required_for.map((item, i) => (
                      <span key={i} className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#3FAF7A]/10 text-[#25785A]">{item}</span>
                    ))}
                  </div>
                </div>
              )}
              {s.veto_power_over && s.veto_power_over.length > 0 && (
                <div>
                  <p className="text-[11px] text-[#BBB] mb-1.5">Veto Power</p>
                  <div className="flex flex-wrap gap-1.5">
                    {s.veto_power_over.map((item, i) => (
                      <span key={i} className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#0A1E2F]/10 text-[#0A1E2F]">{item}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-[13px] text-[#BBB] italic">Not assessed</p>
          )}
        </div>
      </div>

      {/* Win Conditions & Key Concerns */}
      {((s.win_conditions && s.win_conditions.length > 0) || (s.key_concerns && s.key_concerns.length > 0)) && (
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <div className="grid grid-cols-2 gap-8">
            {s.win_conditions && s.win_conditions.length > 0 && (
              <div>
                <SectionLabel>Win Conditions</SectionLabel>
                <ul className="space-y-2.5">
                  {s.win_conditions.map((wc, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-[13px] text-[#666]">
                      <span className="text-[#3FAF7A] mt-0.5 text-lg leading-none">&bull;</span>
                      <span>{wc}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {s.key_concerns && s.key_concerns.length > 0 && (
              <div>
                <SectionLabel>Key Concerns</SectionLabel>
                <ul className="space-y-2.5">
                  {s.key_concerns.map((kc, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-[13px] text-[#666]">
                      <span className="text-[#0A1E2F]/40 mt-0.5 text-lg leading-none">&bull;</span>
                      <span>{kc}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Relationship Map */}
      {(s.reports_to || (s.allies_resolved && s.allies_resolved.length > 0) || (s.potential_blockers_resolved && s.potential_blockers_resolved.length > 0)) && (
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <SectionLabel>Relationship Map</SectionLabel>
          <div className="grid grid-cols-3 gap-6">
            <div>
              <p className="text-[11px] text-[#BBB] mb-2.5">Reports To</p>
              {s.reports_to ? (
                <PersonCard person={s.reports_to} />
              ) : (
                <p className="text-[13px] text-[#BBB] italic p-2.5">None</p>
              )}
            </div>
            <div>
              <p className="text-[11px] text-[#BBB] mb-2.5">Allies</p>
              {s.allies_resolved && s.allies_resolved.length > 0 ? (
                <div className="space-y-2">
                  {s.allies_resolved.map((ally) => (
                    <PersonCard key={ally.id} person={ally} />
                  ))}
                </div>
              ) : (
                <p className="text-[13px] text-[#BBB] italic p-2.5">None</p>
              )}
            </div>
            <div>
              <p className="text-[11px] text-[#BBB] mb-2.5">Potential Friction</p>
              {s.potential_blockers_resolved && s.potential_blockers_resolved.length > 0 ? (
                <div className="space-y-2">
                  {s.potential_blockers_resolved.map((blocker) => (
                    <PersonCard key={blocker.id} person={blocker} variant="blocker" />
                  ))}
                </div>
              ) : (
                <p className="text-[13px] text-[#BBB] italic p-2.5">None</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
