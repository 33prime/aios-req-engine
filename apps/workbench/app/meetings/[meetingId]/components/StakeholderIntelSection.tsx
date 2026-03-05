'use client'

import { useState } from 'react'
import { Users, ChevronDown, ChevronUp, Shield, Target, AlertTriangle, Zap, MessageCircle } from 'lucide-react'
import type { StakeholderIntel } from '@/types/call-intelligence'

const TYPE_CONFIG: Record<string, { bg: string; text: string; label: string }> = {
  champion:   { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Champion' },
  sponsor:    { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]', label: 'Sponsor' },
  blocker:    { bg: 'bg-[#044159]', text: 'text-white',      label: 'Blocker' },
  influencer: { bg: 'bg-[#E0EFF3]', text: 'text-[#044159]', label: 'Influencer' },
  end_user:   { bg: 'bg-[#F0F0F0]', text: 'text-[#666]',    label: 'End User' },
}

const INFLUENCE_CONFIG: Record<string, { bg: string; text: string }> = {
  high:   { bg: 'bg-[#044159]', text: 'text-white' },
  medium: { bg: 'bg-[#E0EFF3]', text: 'text-[#044159]' },
  low:    { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
}

function CompletenessRing({ value }: { value: number }) {
  const r = 10
  const circumference = 2 * Math.PI * r
  const offset = circumference - (value / 100) * circumference
  const color = value >= 70 ? '#25785A' : value >= 40 ? '#044159' : '#999'

  return (
    <svg width="28" height="28" viewBox="0 0 28 28" className="shrink-0">
      <circle cx="14" cy="14" r={r} fill="none" stroke="#E8E8E8" strokeWidth="2.5" />
      <circle
        cx="14" cy="14" r={r} fill="none" stroke={color} strokeWidth="2.5"
        strokeDasharray={circumference} strokeDashoffset={offset}
        strokeLinecap="round" transform="rotate(-90 14 14)"
      />
      <text x="14" y="14.5" textAnchor="middle" dominantBaseline="middle"
        className="text-[7px] font-bold" fill={color}>
        {value}
      </text>
    </svg>
  )
}

function BriefingSection({ icon, label, children }: {
  icon: React.ReactNode
  label: string
  children: React.ReactNode
}) {
  return (
    <div className="mt-2.5">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[#88BABF]">{icon}</span>
        <span className="text-[10px] font-semibold text-[#044159] uppercase tracking-wide">{label}</span>
      </div>
      {children}
    </div>
  )
}

function StakeholderBriefingCard({ s, defaultExpanded }: { s: StakeholderIntel; defaultExpanded: boolean }) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const typeConfig = TYPE_CONFIG[s.stakeholder_type] || TYPE_CONFIG.end_user
  const influenceConfig = INFLUENCE_CONFIG[s.influence] || INFLUENCE_CONFIG.low

  const hasEnrichment = !!(
    s.win_conditions?.length || s.decision_authority || s.domain_expertise?.length ||
    s.priorities?.length || s.risk_if_disengaged || s.approval_required_for?.length
  )

  const hasApproach = !!s.approach_notes && s.approach_notes !== `Build rapport with ${s.name} — understand their perspective.`

  return (
    <div className="bg-white rounded-lg border border-border hover:border-[#D0D0D0] transition-all overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-3.5 py-3 flex items-start gap-3 text-left hover:bg-[#FAFAFA] transition-colors"
      >
        {/* Completeness ring */}
        {s.profile_completeness ? (
          <CompletenessRing value={s.profile_completeness} />
        ) : (
          <div className="w-7 h-7 rounded-full bg-[#E0EFF3] flex items-center justify-center shrink-0">
            <Users className="w-3.5 h-3.5 text-[#044159]" />
          </div>
        )}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[13px] font-semibold text-text-primary">{s.name}</span>
            <span className={`px-1.5 py-[1px] text-[10px] font-semibold rounded ${typeConfig.bg} ${typeConfig.text}`}>
              {typeConfig.label}
            </span>
            <span className={`px-1.5 py-[1px] text-[10px] font-semibold rounded ${influenceConfig.bg} ${influenceConfig.text}`}>
              {s.influence} influence
            </span>
          </div>
          {s.role && <p className="text-[11px] text-text-muted mt-0.5">{s.role}</p>}

          {/* Approach strategy — always visible as the key takeaway */}
          {hasApproach && (
            <div className="mt-2 px-2.5 py-1.5 bg-[#F0F7FA] border-l-2 border-[#044159] rounded-r">
              <p className="text-[11px] text-[#044159] leading-relaxed">{s.approach_notes}</p>
            </div>
          )}
        </div>

        <span className="text-text-muted mt-1 shrink-0">
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </span>
      </button>

      {/* Expanded briefing sections */}
      {expanded && (
        <div className="px-3.5 pb-3.5 pt-0 border-t border-[#F0F0F0]">

          {/* Win Conditions — what success looks like */}
          {s.win_conditions && s.win_conditions.length > 0 && (
            <BriefingSection icon={<Target className="w-3 h-3" />} label="What winning looks like">
              <ul className="space-y-1 pl-1">
                {s.win_conditions.map((w, i) => (
                  <li key={i} className="text-[11px] text-text-secondary leading-relaxed flex gap-1.5">
                    <span className="text-[#3FAF7A] mt-0.5 shrink-0">+</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </BriefingSection>
          )}

          {/* Key Concerns — landmines */}
          {s.key_concerns && s.key_concerns.length > 0 && (
            <BriefingSection icon={<AlertTriangle className="w-3 h-3" />} label="Watch out for">
              <ul className="space-y-1 pl-1">
                {s.key_concerns.map((c, i) => (
                  <li key={i} className="text-[11px] text-text-secondary leading-relaxed flex gap-1.5">
                    <span className="text-[#88BABF] mt-0.5 shrink-0">&mdash;</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </BriefingSection>
          )}

          {/* Decision Authority — who can say yes/no */}
          {(s.decision_authority || s.approval_required_for?.length || s.veto_power_over?.length) && (
            <BriefingSection icon={<Shield className="w-3 h-3" />} label="Decision power">
              {s.decision_authority && (
                <p className="text-[11px] text-text-secondary leading-relaxed pl-1">{s.decision_authority}</p>
              )}
              {s.approval_required_for && s.approval_required_for.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1 pl-1">
                  {s.approval_required_for.map((a, i) => (
                    <span key={i} className="px-1.5 py-0.5 text-[10px] bg-[#E8F5E9] text-[#25785A] rounded">
                      approves: {a}
                    </span>
                  ))}
                </div>
              )}
              {s.veto_power_over && s.veto_power_over.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1 pl-1">
                  {s.veto_power_over.map((v, i) => (
                    <span key={i} className="px-1.5 py-0.5 text-[10px] bg-[#044159] text-white rounded">
                      veto: {v}
                    </span>
                  ))}
                </div>
              )}
            </BriefingSection>
          )}

          {/* Domain expertise — where to probe */}
          {s.domain_expertise && s.domain_expertise.length > 0 && (
            <BriefingSection icon={<Zap className="w-3 h-3" />} label="Deep knowledge (probe here)">
              <div className="flex flex-wrap gap-1 pl-1">
                {s.domain_expertise.map((d, i) => (
                  <span key={i} className="px-1.5 py-0.5 text-[10px] bg-[#E0EFF3] text-[#044159] rounded font-medium">
                    {d.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </BriefingSection>
          )}

          {/* Priorities — what's on their plate */}
          {s.priorities && s.priorities.length > 0 && (
            <BriefingSection icon={<Target className="w-3 h-3" />} label="Current priorities">
              <ul className="space-y-0.5 pl-1">
                {s.priorities.map((p, i) => (
                  <li key={i} className="text-[11px] text-text-secondary leading-relaxed">
                    {typeof p === 'string' ? p : JSON.stringify(p)}
                  </li>
                ))}
              </ul>
            </BriefingSection>
          )}

          {/* Risk if disengaged */}
          {s.risk_if_disengaged && (
            <BriefingSection icon={<AlertTriangle className="w-3 h-3" />} label="Risk if disengaged">
              <p className="text-[11px] text-text-secondary leading-relaxed pl-1">{s.risk_if_disengaged}</p>
            </BriefingSection>
          )}

          {/* Preferred channel + topic mentions */}
          {(s.preferred_channel || (s.topic_mentions && Object.keys(s.topic_mentions).length > 0)) && (
            <BriefingSection icon={<MessageCircle className="w-3 h-3" />} label="Communication">
              <div className="pl-1 space-y-1">
                {s.preferred_channel && (
                  <p className="text-[11px] text-text-secondary">
                    Prefers: <span className="font-medium text-[#044159]">{s.preferred_channel.replace(/_/g, ' ')}</span>
                  </p>
                )}
                {s.topic_mentions && Object.keys(s.topic_mentions).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {Object.entries(s.topic_mentions)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 6)
                      .map(([topic, count], i) => (
                        <span key={i} className="px-1.5 py-0.5 text-[10px] bg-[#F5F5F5] text-text-muted rounded">
                          {topic} <span className="font-semibold text-[#044159]">{count}</span>
                        </span>
                      ))}
                  </div>
                )}
              </div>
            </BriefingSection>
          )}

          {/* Entity ownership */}
          {s.owns_entities && s.owns_entities.length > 0 && (
            <div className="mt-2 pl-1">
              <div className="flex flex-wrap gap-1">
                {s.owns_entities.map((e, i) => (
                  <span key={i} className="px-1.5 py-0.5 text-[10px] bg-[#F0F0F0] text-[#666] rounded">
                    owns: {e.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export function StakeholderIntelSection({ intel }: { intel: StakeholderIntel[] }) {
  if (!intel || intel.length === 0) return null

  return (
    <div className="mt-7">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5 mb-3">
        <Users className="w-3.5 h-3.5" /> Stakeholder Briefing
      </h3>
      <div className="space-y-2">
        {intel.map((s, i) => (
          <StakeholderBriefingCard key={i} s={s} defaultExpanded={i === 0} />
        ))}
      </div>
    </div>
  )
}
