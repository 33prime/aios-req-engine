/**
 * RequirementsIntelligenceTab - Strategic requirements gathering advisor
 *
 * Shows gap analysis, suggested sources, stakeholder intelligence,
 * and tribal knowledge to guide consultants in gathering requirements.
 */

'use client'

import {
  AlertCircle,
  CheckCircle,
  FileText,
  Database,
  Mic,
  Package,
  MessageSquare,
  Users,
  Lightbulb,
  Star,
} from 'lucide-react'
import type { RequirementsIntelligenceResponse } from '@/lib/api'

interface RequirementsIntelligenceTabProps {
  data: RequirementsIntelligenceResponse | null
  isLoading: boolean
}

export function RequirementsIntelligenceTab({ data, isLoading }: RequirementsIntelligenceTabProps) {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
        <p className="text-xs text-[#999999]">Analyzing project intelligence...</p>
      </div>
    )
  }

  if (!data) {
    return (
      <p className="text-sm text-[#999999] text-center py-8">
        Unable to load intelligence data.
      </p>
    )
  }

  const hasGaps = data.information_gaps.length > 0

  if (!hasGaps && data.suggested_sources.length === 0 && data.tribal_knowledge.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-2">
        <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center">
          <CheckCircle className="w-5 h-5 text-emerald-500" />
        </div>
        <p className="text-sm font-medium text-[#333333]">No significant gaps detected</p>
        <p className="text-xs text-[#999999] text-center max-w-[240px]">
          Your project has strong coverage across all areas.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* A. Summary Banner */}
      <SummaryBanner data={data} />

      {/* B. Information Gaps */}
      {data.information_gaps.length > 0 && (
        <InformationGapsSection gaps={data.information_gaps} />
      )}

      {/* C. Suggested Sources */}
      {data.suggested_sources.length > 0 && (
        <SuggestedSourcesSection sources={data.suggested_sources} />
      )}

      {/* D. Stakeholder Intelligence */}
      {data.stakeholder_intelligence.length > 0 && (
        <StakeholderIntelligenceSection stakeholders={data.stakeholder_intelligence} counts={data.counts} />
      )}

      {/* E. Tribal Knowledge */}
      {data.tribal_knowledge.length > 0 && (
        <TribalKnowledgeSection items={data.tribal_knowledge} />
      )}
    </div>
  )
}

// =============================================================================
// A. Summary Banner
// =============================================================================

function SummaryBanner({ data }: { data: RequirementsIntelligenceResponse }) {
  const readinessPercent = Math.round(data.total_readiness * 100)
  const phaseLabel = data.phase.charAt(0).toUpperCase() + data.phase.slice(1)

  return (
    <div className="flex items-center gap-3 bg-[#F9F9F9] rounded-lg px-3 py-2.5">
      <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-teal-50 text-teal-700 uppercase tracking-wide">
        {phaseLabel}
      </span>
      <div className="flex items-center gap-1.5">
        <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#3FAF7A] rounded-full transition-all"
            style={{ width: `${readinessPercent}%` }}
          />
        </div>
        <span className="text-[11px] font-medium text-[#333333]">{readinessPercent}%</span>
      </div>
      <span className="text-[11px] text-[#999999] flex-1 text-right truncate">
        {data.summary}
      </span>
    </div>
  )
}

// =============================================================================
// B. Information Gaps
// =============================================================================

const SEVERITY_STYLES: Record<string, { dot: string; label: string }> = {
  critical: { dot: 'bg-red-500', label: 'Critical' },
  high: { dot: 'bg-amber-500', label: 'High' },
  medium: { dot: 'bg-yellow-400', label: 'Medium' },
  low: { dot: 'bg-gray-300', label: 'Low' },
}

function InformationGapsSection({ gaps }: { gaps: RequirementsIntelligenceResponse['information_gaps'] }) {
  const severityCounts = gaps.reduce<Record<string, number>>((acc, g) => {
    acc[g.severity] = (acc[g.severity] || 0) + 1
    return acc
  }, {})

  const severitySummary = Object.entries(severityCounts)
    .filter(([, count]) => count > 0)
    .map(([sev, count]) => `${count} ${sev}`)
    .join(', ')

  return (
    <div>
      <SectionHeader
        title="Information Gaps"
        right={<span className="text-[11px] text-[#999999]">{severitySummary}</span>}
      />
      <div className="space-y-2">
        {gaps.map((gap) => {
          const style = SEVERITY_STYLES[gap.severity] || SEVERITY_STYLES.medium
          const isFoundation = gap.gap_type === 'foundation'
          return (
            <div key={gap.id} className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2.5">
              <div className="flex items-start gap-2">
                <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${style.dot}`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <h5 className="text-sm font-medium text-[#333333]">{gap.title}</h5>
                    {isFoundation && (
                      <span className="px-1.5 py-0.5 text-[9px] font-medium rounded bg-teal-50 text-teal-700">
                        Foundation
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-[#333333] mt-0.5">{gap.description}</p>
                  {gap.how_to_fix && (
                    <p className="text-[11px] text-[#999999] italic mt-1">
                      How to fix: {gap.how_to_fix}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// =============================================================================
// C. Suggested Sources
// =============================================================================

const SOURCE_TYPE_ICONS: Record<string, typeof FileText> = {
  document: FileText,
  data_export: Database,
  recording: Mic,
  artifact: Package,
}

const PRIORITY_DOT: Record<string, string> = {
  high: 'bg-emerald-500',
  medium: 'bg-teal-400',
  low: 'bg-gray-300',
}

function SuggestedSourcesSection({ sources }: { sources: RequirementsIntelligenceResponse['suggested_sources'] }) {
  return (
    <div>
      <SectionHeader
        title="Suggested Sources"
        right={<span className="text-[11px] text-[#999999]">Key documents and artifacts to pursue</span>}
      />
      <div className="grid grid-cols-2 gap-2">
        {sources.map((src, i) => {
          const Icon = SOURCE_TYPE_ICONS[src.source_type] || FileText
          const priorityDot = PRIORITY_DOT[src.priority] || PRIORITY_DOT.medium
          return (
            <div key={i} className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2.5">
              <div className="flex items-start gap-2">
                <div className="w-6 h-6 rounded bg-teal-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon className="w-3 h-3 text-teal-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <h5 className="text-xs font-medium text-[#333333] leading-tight">{src.title}</h5>
                  <p className="text-[11px] text-[#333333] mt-0.5">{src.description}</p>
                  <p className="text-[11px] text-teal-600 italic mt-1">{src.why_valuable}</p>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-600">
                      {src.likely_owner_role}
                    </span>
                    <div className={`w-1.5 h-1.5 rounded-full ${priorityDot}`} title={`${src.priority} priority`} />
                    {src.related_gaps.map((gapId) => (
                      <span
                        key={gapId}
                        className="px-1 py-0.5 text-[9px] rounded bg-gray-50 text-gray-400 border border-gray-200"
                      >
                        {gapId.split(':')[1]?.replace(/_/g, ' ') || gapId}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// =============================================================================
// D. Stakeholder Intelligence
// =============================================================================

const TYPE_BADGE_STYLES: Record<string, string> = {
  champion: 'bg-emerald-50 text-emerald-700',
  sponsor: 'bg-teal-50 text-teal-700',
  blocker: 'bg-gray-100 text-gray-600',
  influencer: 'bg-teal-50 text-teal-600',
  end_user: 'bg-gray-100 text-gray-500',
}

function StakeholderIntelligenceSection({
  stakeholders,
  counts,
}: {
  stakeholders: RequirementsIntelligenceResponse['stakeholder_intelligence']
  counts: RequirementsIntelligenceResponse['counts']
}) {
  const known = stakeholders.filter((s) => s.is_known)
  const suggested = stakeholders.filter((s) => !s.is_known)

  return (
    <div>
      <SectionHeader
        title="Who Knows What"
        right={
          <span className="text-[11px] text-[#999999]">
            {counts.stakeholders_known} known, {counts.stakeholders_suggested} suggested
          </span>
        }
      />
      <div className="space-y-3">
        {/* Known Stakeholders */}
        {known.length > 0 && (
          <div className="space-y-2">
            {known.map((s, i) => {
              const initials = (s.name || 'U')
                .split(' ')
                .map((w) => w[0])
                .join('')
                .slice(0, 2)
                .toUpperCase()
              const typeBadge = s.stakeholder_type
                ? TYPE_BADGE_STYLES[s.stakeholder_type] || 'bg-gray-100 text-gray-600'
                : null
              return (
                <div key={s.stakeholder_id || i} className="bg-[#F9F9F9] rounded-lg px-3 py-2.5">
                  <div className="flex items-start gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-teal-50 flex items-center justify-center flex-shrink-0">
                      <span className="text-[11px] font-semibold text-teal-600">{initials}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium text-[#333333]">{s.name || 'Unknown'}</span>
                        {s.is_primary_contact && (
                          <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
                        )}
                        {typeBadge && s.stakeholder_type && (
                          <span className={`px-1.5 py-0.5 text-[9px] font-medium rounded ${typeBadge}`}>
                            {s.stakeholder_type.replace(/_/g, ' ')}
                          </span>
                        )}
                        {s.influence_level && (
                          <span className="text-[9px] text-[#999999]">
                            {s.influence_level} influence
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-[#999999] mt-0.5">
                        {s.role}
                        {s.organization && ` · ${s.organization}`}
                      </p>
                      {s.likely_knowledge.length > 0 && (
                        <p className="text-[11px] text-[#333333] mt-1">
                          <span className="text-[#999999]">Likely knows about: </span>
                          {s.likely_knowledge.join(', ')}
                        </p>
                      )}
                      {s.engagement_tip && (
                        <p className="text-[10px] text-[#999999] italic mt-1">{s.engagement_tip}</p>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Suggested Roles */}
        {suggested.length > 0 && (
          <div className="space-y-2">
            {suggested.map((s, i) => (
              <div key={i} className="border border-dashed border-gray-300 rounded-lg px-3 py-2.5">
                <div className="flex items-start gap-2.5">
                  <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                    <Users className="w-3.5 h-3.5 text-gray-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-[#333333]">{s.role}</span>
                      <span className="text-[9px] text-[#999999] italic">Not yet identified</span>
                    </div>
                    {s.likely_knowledge.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {s.likely_knowledge.map((topic, j) => (
                          <span key={j} className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-600">
                            {topic}
                          </span>
                        ))}
                      </div>
                    )}
                    {s.engagement_tip && (
                      <p className="text-[11px] text-[#333333] mt-1">{s.engagement_tip}</p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// E. Tribal Knowledge
// =============================================================================

function TribalKnowledgeSection({ items }: { items: RequirementsIntelligenceResponse['tribal_knowledge'] }) {
  return (
    <div>
      <SectionHeader
        title="Conversations to Have"
        right={<span className="text-[11px] text-[#999999]">Knowledge that only comes from people</span>}
      />
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="bg-gray-50 border border-gray-100 rounded-lg px-3 py-2.5">
            <div className="flex items-start gap-2">
              <MessageSquare className="w-3.5 h-3.5 text-teal-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <h5 className="text-xs font-medium text-[#333333]">{item.title}</h5>
                <p className="text-[11px] text-[#333333] mt-0.5">{item.description}</p>
                <p className="text-[10px] text-[#999999] italic mt-1">{item.why_undocumented}</p>
                <div className="mt-1.5">
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-600">
                    Best asked of: {item.best_asked_of}
                  </span>
                </div>
                {item.conversation_starters.length > 0 && (
                  <ul className="mt-2 space-y-1">
                    {item.conversation_starters.map((starter, j) => (
                      <li key={j} className="text-[11px] text-[#333333] pl-2 border-l-2 border-teal-200">
                        &ldquo;{starter}&rdquo;
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Shared
// =============================================================================

function SectionHeader({ title, right }: { title: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-2.5">
      <h4 className="text-xs font-semibold text-[#333333] uppercase tracking-wide">{title}</h4>
      {typeof right === 'string' ? (
        <span className="text-[11px] text-[#999999]">{right}</span>
      ) : (
        right
      )}
    </div>
  )
}
