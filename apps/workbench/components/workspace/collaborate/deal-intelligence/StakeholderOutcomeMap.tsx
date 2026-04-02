'use client'

import { useMemo, useState, useCallback } from 'react'
import { Users, AlertCircle, Plus, Loader2 } from 'lucide-react'
import { useProjectStakeholders, useOutcomesTab, useBRDData } from '@/lib/hooks/use-api'
import { createStakeholder } from '@/lib/api/workspace'
import { CollapsibleSection } from '../CollapsibleSection'
import type { StakeholderType, InfluenceLevel } from '@/types/workspace'

interface StakeholderOutcomeMapProps {
  projectId: string
}

// ── Types ──

interface ActorOutcomeLink {
  outcomeTitle: string
  actorTitle: string
  strengthScore: number
  status: string
  confirmed: boolean
  sharpenPrompt: string | null
}

interface MappedStakeholder {
  id: string
  name: string
  role: string | null
  stakeholderType: string | null
  influenceLevel: string | null
  winConditions: string[]
  engagementStrategy: string | null
  confirmationStatus: string | null
  keyConcerns: string[]
  linkedOutcomes: ActorOutcomeLink[]
}

interface StakeholderGroup {
  type: string
  label: string
  accentClass: string
  badgeClass: string
  emptyWarning: string | null
  stakeholders: MappedStakeholder[]
}

// ── Config ──

const GROUP_CONFIG: Array<{ type: string; label: string; accentClass: string; badgeClass: string; emptyWarning: string | null }> = [
  { type: 'champion', label: 'Champion', accentClass: 'border-l-[#3FAF7A]', badgeClass: 'bg-brand-primary-light text-[#25785A]', emptyWarning: 'No champion identified — critical for deal success' },
  { type: 'sponsor', label: 'Economic Buyer', accentClass: 'border-l-[#0A1E2F]', badgeClass: 'bg-accent/6 text-accent', emptyWarning: 'No sponsor identified — who controls budget?' },
  { type: 'influencer', label: 'Influencer', accentClass: 'border-l-[#999999]', badgeClass: 'bg-surface-subtle text-text-secondary', emptyWarning: null },
  { type: 'end_user', label: 'End Users', accentClass: 'border-l-border', badgeClass: 'bg-surface-subtle text-text-secondary', emptyWarning: null },
  { type: 'blocker', label: 'Blockers', accentClass: 'border-l-[#0A1E2F]', badgeClass: 'bg-accent/6 text-accent', emptyWarning: null },
]

// ── Subcomponents ──

function InfluenceDots({ level }: { level: string | null | undefined }) {
  const count = level === 'high' ? 3 : level === 'medium' ? 2 : level === 'low' ? 1 : 0
  return (
    <div className="flex items-center gap-0.5" title={`Influence: ${level || 'unknown'}`}>
      {[0, 1, 2].map(i => (
        <span key={i} className={`w-1.5 h-1.5 rounded-full ${i < count ? 'bg-text-secondary' : 'bg-border'}`} />
      ))}
    </div>
  )
}

function MiniStrengthRing({ score }: { score: number }) {
  const size = 28
  const r = (size / 2) - 2.5
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - score / 100)
  const color = score >= 70 ? 'var(--brand-primary, #3FAF7A)' : '#999999'

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} className="-rotate-90" style={{ width: size, height: size }}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#E5E5E5" strokeWidth={2} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={2} strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round" />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-[8px] font-bold text-text-body">{score}</span>
    </div>
  )
}

function StakeholderCard({ s, accentClass }: { s: MappedStakeholder; accentClass: string }) {
  const hasConfirmed = s.linkedOutcomes.some(o => o.confirmed)

  // Find strongest sharpen prompt
  const askPrompt = s.linkedOutcomes.find(o => o.sharpenPrompt)?.sharpenPrompt

  // Belief summary
  const totalLinked = s.linkedOutcomes.length
  const confirmedCount = s.linkedOutcomes.filter(o => o.confirmed).length
  const weakCount = s.linkedOutcomes.filter(o => o.strengthScore < 70).length
  let beliefSummary = ''
  if (totalLinked === 0) {
    beliefSummary = 'No outcomes linked yet.'
  } else if (confirmedCount === totalLinked) {
    beliefSummary = 'Fully aligned — all outcomes confirmed.'
  } else if (weakCount > 0) {
    beliefSummary = `${confirmedCount} of ${totalLinked} confirmed. ${weakCount} need${weakCount > 1 ? '' : 's'} sharpening.`
  } else {
    beliefSummary = `${confirmedCount} of ${totalLinked} confirmed.`
  }

  return (
    <div className={`border border-border ${accentClass} border-l-[3px] rounded-r-xl p-3.5 space-y-2 mb-2 transition-all hover:shadow-sm`}>
      {/* Name row */}
      <div className="flex items-center gap-2">
        <span className="text-[13px] font-semibold text-text-body">{s.name}</span>
        <InfluenceDots level={s.influenceLevel} />
        {hasConfirmed && (
          <span className="px-1.5 py-0.5 rounded-full text-[9px] font-semibold uppercase bg-brand-primary-light text-[#25785A]">
            Confirmed
          </span>
        )}
      </div>

      {/* Role */}
      {s.role && <p className="text-[12px] text-text-secondary">{s.role}</p>}

      {/* Win conditions */}
      {s.winConditions.length > 0 && (
        <p className="text-[11px] text-text-placeholder">Win: {s.winConditions[0]}</p>
      )}

      {/* Linked outcomes */}
      {s.linkedOutcomes.length > 0 && (
        <div className="space-y-1.5">
          {s.linkedOutcomes.map((o, i) => (
            <div key={i} className="flex items-center gap-2">
              <MiniStrengthRing score={o.strengthScore} />
              <div className="min-w-0">
                <span className="text-[11px] text-text-body truncate block">{o.actorTitle}</span>
                <span className="text-[10px] text-text-placeholder flex items-center gap-1">
                  <span className={`w-1 h-1 rounded-full ${o.confirmed ? 'bg-brand-primary' : 'bg-text-placeholder'}`} />
                  {o.status}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Belief summary */}
      <p className="text-[11px] text-text-placeholder italic">{beliefSummary}</p>

      {/* Ask prompt */}
      {askPrompt && (
        <div className="bg-accent/4 rounded-lg px-3 py-2">
          <span className="text-[10px] font-semibold text-accent uppercase tracking-wider">Ask them: </span>
          <span className="text-[12px] text-[#044159] italic">&ldquo;{askPrompt}&rdquo;</span>
        </div>
      )}

      {/* No outcomes but engagement strategy */}
      {s.linkedOutcomes.length === 0 && s.engagementStrategy && (
        <p className="text-[11px] text-text-placeholder italic">Strategy: {s.engagementStrategy}</p>
      )}
    </div>
  )
}

// ── Quick Add ──

const STAKEHOLDER_TYPES: { value: StakeholderType; label: string }[] = [
  { value: 'champion', label: 'Champion' },
  { value: 'sponsor', label: 'Sponsor' },
  { value: 'influencer', label: 'Influencer' },
  { value: 'end_user', label: 'End User' },
  { value: 'blocker', label: 'Blocker' },
]

const INFLUENCE_LEVELS: { value: InfluenceLevel; label: string }[] = [
  { value: 'high', label: 'High' },
  { value: 'medium', label: 'Medium' },
  { value: 'low', label: 'Low' },
]

function QuickAddStakeholder({ projectId, onAdded }: { projectId: string; onAdded: () => void }) {
  const [isOpen, setIsOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [type, setType] = useState<StakeholderType>('champion')
  const [influence, setInfluence] = useState<InfluenceLevel>('medium')

  const handleSubmit = useCallback(async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      await createStakeholder(projectId, {
        name: name.trim(),
        role: role.trim() || undefined,
        stakeholder_type: type,
        influence_level: influence,
      })
      setName('')
      setRole('')
      setType('champion')
      setInfluence('medium')
      setIsOpen(false)
      onAdded()
    } catch (err) {
      console.error('Failed to create stakeholder:', err)
    } finally {
      setSaving(false)
    }
  }, [projectId, name, role, type, influence, onAdded])

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="w-full border border-dashed border-border rounded-xl px-4 py-3 text-[12px] text-brand-primary hover:bg-brand-primary-light transition-colors font-medium flex items-center justify-center gap-1.5"
      >
        <Plus className="w-3.5 h-3.5" />
        Add Stakeholder
      </button>
    )
  }

  return (
    <div className="border border-border rounded-xl p-4 bg-surface-subtle space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider">Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Full name"
            className="mt-1 w-full text-[13px] text-text-body border border-border rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
            autoFocus
          />
        </div>
        <div>
          <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider">Role</label>
          <input
            type="text"
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g. CEO, VP Sales"
            className="mt-1 w-full text-[13px] text-text-body border border-border rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider">Type</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as StakeholderType)}
            className="mt-1 w-full text-[13px] text-text-body border border-border rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
          >
            {STAKEHOLDER_TYPES.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider">Influence</label>
          <select
            value={influence}
            onChange={(e) => setInfluence(e.target.value as InfluenceLevel)}
            className="mt-1 w-full text-[13px] text-text-body border border-border rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
          >
            {INFLUENCE_LEVELS.map(l => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="flex items-center gap-2 justify-end">
        <button
          onClick={() => setIsOpen(false)}
          className="text-[12px] text-text-placeholder hover:text-text-body px-3 py-1.5 rounded-lg transition-colors"
        >
          Cancel
        </button>
        <button
          onClick={handleSubmit}
          disabled={!name.trim() || saving}
          className="bg-brand-primary text-white rounded-lg px-4 py-1.5 text-[12px] font-medium hover:bg-[#25785A] transition-colors disabled:opacity-50 flex items-center gap-1.5"
        >
          {saving ? <Loader2 className="w-3 h-3 animate-spin" /> : <Plus className="w-3 h-3" />}
          Add
        </button>
      </div>
    </div>
  )
}

// ── Main ──

export function StakeholderOutcomeMap({ projectId }: StakeholderOutcomeMapProps) {
  const { data: stakeholderData, mutate: mutateStakeholders } = useProjectStakeholders(projectId)
  const { data: outcomesTab } = useOutcomesTab(projectId)
  const { data: brd } = useBRDData(projectId)

  // Build actor outcome lookup: persona_name → outcomes
  const actorLookup = useMemo(() => {
    const lookup = new Map<string, ActorOutcomeLink[]>()
    const outcomes = outcomesTab?.outcomes
    if (!Array.isArray(outcomes)) return lookup

    for (const outcome of outcomes) {
      const o = outcome as {
        title: string
        actors?: Array<{
          persona_name: string; title: string; strength_score: number;
          status: string; sharpen_prompt?: string | null
        }>
      }
      if (!o.actors) continue
      for (const actor of o.actors) {
        const name = actor.persona_name.toLowerCase()
        const link: ActorOutcomeLink = {
          outcomeTitle: o.title,
          actorTitle: actor.title,
          strengthScore: actor.strength_score,
          status: actor.status,
          confirmed: actor.status === 'confirmed' || actor.status === 'validated',
          sharpenPrompt: actor.sharpen_prompt ?? null,
        }
        const existing = lookup.get(name) ?? []
        existing.push(link)
        lookup.set(name, existing)
      }
    }
    return lookup
  }, [outcomesTab])

  // Map stakeholders with their outcomes
  const stakeholders: MappedStakeholder[] = useMemo(() => {
    const raw = stakeholderData?.stakeholders ?? brd?.stakeholders ?? []
    return raw.map(s => ({
      id: s.id,
      name: s.name,
      role: s.role ?? null,
      stakeholderType: s.stakeholder_type ?? null,
      influenceLevel: s.influence_level ?? null,
      winConditions: ('win_conditions' in s ? (s as Record<string, unknown>).win_conditions as string[] : null) ?? [],
      engagementStrategy: ('engagement_strategy' in s ? (s as Record<string, unknown>).engagement_strategy as string : null) ?? null,
      confirmationStatus: s.confirmation_status ?? null,
      keyConcerns: ('key_concerns' in s ? (s as Record<string, unknown>).key_concerns as string[] : null) ?? [],
      linkedOutcomes: actorLookup.get(s.name.toLowerCase()) ?? [],
    }))
  }, [stakeholderData, brd, actorLookup])

  // Group stakeholders
  const groups: StakeholderGroup[] = useMemo(() => {
    const knownTypes = new Set(GROUP_CONFIG.map(g => g.type))
    const result: StakeholderGroup[] = GROUP_CONFIG.map(cfg => ({
      ...cfg,
      stakeholders: stakeholders.filter(s => s.stakeholderType === cfg.type),
    }))

    // Uncategorized
    const ungrouped = stakeholders.filter(s => !s.stakeholderType || !knownTypes.has(s.stakeholderType))
    if (ungrouped.length > 0) {
      result.push({
        type: 'uncategorized', label: 'Uncategorized',
        accentClass: 'border-l-border', badgeClass: 'bg-surface-subtle text-text-secondary',
        emptyWarning: null, stakeholders: ungrouped,
      })
    }

    return result
  }, [stakeholders])

  // Summary
  const totalStakeholders = stakeholders.length
  const coveredCount = stakeholders.filter(s => s.linkedOutcomes.length > 0).length
  const summary = totalStakeholders > 0 ? `${totalStakeholders} mapped · ${coveredCount} with outcomes` : ''

  // Uncovered gaps
  const missingChampion = !groups.find(g => g.type === 'champion')?.stakeholders.length
  const missingSponsor = !groups.find(g => g.type === 'sponsor')?.stakeholders.length
  const missingEndUsers = !groups.find(g => g.type === 'end_user')?.stakeholders.length

  if (totalStakeholders === 0) {
    return (
      <CollapsibleSection title="Stakeholder-Outcome Map" icon={<Users />} summary="">
        <div className="text-center py-6">
          <Users className="w-8 h-8 mx-auto mb-2 text-border" />
          <p className="text-sm text-text-placeholder">No stakeholders identified yet.</p>
          <p className="text-[11px] text-text-faint mt-1">Feed meeting transcripts or emails to map the client org.</p>
        </div>
      </CollapsibleSection>
    )
  }

  return (
    <CollapsibleSection title="Stakeholder-Outcome Map" icon={<Users />} summary={summary} defaultOpen>
      {groups.map(group => {
        if (group.stakeholders.length === 0 && !group.emptyWarning) return null

        return (
          <div key={group.type} className="mb-4 last:mb-0">
            {/* Group header */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[12px] font-semibold text-text-body">{group.label}</span>
              {group.stakeholders.length > 0 && (
                <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-semibold ${group.badgeClass}`}>
                  {group.stakeholders.length}
                </span>
              )}
            </div>

            {group.stakeholders.length > 0 ? (
              group.stakeholders.map(s => (
                <StakeholderCard key={s.id} s={s} accentClass={group.accentClass} />
              ))
            ) : group.emptyWarning ? (
              <div className="border border-dashed border-border rounded-xl px-3.5 py-2.5 mb-2">
                <p className="text-[11px] text-text-placeholder">{group.emptyWarning}</p>
              </div>
            ) : null}
          </div>
        )
      })}

      {/* Uncovered Gaps */}
      {(missingChampion || missingSponsor || missingEndUsers) && (
        <div className="mt-3 pt-3 border-t border-border">
          <div className="text-[12px] font-semibold text-text-body mb-2">Uncovered</div>
          {missingChampion && (
            <div className="border border-dashed border-border border-l-[3px] border-l-accent rounded-r-xl px-3.5 py-2.5 mb-2 bg-surface-subtle">
              <div className="flex items-center gap-1.5 text-[12px] font-semibold text-accent mb-1">
                <AlertCircle className="w-3.5 h-3.5 text-text-placeholder" />
                No champion identified
              </div>
              <p className="text-[11px] text-text-secondary">Unknown advocacy could mean no internal push.</p>
              <div className="bg-accent/4 rounded-lg px-3 py-2 mt-2">
                <span className="text-[10px] font-semibold text-accent uppercase tracking-wider">Ask: </span>
                <span className="text-[12px] text-[#044159] italic">&ldquo;Who internally is most excited about this project?&rdquo;</span>
              </div>
            </div>
          )}
          {missingSponsor && (
            <div className="border border-dashed border-border border-l-[3px] border-l-accent rounded-r-xl px-3.5 py-2.5 mb-2 bg-surface-subtle">
              <div className="flex items-center gap-1.5 text-[12px] font-semibold text-accent mb-1">
                <AlertCircle className="w-3.5 h-3.5 text-text-placeholder" />
                No economic buyer identified
              </div>
              <p className="text-[11px] text-text-secondary">Can&apos;t close without someone who controls budget.</p>
              <div className="bg-accent/4 rounded-lg px-3 py-2 mt-2">
                <span className="text-[10px] font-semibold text-accent uppercase tracking-wider">Ask: </span>
                <span className="text-[12px] text-[#044159] italic">&ldquo;Who signs off on the budget for this?&rdquo;</span>
              </div>
            </div>
          )}
          {missingEndUsers && stakeholders.length > 2 && (
            <div className="border border-dashed border-border border-l-[3px] border-l-border rounded-r-xl px-3.5 py-2.5 mb-2 bg-surface-subtle">
              <div className="flex items-center gap-1.5 text-[12px] font-semibold text-accent mb-1">
                <AlertCircle className="w-3.5 h-3.5 text-text-placeholder" />
                End users not yet mapped
              </div>
              <p className="text-[11px] text-text-secondary">The people who&apos;ll use this daily — their adoption is the H1 gate.</p>
              <div className="bg-accent/4 rounded-lg px-3 py-2 mt-2">
                <span className="text-[10px] font-semibold text-accent uppercase tracking-wider">Ask: </span>
                <span className="text-[12px] text-[#044159] italic">&ldquo;Can we talk to the team doing this work today?&rdquo;</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Quick Add */}
      <div className="mt-3">
        <QuickAddStakeholder projectId={projectId} onAdded={() => mutateStakeholders()} />
      </div>
    </CollapsibleSection>
  )
}
