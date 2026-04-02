'use client'

import { useMemo } from 'react'
import { Layers, Lock, HelpCircle } from 'lucide-react'
import { useOutcomesTab, useBRDData } from '@/lib/hooks/use-api'
import { CollapsibleSection } from '../CollapsibleSection'

interface InvestmentCaseProps {
  projectId: string
}

function formatCurrency(n: number) {
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toFixed(0)}`
}

interface HorizonCard {
  label: string
  title: string
  isActive: boolean
  outcomeCount: number
  avgStrength: number
  savesLabel: string | null
  unlocksLabel: string | null
  gate: string
  confidence: 'high' | 'medium' | 'low'
}

export function InvestmentCase({ projectId }: InvestmentCaseProps) {
  const { data: outcomesTab } = useOutcomesTab(projectId)
  const { data: brd } = useBRDData(projectId)

  const outcomes = useMemo(() => {
    if (!Array.isArray(outcomesTab?.outcomes)) return []
    return outcomesTab.outcomes as Array<{
      id: string; title: string; strength_score: number; horizon: string;
      confirmation_status: string; description: string;
      actors?: Array<{ sharpen_prompt?: string | null; persona_name: string }>
    }>
  }, [outcomesTab])

  const successMetrics = brd?.business_context?.success_metrics ?? []
  const roiSummary = brd?.roi_summary ?? []

  // Aggregate financials
  const totalAnnualLow = successMetrics
    .filter(m => m.monetary_timeframe === 'annual' || !m.monetary_timeframe)
    .reduce((s, m) => s + (m.monetary_value_low ?? 0), 0)
  const totalAnnualHigh = successMetrics
    .filter(m => m.monetary_timeframe === 'annual' || !m.monetary_timeframe)
    .reduce((s, m) => s + (m.monetary_value_high ?? 0), 0)
  const totalROI = roiSummary.reduce((s, r) => s + (r.cost_saved_per_year ?? 0), 0)

  // Group by horizon
  const horizonGroups = useMemo(() => {
    const groups: Record<string, typeof outcomes> = { h1: [], h2: [], h3: [] }
    for (const o of outcomes) {
      const h = o.horizon || 'h1'
      if (groups[h]) groups[h].push(o)
    }
    return groups
  }, [outcomes])

  const cards: HorizonCard[] = useMemo(() => {
    const h1 = horizonGroups.h1
    const h2 = horizonGroups.h2
    const h3 = horizonGroups.h3

    const h1Confirmed = h1.filter(o => o.confirmation_status === 'confirmed_consultant' || o.confirmation_status === 'confirmed_client').length
    const h1Avg = h1.length ? Math.round(h1.reduce((s, o) => s + o.strength_score, 0) / h1.length) : 0

    return [
      {
        label: 'H1', title: 'Prove It', isActive: true,
        outcomeCount: h1.length, avgStrength: h1Avg,
        savesLabel: totalROI > 0 ? `${formatCurrency(totalROI)}/yr` : (totalAnnualLow > 0 ? `${formatCurrency(totalAnnualLow)}/yr` : null),
        unlocksLabel: h1.length > 0 ? `${h1.length} outcome${h1.length > 1 ? 's' : ''}` : null,
        gate: h1.length > 0 ? `${h1Confirmed}/${h1.length} confirmed` : 'No outcomes',
        confidence: h1Avg >= 70 ? 'high' : h1Avg >= 40 ? 'medium' : 'low',
      },
      {
        label: 'H2', title: 'Scale It', isActive: false,
        outcomeCount: h2.length,
        avgStrength: h2.length ? Math.round(h2.reduce((s, o) => s + o.strength_score, 0) / h2.length) : 0,
        savesLabel: null,
        unlocksLabel: h2.length > 0 ? `${h2.length} outcome${h2.length > 1 ? 's' : ''}` : null,
        gate: h2.length > 0 ? 'Requires H1 proven' : 'No outcomes',
        confidence: h2.length > 0 ? 'medium' : 'low',
      },
      {
        label: 'H3', title: 'Own It', isActive: false,
        outcomeCount: h3.length,
        avgStrength: h3.length ? Math.round(h3.reduce((s, o) => s + o.strength_score, 0) / h3.length) : 0,
        savesLabel: null,
        unlocksLabel: h3.length > 0 ? `${h3.length} outcome${h3.length > 1 ? 's' : ''}` : null,
        gate: h3.length > 0 ? 'Requires H2 at scale' : 'No outcomes',
        confidence: h3.length > 0 ? 'low' : 'low',
      },
    ]
  }, [horizonGroups, totalROI, totalAnnualLow])

  // Insight synthesis
  const insight = useMemo(() => {
    if (totalROI > 0 && totalAnnualHigh > totalROI * 1.5) {
      return `The real play: estimated value (${formatCurrency(totalAnnualHigh)}/yr) is ${(totalAnnualHigh / totalROI).toFixed(1)}x the direct savings (${formatCurrency(totalROI)}/yr). This isn't just a cost project — it's a growth project.`
    }
    if (totalROI > 0) {
      return `H1 delivers ${formatCurrency(totalROI)}/yr in measurable savings. Each subsequent horizon only unlocks if the previous one proves out — the client is never over-committed.`
    }
    if (outcomes.length > 0) {
      return `${outcomes.length} outcomes mapped across ${[horizonGroups.h1.length > 0, horizonGroups.h2.length > 0, horizonGroups.h3.length > 0].filter(Boolean).length} horizons. Each horizon gates the next — de-risked investment at every stage.`
    }
    return null
  }, [totalROI, totalAnnualHigh, outcomes, horizonGroups])

  // Data needed from sharpen prompts
  const dataNeed = useMemo(() => {
    const needs: string[] = []
    for (const o of outcomes) {
      if (o.strength_score > 0 && o.strength_score < 70 && o.actors) {
        for (const a of o.actors) {
          if (a.sharpen_prompt && needs.length < 3) {
            needs.push(`${a.persona_name}: "${a.sharpen_prompt}" → sharpens "${o.title}"`)
          }
        }
      }
    }
    return needs
  }, [outcomes])

  // Summary
  const summaryParts: string[] = []
  if (totalROI > 0) summaryParts.push(`${formatCurrency(totalROI)}/yr savings`)
  if (outcomes.length > 0) summaryParts.push(`${outcomes.length} outcomes across ${cards.filter(c => c.outcomeCount > 0).length} horizons`)
  const summary = summaryParts.join(' · ')

  if (outcomes.length === 0 && totalROI === 0 && totalAnnualLow === 0) {
    return (
      <CollapsibleSection title="Investment Case" icon={<Layers />} summary="" defaultOpen={false}>
        <div className="text-center py-6">
          <Layers className="w-8 h-8 mx-auto mb-2 text-border" />
          <p className="text-sm text-text-placeholder">Generate outcomes to see your investment case.</p>
        </div>
      </CollapsibleSection>
    )
  }

  return (
    <CollapsibleSection title="Investment Case" icon={<Layers />} summary={summary} defaultOpen={false}>
      {/* Horizon Cascade */}
      <div className="flex items-stretch gap-0 mb-4">
        {cards.map((card, i) => (
          <div key={card.label} className="contents">
            {i > 0 && (
              <div className="flex items-center justify-center w-10 shrink-0 text-text-placeholder text-lg">
                →
              </div>
            )}
            <div className={`flex-1 border rounded-xl p-3.5 text-center ${card.isActive ? 'border-brand-primary' : 'border-border'}`}>
              <div className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider mb-1">{card.label}</div>
              <div className="text-[13px] font-semibold text-text-body mb-3">{card.title}</div>

              {card.savesLabel && (
                <>
                  <div className="text-[10px] font-semibold text-text-placeholder uppercase">Saves</div>
                  <div className="text-[12px] font-medium text-text-body mb-2">{card.savesLabel}</div>
                </>
              )}

              {card.unlocksLabel && (
                <>
                  <div className="text-[10px] font-semibold text-text-placeholder uppercase">Unlocks</div>
                  <div className="text-[12px] font-medium text-text-body mb-2">{card.unlocksLabel}</div>
                </>
              )}

              <div className="text-[10px] font-semibold text-text-placeholder uppercase">Gate</div>
              <div className="text-[11px] text-text-secondary flex items-center justify-center gap-1">
                <Lock className="w-3 h-3" />
                {card.gate}
              </div>

              {card.outcomeCount > 0 && (
                <div className="mt-2 pt-2 border-t border-border">
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                    card.confidence === 'high' ? 'bg-brand-primary-light text-[#25785A]'
                    : card.confidence === 'medium' ? 'bg-surface-subtle text-text-secondary'
                    : 'bg-surface-subtle text-text-placeholder'
                  }`}>
                    {card.confidence} confidence
                  </span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Insight Banner */}
      {insight && (
        <div className="bg-accent/4 border border-accent/8 rounded-xl px-4 py-3 mb-3">
          <p className="text-[13px] text-text-secondary leading-relaxed">{insight}</p>
        </div>
      )}

      {/* ROI Detail */}
      {roiSummary.length > 0 && (
        <div className="mb-3">
          <div className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider mb-2">Workflow ROI</div>
          <div className="space-y-1">
            {roiSummary.slice(0, 5).map((roi, i) => (
              <div key={i} className="flex items-center justify-between text-[12px]">
                <span className="text-text-secondary truncate">{roi.workflow_name}</span>
                <span className="text-text-body font-medium shrink-0 ml-2">
                  {roi.time_saved_minutes}min saved
                  {roi.cost_saved_per_year > 0 && ` · ${formatCurrency(roi.cost_saved_per_year)}/yr`}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Data needed */}
      {dataNeed.length > 0 && (
        <div className="bg-surface-subtle border border-border rounded-xl px-4 py-3">
          <div className="flex items-center gap-1.5 text-[12px] font-semibold text-text-body mb-2">
            <HelpCircle className="w-3.5 h-3.5 text-text-placeholder" />
            Data needed to sharpen
          </div>
          <div className="space-y-2">
            {dataNeed.map((d, i) => (
              <div key={i} className="flex items-start gap-2">
                <div className="w-1.5 h-1.5 rounded-full bg-brand-primary mt-1.5 shrink-0" />
                <p className="text-[12px] text-text-secondary leading-relaxed">{d}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </CollapsibleSection>
  )
}
