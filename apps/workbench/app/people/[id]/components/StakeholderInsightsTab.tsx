'use client'

import { useState, useEffect } from 'react'
import { Brain, ChevronRight, Clock, Loader2 } from 'lucide-react'
import { getStakeholderIntelligenceLogs } from '@/lib/api'
import type { StakeholderDetail, ResolvedStakeholderRef, StakeholderIntelligenceProfile, StakeholderIntelligenceLog } from '@/types/workspace'
import { CompletenessRing } from '@/components/workspace/brd/components/CompletenessRing'

interface StakeholderInsightsTabProps {
  stakeholder: StakeholderDetail
  intelligence: StakeholderIntelligenceProfile | null
  projectId: string
  stakeholderId: string
}

const PROFILE_SECTIONS = [
  { key: 'core_identity', label: 'Core Identity', max: 10 },
  { key: 'engagement_profile', label: 'Engagement', max: 20 },
  { key: 'decision_authority', label: 'Decision Authority', max: 20 },
  { key: 'relationships', label: 'Relationships', max: 20 },
  { key: 'communication', label: 'Communication', max: 10 },
  { key: 'win_conditions_concerns', label: 'Win Conditions', max: 15 },
  { key: 'evidence_depth', label: 'Evidence', max: 5 },
] as const

const ENGAGEMENT_STYLE: Record<string, { bg: string; text: string }> = {
  high: { bg: 'bg-brand-primary-light', text: 'text-brand-primary' },
  medium: { bg: 'bg-brand-primary-light', text: 'text-[#25785A]' },
  low: { bg: 'bg-[#0A1E2F]/10', text: 'text-[#0A1E2F]' },
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-4">
      {children}
    </h3>
  )
}

function PersonCard({ person, variant = 'default' }: { person: ResolvedStakeholderRef; variant?: 'default' | 'blocker' }) {
  const initial = person.name[0]?.toUpperCase() || '?'
  const isBlocker = variant === 'blocker'
  return (
    <div className="flex items-center gap-2.5 p-2.5 rounded-xl bg-[#F4F4F4]">
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-[11px] font-medium flex-shrink-0 ${
        isBlocker ? 'bg-gradient-to-br from-gray-400 to-gray-500' : 'bg-gradient-to-br from-brand-primary to-[#25785A]'
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

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function completenessLabel(score: number): string {
  if (score >= 80) return 'Excellent'
  if (score >= 60) return 'Good'
  if (score >= 30) return 'Fair'
  return 'Poor'
}

function getSectionScore(intelligence: StakeholderIntelligenceProfile, sectionKey: string, max: number): number {
  const match = intelligence.sections.find(s => s.section === sectionKey)
  if (match) return Math.min(match.score, max)
  return 0
}

export function AnalysisHistoryTimeline({
  projectId,
  stakeholderId,
}: {
  projectId: string
  stakeholderId: string
}) {
  const [logs, setLogs] = useState<StakeholderIntelligenceLog[]>([])
  const [logsLoading, setLogsLoading] = useState(true)
  const [expandedLog, setExpandedLog] = useState<string | null>(null)

  useEffect(() => {
    setLogsLoading(true)
    getStakeholderIntelligenceLogs(projectId, stakeholderId, { limit: 20 })
      .then((result) => setLogs(result.logs))
      .catch((err) => console.error('Failed to load intelligence logs:', err))
      .finally(() => setLogsLoading(false))
  }, [projectId, stakeholderId])

  if (logsLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-5 h-5 text-brand-primary animate-spin" />
      </div>
    )
  }

  if (logs.length === 0) {
    return (
      <div className="bg-[#F4F4F4] rounded-lg px-4 py-6 text-center">
        <p className="text-[13px] text-[#666]">No analysis runs yet</p>
      </div>
    )
  }

  return (
    <div className="relative pl-6">
      <div className="absolute left-[15px] top-0 bottom-0 w-px bg-gray-200" />
      <div className="space-y-4">
        {logs.map((log) => {
          const isExpanded = expandedLog === log.id
          const dotColor = log.success ? 'bg-brand-primary' : 'bg-red-400'

          return (
            <div key={log.id} className="relative">
              <div className={`absolute -left-6 top-1 w-[14px] h-[14px] rounded-full border-2 border-white ${dotColor}`} />

              <div
                className="bg-[#F4F4F4] rounded-lg px-3 py-2 cursor-pointer hover:bg-[#ECECEC] transition-colors"
                onClick={() => setExpandedLog(isExpanded ? null : log.id)}
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[12px] text-[#999]">{formatTimeAgo(log.created_at)}</span>
                  <span className="px-1.5 py-0.5 text-[10px] font-medium text-[#666] bg-border rounded">
                    {log.trigger?.replace(/_/g, ' ')}
                  </span>
                  {log.action_summary && (
                    <span className="text-[12px] text-[#333]">{log.action_summary}</span>
                  )}
                  <span className="flex-1" />
                  {log.execution_time_ms != null && (
                    <span className="text-[11px] text-[#999] flex items-center gap-0.5">
                      <Clock className="w-3 h-3" />
                      {log.execution_time_ms < 1000
                        ? `${log.execution_time_ms}ms`
                        : `${(log.execution_time_ms / 1000).toFixed(1)}s`}
                    </span>
                  )}
                  {log.profile_completeness_before != null && log.profile_completeness_after != null && (
                    <span className={`text-[12px] font-semibold ${
                      log.profile_completeness_after! > log.profile_completeness_before! ? 'text-brand-primary' : 'text-[#999]'
                    }`}>
                      {log.profile_completeness_before}% &rarr; {log.profile_completeness_after}%
                    </span>
                  )}
                  <ChevronRight className={`w-3.5 h-3.5 text-[#999] transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                </div>

                {/* Fields affected chips (collapsed) */}
                {!isExpanded && log.fields_affected && log.fields_affected.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {log.fields_affected.map((f, i) => (
                      <span key={i} className="px-1.5 py-0.5 text-[10px] text-[#25785A] bg-[#E8F5E9] rounded">
                        {f.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                )}

                {/* Expanded details */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-border space-y-3">
                    {log.action_type && (
                      <div>
                        <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">Action Type</p>
                        <p className="text-[12px] text-[#666] mt-0.5">{log.action_type.replace(/_/g, ' ')}</p>
                      </div>
                    )}
                    {log.fields_affected && log.fields_affected.length > 0 && (
                      <div>
                        <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Fields Affected</p>
                        <div className="flex flex-wrap gap-1">
                          {log.fields_affected.map((f, i) => (
                            <span key={i} className="px-1.5 py-0.5 text-[10px] text-[#25785A] bg-[#E8F5E9] rounded">
                              {f.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {log.stop_reason && (
                      <div>
                        <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">Stop Reason</p>
                        <p className="text-[12px] text-[#666] mt-0.5">{log.stop_reason}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function StakeholderInsightsTab({ stakeholder, intelligence, projectId, stakeholderId }: StakeholderInsightsTabProps) {
  const s = stakeholder

  // Empty state — no intelligence data yet
  if (!intelligence) {
    const hasEnrichment = s.engagement_level || s.decision_authority || s.engagement_strategy ||
      s.risk_if_disengaged || (s.win_conditions && s.win_conditions.length > 0) ||
      (s.key_concerns && s.key_concerns.length > 0)

    if (!hasEnrichment) {
      return (
        <div className="bg-white border border-border rounded-2xl shadow-sm p-12 text-center">
          <div className="w-16 h-16 rounded-2xl bg-[#F4F4F4] flex items-center justify-center mx-auto mb-4">
            <Brain className="w-7 h-7 text-[#BBB]" />
          </div>
          <h3 className="text-[18px] font-semibold text-[#333] mb-1">Stakeholder Intelligence</h3>
          <p className="text-[14px] text-[#666] max-w-md mx-auto">
            Run the Analyze action to generate a stakeholder intelligence profile
          </p>
        </div>
      )
    }
  }

  const completeness = intelligence?.profile_completeness ?? 0
  const engStyle = ENGAGEMENT_STYLE[s.engagement_level?.toLowerCase() || ''] || ENGAGEMENT_STYLE.medium

  return (
    <div className="space-y-6">
      {/* Profile Completeness */}
      {intelligence && (
        <div className="bg-white rounded-2xl border border-border shadow-md p-5">
          <div className="flex items-center gap-4 mb-5">
            <CompletenessRing score={completeness} size="lg" />
            <div>
              <p className="text-[16px] font-bold text-[#333]">{completeness}%</p>
              <p className="text-[12px] text-[#999]">{completenessLabel(completeness)}</p>
              {intelligence.last_intelligence_at && (
                <p className="text-[11px] text-[#999] mt-0.5">
                  Last analyzed {formatTimeAgo(intelligence.last_intelligence_at)}
                </p>
              )}
            </div>
          </div>
          <div className="space-y-3">
            {PROFILE_SECTIONS.map(({ key, label, max }) => {
              const score = getSectionScore(intelligence, key, max)
              const pct = max > 0 ? (score / max) * 100 : 0
              return (
                <div key={key} className="flex items-center gap-3">
                  <span className="w-36 text-[12px] text-[#666] flex-shrink-0">{label}</span>
                  <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-brand-primary rounded-full transition-all"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <span className="text-[11px] text-[#999] w-10 text-right flex-shrink-0">{score}/{max}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* 2x2 Enrichment Grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Engagement Assessment */}
        <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
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
        <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
          <SectionLabel>Engagement Strategy</SectionLabel>
          {s.engagement_strategy ? (
            <p className="text-[13px] text-[#666] leading-relaxed">{s.engagement_strategy}</p>
          ) : (
            <p className="text-[13px] text-[#BBB] italic">No strategy defined</p>
          )}
        </div>

        {/* Risk if Disengaged */}
        <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
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
        <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
          <SectionLabel>Decision Power</SectionLabel>
          {s.decision_authority ? (
            <div className="space-y-3">
              <p className="text-[13px] text-[#666]">{s.decision_authority}</p>
              {s.approval_required_for && s.approval_required_for.length > 0 && (
                <div>
                  <p className="text-[11px] text-[#BBB] mb-1.5">Approval Required</p>
                  <div className="flex flex-wrap gap-1.5">
                    {s.approval_required_for.map((item, i) => (
                      <span key={i} className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-brand-primary-light text-[#25785A]">{item}</span>
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
        <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
          <div className="grid grid-cols-2 gap-8">
            {s.win_conditions && s.win_conditions.length > 0 && (
              <div>
                <SectionLabel>Win Conditions</SectionLabel>
                <ul className="space-y-2.5">
                  {s.win_conditions.map((wc, i) => (
                    <li key={i} className="flex items-start gap-2.5 text-[13px] text-[#666]">
                      <span className="text-brand-primary mt-0.5 text-lg leading-none">&bull;</span>
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
        <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
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

      {/* Analysis History */}
      <div className="bg-white rounded-2xl border border-border shadow-md p-5">
        <h3 className="text-[14px] font-semibold text-[#333] mb-4">Analysis History</h3>
        <AnalysisHistoryTimeline projectId={projectId} stakeholderId={stakeholderId} />
      </div>
    </div>
  )
}
