'use client'

import { useState, useEffect } from 'react'
import { User, Clock } from 'lucide-react'
import type {
  StakeholderDetail,
  StakeholderIntelligenceProfile,
  ResolvedStakeholderRef,
} from '@/types/workspace'
import { getStakeholderEvidence } from '@/lib/api'

interface StakeholderProfileProps {
  stakeholder: StakeholderDetail
  intelligence: StakeholderIntelligenceProfile | null
  projectId: string
}

const MOSCOW_LABEL: Record<string, string> = {
  must_have: 'Must Have',
  should_have: 'Should Have',
  could_have: 'Could Have',
  out_of_scope: 'Out of Scope',
}

const DRIVER_TYPE_LABEL: Record<string, string> = {
  pain: 'Pain',
  goal: 'Goal',
  kpi: 'KPI',
}

const SECTION_LABELS: Record<string, { label: string; max: number }> = {
  core_identity: { label: 'Identity', max: 10 },
  engagement_profile: { label: 'Engagement', max: 20 },
  decision_authority: { label: 'Decision', max: 20 },
  relationships: { label: 'Relationships', max: 20 },
  communication: { label: 'Communication', max: 10 },
  win_conditions_concerns: { label: 'Win Conditions', max: 15 },
  evidence_depth: { label: 'Evidence', max: 5 },
}

const ENGAGEMENT_STYLE: Record<string, string> = {
  highly_engaged: 'bg-[#E8F5E9] text-[#25785A]',
  moderately_engaged: 'bg-[#E8F5E9] text-[#25785A]',
  neutral: 'bg-[#F0F0F0] text-[#666]',
  disengaged: 'bg-[#FEE2E2] text-[#991B1B]',
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-4">
      {children}
    </h3>
  )
}

function FieldRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[11px] text-[#BBB] mb-0.5">{label}</p>
      <div className="text-[13px] text-[#333]">{children}</div>
    </div>
  )
}

function PersonRef({ person, variant = 'default' }: { person: ResolvedStakeholderRef; variant?: 'default' | 'blocker' }) {
  const initial = person.name[0]?.toUpperCase() || '?'
  const bg = variant === 'blocker'
    ? 'bg-gradient-to-br from-gray-400 to-gray-500'
    : 'bg-gradient-to-br from-brand-primary to-[#25785A]'
  return (
    <div className="flex items-center gap-2.5">
      <div className={`w-7 h-7 rounded-full ${bg} flex items-center justify-center text-white text-[10px] font-medium flex-shrink-0`}>
        {initial}
      </div>
      <span className="text-[13px] text-[#333] font-medium">{person.name}</span>
      {person.role && <span className="text-[11px] text-[#999]">{person.role}</span>}
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
  if (days < 30) return `${days}d ago`
  return `${Math.floor(days / 7)}w ago`
}

// =============================================================================
// Recent Activity section
// =============================================================================

interface ActivityItem {
  text: string
  type: string
  date: string
}

function RecentActivity({ projectId, stakeholderId }: { projectId: string; stakeholderId: string }) {
  const [items, setItems] = useState<ActivityItem[]>([])

  useEffect(() => {
    if (!projectId || !stakeholderId) return
    getStakeholderEvidence(projectId, stakeholderId)
      .then((data) => {
        const activity: ActivityItem[] = []

        // Source signals → "Mentioned in X"
        for (const sig of (data.source_signals || []).slice(0, 5)) {
          const label = sig.title || sig.source_label || sig.signal_type || 'signal'
          const type = sig.signal_type || 'document'
          activity.push({
            text: `Mentioned in "${label}"`,
            type,
            date: sig.created_at || '',
          })
        }

        // Enrichment history → "Profile updated"
        for (const rev of (data.enrichment_history || []).slice(0, 3)) {
          const summary = rev.diff_summary || 'Profile updated'
          activity.push({
            text: summary,
            type: 'enrichment',
            date: rev.created_at || '',
          })
        }

        // Sort by date descending, take top 6
        activity.sort((a, b) => {
          if (!a.date || !b.date) return 0
          return new Date(b.date).getTime() - new Date(a.date).getTime()
        })
        setItems(activity.slice(0, 6))
      })
      .catch(() => {})
  }, [projectId, stakeholderId])

  if (items.length === 0) return null

  const TYPE_LABELS: Record<string, string> = {
    transcript: 'Transcript',
    email: 'Email',
    document: 'Document',
    research: 'Research',
    note: 'Note',
    enrichment: 'Enrichment',
  }

  return (
    <div className="bg-white border border-border rounded-2xl shadow-sm p-6 mt-6">
      <SectionLabel>Recent Activity</SectionLabel>
      <div className="space-y-2">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-3 py-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-brand-primary flex-shrink-0" />
            <span className="text-[13px] text-[#333] flex-1 truncate">{item.text}</span>
            <span className="px-2 py-0.5 text-[10px] font-medium text-[#666] bg-[#F0F0F0] rounded flex-shrink-0">
              {TYPE_LABELS[item.type] || item.type}
            </span>
            {item.date && (
              <span className="text-[11px] text-[#999] flex-shrink-0">
                {formatTimeAgo(item.date)}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Main Profile Component
// =============================================================================

export function StakeholderProfile({ stakeholder: s, intelligence, projectId }: StakeholderProfileProps) {
  const commPrefs = s.communication_preferences
  const commPrefStr = commPrefs
    ? Object.entries(commPrefs).map(([, v]) => `${v}`).join(', ')
    : null

  const isKeyPerson = ['champion', 'sponsor', 'blocker'].includes(s.stakeholder_type || '')

  return (
    <>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6">
        {/* LEFT COLUMN */}
        <div className="space-y-6">
          {/* Contact & Identity */}
          {(s.email || s.phone || s.organization || s.linkedin_profile || commPrefStr || s.preferred_channel || s.source_type) && (
          <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
            <SectionLabel>Contact & Identity</SectionLabel>
            <div className="grid grid-cols-2 gap-x-6 gap-y-4">
              {s.email && (
                <FieldRow label="Email">
                  <a href={`mailto:${s.email}`} className="text-brand-primary hover:underline">{s.email}</a>
                </FieldRow>
              )}
              {s.phone && (
                <FieldRow label="Phone">{s.phone}</FieldRow>
              )}
              {s.organization && (
                <FieldRow label="Organization">{s.organization}</FieldRow>
              )}
              {s.linkedin_profile && (
                <FieldRow label="LinkedIn">
                  <a href={s.linkedin_profile} target="_blank" rel="noopener noreferrer" className="text-brand-primary hover:underline truncate block">
                    {s.linkedin_profile.replace(/^https?:\/\/(www\.)?/, '')}
                  </a>
                </FieldRow>
              )}
              {(commPrefStr || s.preferred_channel) && (
                <FieldRow label="Communication">
                  {commPrefStr || s.preferred_channel}
                </FieldRow>
              )}
              {s.source_type && (
                <FieldRow label="Source">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-100 text-[#666]">
                    {s.source_type.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
                  </span>
                </FieldRow>
              )}
            </div>
          </div>
          )}

          {/* Domain Expertise */}
          {s.domain_expertise && s.domain_expertise.length > 0 && (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>Domain Expertise</SectionLabel>
              <div className="flex flex-wrap gap-2">
                {s.domain_expertise.map((area, i) => (
                  <span key={i} className="px-3 py-1 rounded-full text-[12px] font-medium bg-brand-primary-light text-brand-primary">
                    {area}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Engagement & Communication — AI enriched (show for key people) */}
          {isKeyPerson && (s.engagement_level || s.engagement_strategy || s.risk_if_disengaged) && (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>Engagement Intelligence</SectionLabel>
              <div className="grid grid-cols-2 gap-4">
                {s.engagement_level && (
                  <div>
                    <p className="text-[11px] text-[#BBB] mb-1">Engagement Level</p>
                    <span className={`inline-flex px-2.5 py-0.5 rounded-full text-[11px] font-medium ${ENGAGEMENT_STYLE[s.engagement_level] || 'bg-[#F0F0F0] text-[#666]'}`}>
                      {s.engagement_level.replace(/_/g, ' ')}
                    </span>
                  </div>
                )}
                {s.engagement_strategy && (
                  <div className="col-span-2">
                    <p className="text-[11px] text-[#BBB] mb-1">Strategy</p>
                    <p className="text-[13px] text-[#666]">{s.engagement_strategy}</p>
                  </div>
                )}
                {s.risk_if_disengaged && (
                  <div className="col-span-2">
                    <p className="text-[11px] text-[#BBB] mb-1">Risk if Disengaged</p>
                    <p className="text-[13px] text-[#666]">{s.risk_if_disengaged}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* What They Care About — merged priorities/concerns + win conditions/key concerns */}
          {((s.priorities?.length) || (s.concerns?.length) || (s.win_conditions?.length) || (s.key_concerns?.length)) ? (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>What They Care About</SectionLabel>
              <div className="grid grid-cols-2 gap-8">
                {/* Positive — priorities + win conditions */}
                <div>
                  {s.priorities && s.priorities.length > 0 && (
                    <div className="mb-4">
                      <p className="text-[11px] text-[#BBB] mb-2">Priorities</p>
                      <ul className="space-y-2">
                        {s.priorities.map((p, i) => (
                          <li key={i} className="flex items-start gap-2 text-[13px] text-[#666]">
                            <span className="text-brand-primary mt-0.5">&bull;</span>
                            <span>{p}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {s.win_conditions && s.win_conditions.length > 0 && (
                    <div>
                      <p className="text-[11px] text-[#BBB] mb-2">Win Conditions</p>
                      <ul className="space-y-2">
                        {s.win_conditions.map((w, i) => (
                          <li key={i} className="flex items-start gap-2 text-[13px] text-[#25785A]">
                            <span className="mt-0.5">&bull;</span>
                            <span>{w}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
                {/* Negative — concerns + key concerns */}
                <div>
                  {s.concerns && s.concerns.length > 0 && (
                    <div className="mb-4">
                      <p className="text-[11px] text-[#BBB] mb-2">Concerns</p>
                      <ul className="space-y-2">
                        {s.concerns.map((c, i) => (
                          <li key={i} className="flex items-start gap-2 text-[13px] text-[#666]">
                            <span className="text-[#999] mt-0.5">&bull;</span>
                            <span>{c}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {s.key_concerns && s.key_concerns.length > 0 && (
                    <div>
                      <p className="text-[11px] text-[#BBB] mb-2">Key Concerns</p>
                      <ul className="space-y-2">
                        {s.key_concerns.map((c, i) => (
                          <li key={i} className="flex items-start gap-2 text-[13px] text-[#991B1B]">
                            <span className="mt-0.5">&bull;</span>
                            <span>{c}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : null}

          {/* Notes */}
          {s.notes && (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>Notes</SectionLabel>
              <p className="text-[14px] text-[#666] leading-relaxed whitespace-pre-wrap">{s.notes}</p>
            </div>
          )}
        </div>

        {/* RIGHT COLUMN */}
        <div className="space-y-6">
          {/* Decision Scope */}
          {(s.decision_authority || (s.approval_required_for?.length) || (s.veto_power_over?.length)) ? (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>Decision Scope</SectionLabel>
              <div className="space-y-4">
                {s.decision_authority && (
                  <div>
                    <p className="text-[11px] text-[#BBB] mb-1">Authority</p>
                    <p className="text-[13px] text-[#666]">{s.decision_authority}</p>
                  </div>
                )}
                {s.approval_required_for && s.approval_required_for.length > 0 && (
                  <div>
                    <p className="text-[11px] text-[#BBB] mb-1.5">Approval Required For</p>
                    <div className="flex flex-wrap gap-1.5">
                      {s.approval_required_for.map((item, i) => (
                        <span key={i} className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-brand-primary-light text-[#25785A]">{item}</span>
                      ))}
                    </div>
                  </div>
                )}
                {s.veto_power_over && s.veto_power_over.length > 0 && (
                  <div>
                    <p className="text-[11px] text-[#BBB] mb-1.5">Veto Power Over</p>
                    <div className="flex flex-wrap gap-1.5">
                      {s.veto_power_over.map((item, i) => (
                        <span key={i} className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#0A1E2F]/10 text-[#0A1E2F]">{item}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {/* Relationships */}
          {(s.reports_to || s.allies_resolved?.length || s.potential_blockers_resolved?.length) ? (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>Relationships</SectionLabel>
              <div className="space-y-4">
                {s.reports_to && (
                  <div>
                    <p className="text-[11px] text-[#BBB] mb-2">Reports To</p>
                    <PersonRef person={s.reports_to} />
                  </div>
                )}
                {s.allies_resolved && s.allies_resolved.length > 0 && (
                  <div>
                    <p className="text-[11px] text-[#BBB] mb-2">Allies</p>
                    <div className="space-y-2">
                      {s.allies_resolved.map((ally) => (
                        <PersonRef key={ally.id} person={ally} />
                      ))}
                    </div>
                  </div>
                )}
                {s.potential_blockers_resolved && s.potential_blockers_resolved.length > 0 && (
                  <div>
                    <p className="text-[11px] text-[#BBB] mb-2">Potential Blockers</p>
                    <div className="space-y-2">
                      {s.potential_blockers_resolved.map((b) => (
                        <PersonRef key={b.id} person={b} variant="blocker" />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : null}

          {/* Requirement Connections */}
          {(s.linked_features?.length || s.linked_drivers?.length) ? (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>Requirement Connections</SectionLabel>
              {s.linked_features && s.linked_features.length > 0 && (
                <div className="space-y-1">
                  {s.linked_features.map((f) => (
                    <div key={f.id} className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl hover:bg-brand-primary/[0.06] transition-colors">
                      <div className="w-1.5 h-1.5 rounded-full bg-brand-primary flex-shrink-0" />
                      <span className="text-[13px] font-medium text-[#333] flex-1 truncate">{f.name}</span>
                      {f.priority_group && (
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-brand-primary-light text-[#25785A] font-medium">
                          {MOSCOW_LABEL[f.priority_group] || f.priority_group}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {s.linked_drivers && s.linked_drivers.length > 0 && (
                <div className="mt-4 pt-4 border-t border-border">
                  <p className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-3">Business Drivers</p>
                  <div className="space-y-1">
                    {s.linked_drivers.map((d) => (
                      <div key={d.id} className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl hover:bg-brand-primary/[0.06] transition-colors">
                        <div className="w-1.5 h-1.5 rounded-full bg-[#0A1E2F]/30 flex-shrink-0" />
                        <span className="text-[13px] text-[#666] flex-1 truncate">{d.description}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#0A1E2F]/10 text-[#0A1E2F] font-medium">
                          {DRIVER_TYPE_LABEL[d.driver_type] || d.driver_type}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}

          {/* Profile Gaps — section completeness bars */}
          {intelligence && intelligence.profile_completeness > 0 && (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>Profile Gaps</SectionLabel>
              <p className="text-[12px] text-[#999] mb-3">
                Click Analyze to fill the weakest section.
              </p>
              <div className="space-y-2">
                {intelligence.sections?.map((section) => {
                  const config = SECTION_LABELS[section.section]
                  if (!config) return null
                  const pct = config.max > 0 ? Math.min(100, (section.score / config.max) * 100) : 0
                  return (
                    <div key={section.section} className="flex items-center gap-3">
                      <span className="text-[11px] text-[#666] w-24 flex-shrink-0">{config.label}</span>
                      <div className="flex-1 h-1.5 bg-[#F0F0F0] rounded-full overflow-hidden">
                        <div className="h-full bg-brand-primary rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                      <span className="text-[10px] text-[#999] w-8 text-right">{section.score}/{config.max}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Linked Persona */}
          {s.linked_persona && (
            <div className="bg-white border border-border rounded-2xl shadow-sm p-6">
              <SectionLabel>Linked Persona</SectionLabel>
              <div className="flex items-center gap-3 p-3 bg-[#F4F4F4] rounded-xl">
                <div className="w-9 h-9 rounded-xl bg-brand-primary-light flex items-center justify-center">
                  <User className="w-4 h-4 text-brand-primary" />
                </div>
                <div>
                  <p className="text-[13px] font-medium text-[#333]">{s.linked_persona.name}</p>
                  {s.linked_persona.role && (
                    <p className="text-[11px] text-[#999]">{s.linked_persona.role}</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent Activity — full width below the two columns */}
      <RecentActivity projectId={projectId} stakeholderId={s.id} />
    </>
  )
}
