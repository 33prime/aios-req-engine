'use client'

import { useMemo, useState, useCallback } from 'react'
import { BookOpen, Zap, Lock, HelpCircle } from 'lucide-react'
import { useOutcomesTab, useBRDData } from '@/lib/hooks/use-api'
import { Markdown } from '@/components/ui/Markdown'
import { CollapsibleSection } from '../CollapsibleSection'
import { ValueCalculator, type CalculatedValues } from './ValueCalculator'

interface ValueStorySectionProps {
  projectId: string
}

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toFixed(0)}`
}

function StrengthRing({ score, size = 28 }: { score: number; size?: number }) {
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
      <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-text-body">{score}</span>
    </div>
  )
}

export function ValueStorySection({ projectId }: ValueStorySectionProps) {
  const { data: outcomesTab } = useOutcomesTab(projectId)
  const { data: brd } = useBRDData(projectId)

  const [calcValues, setCalcValues] = useState<CalculatedValues | null>(null)

  const handleCalcChange = useCallback((values: CalculatedValues) => {
    setCalcValues(values)
  }, [])

  const outcomes = useMemo(() => {
    if (!Array.isArray(outcomesTab?.outcomes)) return []
    return outcomesTab.outcomes as Array<{
      id: string; title: string; description: string; strength_score: number;
      strength_dimensions?: Record<string, number>; horizon: string;
      confirmation_status: string; actors?: Array<{ sharpen_prompt?: string | null; persona_name: string }>
    }>
  }, [outcomesTab])

  const macroOutcome = outcomesTab?.macro_outcome as string | null | undefined
  const outcomeThesis = outcomesTab?.outcome_thesis as string | null | undefined
  const rollup = outcomesTab?.rollup as {
    total_outcomes?: number; strong_outcomes?: number; avg_strength?: number; weak_outcomes?: number
  } | undefined

  const successMetrics = brd?.business_context?.success_metrics ?? []
  const roiSummary = brd?.roi_summary ?? []
  const needNarrative = brd?.need_narrative

  // Group outcomes by horizon — each horizon is independent (not cascading)
  const horizonGroups = useMemo(() => {
    const groups: Record<string, typeof outcomes> = { h1: [], h2: [], h3: [] }
    for (const o of outcomes) {
      const h = o.horizon || 'h1'
      if (groups[h]) groups[h].push(o)
      else groups.h1.push(o)
    }
    return groups
  }, [outcomes])

  // Derive horizon financials from calculator values
  const horizonCards = useMemo(() => {
    const cv = calcValues

    return [
      {
        key: 'h1', tag: 'H1 · Near Term', title: 'Prove It',
        outcomes: horizonGroups.h1,
        savesLabel: cv ? `${formatCurrency(cv.directSavings)}/yr` : null,
        savesDetail: cv ? `${cv.hoursFreedPerYear} hrs/yr freed` : null,
        unlocksLabel: cv ? `+${cv.additionalClients} clients` : (horizonGroups.h1.length > 0 ? `${horizonGroups.h1.length} outcomes` : null),
        unlocksDetail: cv ? `${formatCurrency(cv.revenueUnlock)}/yr capacity` : null,
        gate: horizonGroups.h1.length > 0
          ? `${horizonGroups.h1.filter(o => o.confirmation_status === 'confirmed_consultant' || o.confirmation_status === 'confirmed_client').length}/${horizonGroups.h1.length} outcomes confirmed`
          : null,
      },
      {
        key: 'h2', tag: 'H2 · Mid Term', title: 'Scale It',
        outcomes: horizonGroups.h2,
        savesLabel: null,
        savesDetail: null,
        unlocksLabel: horizonGroups.h2.length > 0 ? `${horizonGroups.h2.length} outcomes` : null,
        unlocksDetail: horizonGroups.h2.length > 0 ? 'Operational scale' : null,
        gate: horizonGroups.h2.length > 0
          ? `${horizonGroups.h2.filter(o => o.confirmation_status === 'confirmed_consultant' || o.confirmation_status === 'confirmed_client').length}/${horizonGroups.h2.length} confirmed`
          : null,
      },
      {
        key: 'h3', tag: 'H3 · Long Term', title: 'Own It',
        outcomes: horizonGroups.h3,
        savesLabel: null,
        savesDetail: null,
        unlocksLabel: horizonGroups.h3.length > 0 ? `${horizonGroups.h3.length} outcomes` : null,
        unlocksDetail: horizonGroups.h3.length > 0 ? 'Strategic advantage' : null,
        gate: horizonGroups.h3.length > 0
          ? `${horizonGroups.h3.filter(o => o.confirmation_status === 'confirmed_consultant' || o.confirmation_status === 'confirmed_client').length}/${horizonGroups.h3.length} confirmed`
          : null,
      },
    ]
  }, [horizonGroups, calcValues])

  // Strengthening questions from weak outcomes
  const sharpenQuestions = useMemo(() => {
    const questions: Array<{ question: string; who: string; impact: string }> = []
    for (const o of outcomes) {
      if (o.strength_score > 0 && o.strength_score < 70 && o.actors) {
        for (const actor of o.actors) {
          if (actor.sharpen_prompt) {
            questions.push({
              question: actor.sharpen_prompt,
              who: `Ask ${actor.persona_name}`,
              impact: `Strengthens "${o.title}" (currently ${o.strength_score})`,
            })
          }
        }
      }
      if (questions.length >= 3) break
    }
    return questions
  }, [outcomes])

  const summary = useMemo(() => {
    const parts: string[] = []
    if (rollup?.total_outcomes) parts.push(`${rollup.total_outcomes} outcomes`)
    if (calcValues?.totalValue) parts.push(`${formatCurrency(calcValues.totalValue)}/yr value`)
    else if (rollup?.avg_strength) parts.push(`avg ${rollup.avg_strength}`)
    return parts.join(' · ')
  }, [rollup, calcValues])

  // Is it actually a no-brainer?
  const isNoBrainer = calcValues?.isNoBrainer ?? false

  if (outcomes.length === 0 && !needNarrative && !macroOutcome) {
    return (
      <CollapsibleSection title="Value Story" icon={<BookOpen />} summary="">
        <div className="text-center py-6">
          <BookOpen className="w-8 h-8 mx-auto mb-2 text-border" />
          <p className="text-sm text-text-placeholder">Feed signals to build your value story.</p>
          <p className="text-[11px] text-text-faint mt-1">Outcomes will appear as the system processes signals.</p>
        </div>
      </CollapsibleSection>
    )
  }

  return (
    <CollapsibleSection title="Value Story" icon={<BookOpen />} summary={summary} defaultOpen>
      {/* Macro Outcome */}
      {macroOutcome && (
        <div className="border-l-[3px] border-brand-primary bg-brand-primary-light rounded-r-xl px-4 py-3 mb-4">
          <p className="text-sm font-semibold text-text-body leading-relaxed">{String(macroOutcome)}</p>
        </div>
      )}

      {/* Outcome Thesis — rendered as markdown */}
      {outcomeThesis && (
        <div className="mb-4">
          <Markdown content={String(outcomeThesis)} className="text-[13px] text-text-secondary leading-relaxed" />
        </div>
      )}

      {/* Need Narrative fallback */}
      {!macroOutcome && !outcomeThesis && needNarrative && (
        <div className="border-l-[3px] border-brand-primary bg-brand-primary-light rounded-r-xl px-4 py-3 mb-4">
          <p className="text-sm text-text-body leading-relaxed">{needNarrative.text}</p>
        </div>
      )}

      {/* Rollup Stats */}
      {rollup && (rollup.total_outcomes ?? 0) > 0 && (
        <div className="flex items-center gap-4 mb-4 text-[12px] text-text-secondary">
          <span><strong className="text-text-body">{rollup.total_outcomes}</strong> outcomes</span>
          <span><strong className="text-text-body">{rollup.strong_outcomes}</strong> strong</span>
          {(rollup.weak_outcomes ?? 0) > 0 && (
            <span className="text-text-placeholder">{rollup.weak_outcomes} need sharpening</span>
          )}
          {rollup.avg_strength !== undefined && (
            <span className="ml-auto flex items-center gap-1.5">
              <StrengthRing score={rollup.avg_strength} />
              <span className="text-[11px] text-text-placeholder">avg</span>
            </span>
          )}
        </div>
      )}

      {/* Value Calculator */}
      {roiSummary.length > 0 && (
        <div className="mb-4">
          <ValueCalculator
            roiSummary={roiSummary}
            workflowPairCount={roiSummary.length}
            currentTotalMinutes={roiSummary.reduce((s, r) => s + (r.current_total_minutes ?? 0), 0)}
            futureTotalMinutes={roiSummary.reduce((s, r) => s + (r.future_total_minutes ?? 0), 0)}
            onValuesChange={handleCalcChange}
          />
        </div>
      )}

      {/* Horizon Cards — independent, not cascading */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {horizonCards.map((h, idx) => (
          <div
            key={h.key}
            className={`border rounded-xl p-4 bg-white ${
              idx === 0 ? 'border-l-[3px] border-l-brand-primary border-border' : 'border-border opacity-80'
            }`}
          >
            <div className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider mb-1">{h.tag}</div>
            <div className="text-[14px] font-semibold text-text-body mb-2">{h.title}</div>

            {h.outcomes.length > 0 ? (
              <>
                <div className="space-y-1.5 mb-3">
                  {h.outcomes.slice(0, 3).map(o => (
                    <div key={o.id} className="flex items-center gap-2">
                      <StrengthRing score={o.strength_score} size={24} />
                      <span className="text-[11px] text-text-body truncate">{o.title}</span>
                    </div>
                  ))}
                  {h.outcomes.length > 3 && (
                    <span className="text-[10px] text-text-placeholder">+{h.outcomes.length - 3} more</span>
                  )}
                </div>

                {(h.savesLabel || h.unlocksLabel) && (
                  <div className="space-y-2">
                    {h.savesLabel && (
                      <div className="bg-surface-subtle rounded-lg px-3 py-2">
                        <div className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider">Saves</div>
                        <div className="text-[13px] font-semibold text-text-body">{h.savesLabel}</div>
                        {h.savesDetail && <div className="text-[11px] text-text-placeholder">{h.savesDetail}</div>}
                      </div>
                    )}
                    {h.unlocksLabel && (
                      <div className="bg-brand-primary-light rounded-lg px-3 py-2">
                        <div className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider">Unlocks</div>
                        <div className="text-[13px] font-semibold text-text-body">{h.unlocksLabel}</div>
                        {h.unlocksDetail && <div className="text-[11px] text-text-placeholder">{h.unlocksDetail}</div>}
                      </div>
                    )}
                  </div>
                )}

                {h.gate && (
                  <div className="mt-2 pt-2 border-t border-border flex items-center gap-1.5 text-[11px] text-text-placeholder">
                    <Lock className="w-3 h-3" />
                    {h.gate}
                  </div>
                )}
              </>
            ) : (
              <div className="py-4 text-center">
                <p className="text-[11px] text-text-placeholder">No outcomes mapped here yet.</p>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* No-brainer — only if the math actually supports it */}
      {isNoBrainer && calcValues && (
        <div className="bg-brand-primary-light border border-brand-primary/15 rounded-xl px-4 py-3 mb-3">
          <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[#25785A] mb-1">
            <Zap className="w-3.5 h-3.5" />
            No-brainer
          </div>
          <p className="text-[13px] text-text-body leading-relaxed">
            At {formatCurrency(calcValues.engagementValue)} per engagement, the platform pays for itself in{' '}
            <strong>{calcValues.paybackMonths} months</strong> through direct savings alone.
            Revenue capacity adds {formatCurrency(calcValues.revenueUnlock)}/yr on top.
          </p>
        </div>
      )}

      {/* Strengthening Questions */}
      {sharpenQuestions.length > 0 && (
        <div className="bg-white border border-border rounded-xl px-4 py-3">
          <div className="flex items-center gap-1.5 text-[12px] font-semibold text-text-body mb-2">
            <HelpCircle className="w-3.5 h-3.5 text-text-placeholder" />
            What would strengthen this?
          </div>
          <div className="space-y-2.5">
            {sharpenQuestions.map((q, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <div className="w-1.5 h-1.5 rounded-full bg-brand-primary mt-1.5 shrink-0" />
                <div>
                  <p className="text-[12px] text-text-secondary leading-relaxed">&ldquo;{q.question}&rdquo;</p>
                  <p className="text-[10px] font-semibold text-accent uppercase tracking-wider mt-0.5">{q.who}</p>
                  <p className="text-[11px] text-text-placeholder mt-0.5">{q.impact}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </CollapsibleSection>
  )
}
