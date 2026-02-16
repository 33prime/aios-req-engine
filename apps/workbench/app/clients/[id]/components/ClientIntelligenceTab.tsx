'use client'

import { useState, useEffect } from 'react'
import { ChevronRight, Sparkles, AlertTriangle, Users, Loader2 } from 'lucide-react'
import { getClientIntelligenceLogs } from '@/lib/api'
import type { ClientIntelligenceProfile } from '@/lib/api'
import type { ClientDetail, ClientIntelligenceLog } from '@/types/workspace'
import { CompletenessRing } from '@/components/workspace/brd/components/CompletenessRing'

interface ClientIntelligenceTabProps {
  clientId: string
  client: ClientDetail
  intelligence: ClientIntelligenceProfile | null
}

const PROFILE_SECTIONS = [
  { key: 'firmographics', label: 'Firmographics', max: 15 },
  { key: 'stakeholder_map', label: 'Stakeholder Map', max: 20 },
  { key: 'organizational_context', label: 'Org Context', max: 15 },
  { key: 'constraints', label: 'Constraints', max: 15 },
  { key: 'vision_strategy', label: 'Vision/Strategy', max: 10 },
  { key: 'data_landscape', label: 'Data Landscape', max: 10 },
  { key: 'competitive_context', label: 'Competitive', max: 10 },
  { key: 'portfolio_health', label: 'Portfolio Health', max: 5 },
] as const

function completenessLabel(score: number): string {
  if (score >= 80) return 'Excellent'
  if (score >= 60) return 'Good'
  if (score >= 30) return 'Fair'
  return 'Poor'
}

function estimateSectionScore(intel: ClientIntelligenceProfile, sectionKey: string, max: number): number {
  const s = intel.sections
  switch (sectionKey) {
    case 'firmographics': {
      const f = s.firmographics
      let score = 0
      if (f.company_summary) score += 3
      if (f.market_position) score += 2
      if (f.technology_maturity) score += 2
      if (f.digital_readiness) score += 2
      if (f.revenue_range) score += 2
      if (f.employee_count) score += 2
      if (f.headquarters) score += 1
      if (f.tech_stack?.length) score += 1
      return Math.min(score, max)
    }
    case 'stakeholder_map':
      return Math.min((intel.profile_completeness > 60 ? 14 : intel.profile_completeness > 30 ? 8 : 3), max)
    case 'organizational_context':
      return Math.min(Object.keys(s.organizational_context || {}).length * 3, max)
    case 'constraints':
      return Math.min((s.constraints?.length || 0) * 3, max)
    case 'vision_strategy':
      return s.vision ? Math.min(8, max) : 0
    case 'data_landscape':
      return Math.min(intel.profile_completeness > 50 ? 6 : 2, max)
    case 'competitive_context':
      return Math.min((s.competitors?.length || 0) * 3, max)
    case 'portfolio_health':
      return Math.min(intel.profile_completeness > 70 ? 4 : 1, max)
    default:
      return 0
  }
}

function CollapsibleSection({ title, icon, children, defaultOpen = false }: {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-5 py-4 text-left hover:bg-[#FAFAFA] transition-colors"
      >
        <ChevronRight className={`w-4 h-4 text-[#999] transition-transform ${open ? 'rotate-90' : ''}`} />
        {icon}
        <span className="text-[14px] font-semibold text-[#333]">{title}</span>
      </button>
      <div
        className={`transition-all duration-200 overflow-hidden ${
          open ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-5 pb-5 border-t border-[#E5E5E5]">
          {children}
        </div>
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

export function ClientIntelligenceTab({ clientId, client, intelligence }: ClientIntelligenceTabProps) {
  const [logs, setLogs] = useState<ClientIntelligenceLog[]>([])
  const [logsLoading, setLogsLoading] = useState(true)
  const [expandedLog, setExpandedLog] = useState<string | null>(null)

  useEffect(() => {
    loadLogs()
  }, [clientId])

  const loadLogs = async () => {
    setLogsLoading(true)
    try {
      const result = await getClientIntelligenceLogs(clientId)
      setLogs(result.logs)
    } catch (err) {
      console.error('Failed to load intelligence logs:', err)
    } finally {
      setLogsLoading(false)
    }
  }

  if (!intelligence) {
    return (
      <div className="text-center py-12 bg-white rounded-2xl border border-[#E5E5E5] shadow-md">
        <Sparkles className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
        <p className="text-[13px] text-[#666] mb-1">No intelligence data yet</p>
        <p className="text-[12px] text-[#999]">Run the Analyze action to generate a client intelligence profile</p>
      </div>
    )
  }

  const completeness = intelligence.profile_completeness

  return (
    <div className="space-y-6">
      {/* Profile Completeness */}
      <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
        <div className="flex items-center gap-4 mb-5">
          <CompletenessRing score={completeness} size="lg" />
          <div>
            <p className="text-[16px] font-bold text-[#333]">{completeness}%</p>
            <p className="text-[12px] text-[#999]">{completenessLabel(completeness)}</p>
          </div>
        </div>
        <div className="space-y-3">
          {PROFILE_SECTIONS.map(({ key, label, max }) => {
            const score = estimateSectionScore(intelligence, key, max)
            const pct = max > 0 ? (score / max) * 100 : 0
            return (
              <div key={key} className="flex items-center gap-3">
                <span className="w-36 text-[12px] text-[#666] flex-shrink-0">{label}</span>
                <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#3FAF7A] rounded-full transition-all"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-[11px] text-[#999] w-10 text-right flex-shrink-0">{score}/{max}</span>
              </div>
            )
          })}
        </div>
      </div>

      {/* Vision Synthesis */}
      {intelligence.sections.vision && (
        <CollapsibleSection
          title="Vision Synthesis"
          icon={<Sparkles className="w-4 h-4 text-[#3FAF7A]" />}
          defaultOpen
        >
          <p className="text-[13px] text-[#666] leading-relaxed pt-3">{intelligence.sections.vision}</p>
        </CollapsibleSection>
      )}

      {/* Organizational Context */}
      {intelligence.sections.organizational_context && Object.keys(intelligence.sections.organizational_context).length > 0 && (
        <CollapsibleSection
          title="Organizational Context"
          icon={<Users className="w-4 h-4 text-[#666]" />}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-3">
            {Object.entries(intelligence.sections.organizational_context).map(([key, val]) => (
              <div key={key} className="bg-[#F4F4F4] rounded-lg px-3 py-2">
                <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">
                  {key.replace(/_/g, ' ')}
                </p>
                <p className="text-[13px] text-[#333] mt-0.5">{String(val)}</p>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Constraints */}
      {intelligence.sections.constraints && intelligence.sections.constraints.length > 0 && (
        <CollapsibleSection
          title={`Constraints (${intelligence.sections.constraints.length})`}
          icon={<AlertTriangle className="w-4 h-4 text-[#666]" />}
        >
          <div className="space-y-2 pt-3">
            {intelligence.sections.constraints.map((c, i) => (
              <div key={i} className="bg-[#F4F4F4] rounded-xl p-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-[13px] font-semibold text-[#333]">{c.title}</span>
                  <span className="px-1.5 py-0.5 text-[10px] font-medium text-[#666] bg-[#E5E5E5] rounded">
                    {c.severity}
                  </span>
                  <span className="px-1.5 py-0.5 text-[10px] font-medium text-[#666] bg-[#E5E5E5] rounded">
                    {c.category}
                  </span>
                </div>
                <p className="text-[12px] text-[#666]">{c.description}</p>
                {c.source && (
                  <p className="text-[11px] text-[#999] mt-1">Source: {c.source}</p>
                )}
                {c.impacts && c.impacts.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {c.impacts.map((impact, j) => (
                      <span key={j} className="px-1.5 py-0.5 text-[10px] text-[#999] bg-white rounded border border-[#E5E5E5]">
                        {impact}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Role Gaps */}
      {intelligence.sections.role_gaps && intelligence.sections.role_gaps.length > 0 && (
        <CollapsibleSection
          title={`Role Gaps (${intelligence.sections.role_gaps.length})`}
          icon={<Users className="w-4 h-4 text-[#666]" />}
        >
          <div className="space-y-2 pt-3">
            {intelligence.sections.role_gaps.map((gap, i) => (
              <div key={i} className="bg-[#F4F4F4] rounded-xl p-3">
                <div className="flex items-center gap-2">
                  <span className="text-[13px] font-semibold text-[#333]">{gap.role}</span>
                  <span className="px-1.5 py-0.5 text-[10px] font-medium text-[#666] bg-[#E5E5E5] rounded">
                    {gap.urgency}
                  </span>
                </div>
                <p className="text-[12px] text-[#666] mt-1">{gap.why_needed}</p>
                {gap.which_areas && gap.which_areas.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-1.5">
                    {gap.which_areas.map((area, j) => (
                      <span key={j} className="px-1.5 py-0.5 text-[10px] text-[#999] bg-white rounded border border-[#E5E5E5]">
                        {area}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Analysis History */}
      <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
        <h3 className="text-[14px] font-semibold text-[#333] mb-4">Analysis History</h3>
        {logsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-[#3FAF7A] animate-spin" />
          </div>
        ) : logs.length === 0 ? (
          <div className="bg-[#F4F4F4] rounded-lg px-4 py-6 text-center">
            <p className="text-[13px] text-[#666]">No analysis runs yet</p>
          </div>
        ) : (
          <div className="relative pl-6">
            {/* Vertical line */}
            <div className="absolute left-[15px] top-0 bottom-0 w-px bg-gray-200" />

            <div className="space-y-4">
              {logs.map((log) => {
                const isExpanded = expandedLog === log.id
                const dotColor = log.status === 'completed' ? 'bg-[#3FAF7A]'
                  : log.status === 'error' ? 'bg-red-400'
                  : 'bg-[#999]'

                return (
                  <div key={log.id} className="relative">
                    {/* Dot */}
                    <div className={`absolute -left-6 top-1 w-[14px] h-[14px] rounded-full border-2 border-white ${dotColor}`} />

                    {/* Card */}
                    <div
                      className="bg-[#F4F4F4] rounded-lg px-3 py-2 cursor-pointer hover:bg-[#ECECEC] transition-colors"
                      onClick={() => setExpandedLog(isExpanded ? null : log.id)}
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="px-1.5 py-0.5 text-[10px] font-medium text-[#666] bg-[#E5E5E5] rounded">
                          {log.trigger}
                        </span>
                        <span className="text-[12px] text-[#999]">{formatTimeAgo(log.created_at)}</span>
                        {log.action_summary && (
                          <span className="text-[12px] text-[#333] flex-1">{log.action_summary}</span>
                        )}
                        {log.profile_completeness_before != null && log.profile_completeness_after != null && (
                          <span className="text-[11px] font-medium text-[#3FAF7A]">
                            {log.profile_completeness_before}% → {log.profile_completeness_after}%
                          </span>
                        )}
                        <ChevronRight className={`w-3.5 h-3.5 text-[#999] transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                      </div>

                      {isExpanded && (
                        <div className="mt-3 pt-3 border-t border-[#E5E5E5] space-y-2">
                          {log.observation && (
                            <div>
                              <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">Observation</p>
                              <p className="text-[12px] text-[#666] mt-0.5">{log.observation}</p>
                            </div>
                          )}
                          {log.thinking && (
                            <div>
                              <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">Thinking</p>
                              <p className="text-[12px] text-[#666] mt-0.5">{log.thinking}</p>
                            </div>
                          )}
                          {log.decision && (
                            <div>
                              <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">Decision</p>
                              <p className="text-[12px] text-[#666] mt-0.5">{log.decision}</p>
                            </div>
                          )}
                          {log.tools_called && log.tools_called.length > 0 && (
                            <div>
                              <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Tools Called</p>
                              <div className="flex flex-wrap gap-1">
                                {log.tools_called.map((tc, j) => (
                                  <span key={j} className="bg-white rounded-lg px-2 py-1 text-[11px] text-[#666] border border-[#E5E5E5]">
                                    {tc.tool}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                          {log.error_message && (
                            <div>
                              <p className="text-[11px] text-red-500 font-medium">Error: {log.error_message}</p>
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
        )}
      </div>
    </div>
  )
}
