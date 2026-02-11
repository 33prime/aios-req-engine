'use client'

import { User } from 'lucide-react'
import type { StakeholderDetail, ResolvedStakeholderRef, ResolvedPersonaRef } from '@/types/workspace'

interface StakeholderOverviewTabProps {
  stakeholder: StakeholderDetail
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

function StakeholderAvatar({ name, size = 'sm' }: { name: string; size?: 'sm' | 'md' }) {
  const initial = name[0]?.toUpperCase() || '?'
  const dim = size === 'sm' ? 'w-7 h-7 text-[10px]' : 'w-9 h-9 text-[12px]'
  return (
    <div className={`${dim} rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center text-white font-medium flex-shrink-0`}>
      {initial}
    </div>
  )
}

function PersonRef({ person }: { person: ResolvedStakeholderRef }) {
  return (
    <div className="flex items-center gap-2.5">
      <StakeholderAvatar name={person.name} />
      <span className="text-[13px] text-[#333] font-medium">{person.name}</span>
      {person.role && <span className="text-[11px] text-[#999]">{person.role}</span>}
    </div>
  )
}

export function StakeholderOverviewTab({ stakeholder }: StakeholderOverviewTabProps) {
  const s = stakeholder
  const commPrefs = s.communication_preferences
  const commPrefStr = commPrefs
    ? Object.entries(commPrefs).map(([k, v]) => `${v}`).join(', ')
    : null

  return (
    <div className="grid grid-cols-[1fr_340px] gap-6">
      {/* LEFT COLUMN */}
      <div className="space-y-6">
        {/* Contact & Identity */}
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <SectionLabel>Contact & Identity</SectionLabel>
          <div className="grid grid-cols-2 gap-x-6 gap-y-4">
            <FieldRow label="Email">
              {s.email ? (
                <a href={`mailto:${s.email}`} className="text-[#3FAF7A] hover:text-[#25785A] hover:underline transition-colors">{s.email}</a>
              ) : (
                <span className="text-[#BBB] italic">Not set</span>
              )}
            </FieldRow>
            <FieldRow label="Phone">
              {s.phone || <span className="text-[#BBB] italic">Not set</span>}
            </FieldRow>
            <FieldRow label="Organization">
              {s.organization || <span className="text-[#BBB] italic">Not set</span>}
            </FieldRow>
            <FieldRow label="LinkedIn">
              {s.linkedin_profile ? (
                <a href={s.linkedin_profile} target="_blank" rel="noopener noreferrer" className="text-[#3FAF7A] hover:text-[#25785A] hover:underline transition-colors truncate block">
                  {s.linkedin_profile.replace(/^https?:\/\/(www\.)?/, '')}
                </a>
              ) : (
                <span className="text-[#BBB] italic">Not set</span>
              )}
            </FieldRow>
            <FieldRow label="Source">
              {s.source_type ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-gray-100 text-[#666]">
                  {s.source_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
              ) : (
                <span className="text-[#BBB] italic">Unknown</span>
              )}
            </FieldRow>
            <FieldRow label="Communication Pref">
              {commPrefStr || s.preferred_channel || <span className="text-[#BBB] italic">Not set</span>}
            </FieldRow>
          </div>
        </div>

        {/* Domain Expertise */}
        {s.domain_expertise && s.domain_expertise.length > 0 && (
          <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
            <SectionLabel>Domain Expertise</SectionLabel>
            <div className="flex flex-wrap gap-2">
              {s.domain_expertise.map((area, i) => (
                <span key={i} className="px-3 py-1 rounded-full text-[12px] font-medium bg-[#3FAF7A]/10 text-[#3FAF7A]">
                  {area}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Priorities & Concerns */}
        {((s.priorities && s.priorities.length > 0) || (s.concerns && s.concerns.length > 0)) && (
          <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
            <div className="grid grid-cols-2 gap-8">
              {s.priorities && s.priorities.length > 0 && (
                <div>
                  <SectionLabel>Priorities</SectionLabel>
                  <ul className="space-y-2.5">
                    {s.priorities.map((p, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-[13px] text-[#666]">
                        <span className="text-[#3FAF7A] mt-0.5 text-lg leading-none">&bull;</span>
                        <span>{p}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {s.concerns && s.concerns.length > 0 && (
                <div>
                  <SectionLabel>Concerns</SectionLabel>
                  <ul className="space-y-2.5">
                    {s.concerns.map((c, i) => (
                      <li key={i} className="flex items-start gap-2.5 text-[13px] text-[#666]">
                        <span className="text-[#0A1E2F]/40 mt-0.5 text-lg leading-none">&bull;</span>
                        <span>{c}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Notes */}
        {s.notes && (
          <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
            <SectionLabel>Notes</SectionLabel>
            <p className="text-[14px] text-[#666] leading-relaxed whitespace-pre-wrap">{s.notes}</p>
          </div>
        )}
      </div>

      {/* RIGHT COLUMN */}
      <div className="space-y-6">
        {/* Decision Scope */}
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <SectionLabel>Decision Scope</SectionLabel>
          <div className="space-y-4">
            <div>
              <p className="text-[11px] text-[#BBB] mb-1">Authority</p>
              <p className="text-[13px] text-[#666]">
                {s.decision_authority || <span className="italic text-[#BBB]">Not assessed</span>}
              </p>
            </div>
            {s.approval_required_for && s.approval_required_for.length > 0 && (
              <div>
                <p className="text-[11px] text-[#BBB] mb-1.5">Approval Required For</p>
                <div className="flex flex-wrap gap-1.5">
                  {s.approval_required_for.map((item, i) => (
                    <span key={i} className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#3FAF7A]/10 text-[#25785A]">{item}</span>
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

        {/* Requirement Connections */}
        {((s.linked_features && s.linked_features.length > 0) || (s.linked_drivers && s.linked_drivers.length > 0)) && (
          <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
            <SectionLabel>Requirement Connections</SectionLabel>
            {s.linked_features && s.linked_features.length > 0 && (
              <div className="space-y-1">
                {s.linked_features.map((f) => (
                  <div key={f.id} className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl hover:bg-[#3FAF7A]/[0.06] transition-colors cursor-pointer">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#3FAF7A] flex-shrink-0" />
                    <span className="text-[13px] font-medium text-[#333] flex-1 truncate">{f.name}</span>
                    {f.priority_group && (
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#3FAF7A]/10 text-[#25785A] font-medium">
                        {MOSCOW_LABEL[f.priority_group] || f.priority_group}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
            {s.linked_drivers && s.linked_drivers.length > 0 && (
              <>
                <div className="mt-4 pt-4 border-t border-[#E5E5E5]">
                  <p className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-3">Business Drivers</p>
                  <div className="space-y-1">
                    {s.linked_drivers.map((d) => (
                      <div key={d.id} className="flex items-center gap-2.5 px-2.5 py-2 rounded-xl hover:bg-[#3FAF7A]/[0.06] transition-colors cursor-pointer">
                        <div className="w-1.5 h-1.5 rounded-full bg-[#0A1E2F]/30 flex-shrink-0" />
                        <span className="text-[13px] text-[#666] flex-1 truncate">{d.description}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-[#0A1E2F]/10 text-[#0A1E2F] font-medium">
                          {DRIVER_TYPE_LABEL[d.driver_type] || d.driver_type}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Relationships */}
        {(s.reports_to || (s.allies_resolved && s.allies_resolved.length > 0) || (s.potential_blockers_resolved && s.potential_blockers_resolved.length > 0)) && (
          <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
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
                    {s.potential_blockers_resolved.map((blocker) => (
                      <div key={blocker.id} className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-full bg-gradient-to-br from-gray-400 to-gray-500 flex items-center justify-center text-white text-[10px] font-medium flex-shrink-0">
                          {blocker.name[0]?.toUpperCase() || '?'}
                        </div>
                        <span className="text-[13px] text-[#333] font-medium">{blocker.name}</span>
                        {blocker.role && <span className="text-[11px] text-[#999]">{blocker.role}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Linked Persona */}
        {s.linked_persona ? (
          <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
            <SectionLabel>Linked Persona</SectionLabel>
            <div className="flex items-center gap-3 p-3 bg-[#F4F4F4] rounded-xl">
              <div className="w-9 h-9 rounded-xl bg-[#3FAF7A]/10 flex items-center justify-center">
                <User className="w-4 h-4 text-[#3FAF7A]" />
              </div>
              <div>
                <p className="text-[13px] font-medium text-[#333]">{s.linked_persona.name}</p>
                {s.linked_persona.role && (
                  <p className="text-[11px] text-[#999]">{s.linked_persona.role}</p>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
            <SectionLabel>Linked Persona</SectionLabel>
            <div className="flex items-center gap-3 p-3 bg-[#F4F4F4] rounded-xl">
              <div className="w-9 h-9 rounded-xl bg-gray-100 flex items-center justify-center">
                <User className="w-4 h-4 text-[#BBB]" />
              </div>
              <p className="text-[13px] text-[#999] italic">No linked persona</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
