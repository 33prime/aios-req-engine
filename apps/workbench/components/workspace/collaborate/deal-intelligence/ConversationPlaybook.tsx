'use client'

import { useMemo } from 'react'
import { MessageCircle } from 'lucide-react'
import { useOutcomesTab, useProjectStakeholders, useBRDData, useSalesIntel } from '@/lib/hooks/use-api'
import { computeMeddicDimensions } from '../MeddicTracker'
import { CollapsibleSection } from '../CollapsibleSection'

interface ConversationPlaybookProps {
  projectId: string
}

// ── Types ──

interface PlaybookItem {
  id: string
  priority: number
  type: string
  who: string
  question: string
  why: string
  impacts: string[]
}

// ── Main ──

export function ConversationPlaybook({ projectId }: ConversationPlaybookProps) {
  const { data: outcomesTab } = useOutcomesTab(projectId)
  const { data: stakeholderData } = useProjectStakeholders(projectId)
  const { data: brd } = useBRDData(projectId)
  const { data: salesIntel } = useSalesIntel(projectId)

  const outcomes = useMemo(() => {
    if (!Array.isArray(outcomesTab?.outcomes)) return []
    return outcomesTab.outcomes as Array<{
      id: string; title: string; strength_score: number; horizon: string;
      strength_dimensions?: Record<string, number>;
      tension_with?: { outcome_id: string; outcome_title: string } | null;
      actors?: Array<{ persona_name: string; sharpen_prompt?: string | null; strength_score: number }>
    }>
  }, [outcomesTab])

  const stakeholders = stakeholderData?.stakeholders ?? brd?.stakeholders ?? []
  const painPoints = brd?.business_context?.pain_points ?? []
  const successMetrics = brd?.business_context?.success_metrics ?? []
  const phase = salesIntel?.deal_readiness_score !== undefined ? 'validation' : undefined

  const items = useMemo(() => {
    const result: PlaybookItem[] = []
    let id = 0

    // 1. Sharpen prompts from weak outcomes (h1 weighted 1.5x)
    const weakOutcomes = [...outcomes]
      .filter(o => o.strength_score > 0 && o.strength_score < 70)
      .sort((a, b) => {
        const aWeight = a.horizon === 'h1' ? 1.5 : 1
        const bWeight = b.horizon === 'h1' ? 1.5 : 1
        return (100 - b.strength_score) * bWeight - (100 - a.strength_score) * aWeight
      })

    for (const o of weakOutcomes.slice(0, 3)) {
      const actor = o.actors?.find(a => a.sharpen_prompt)
      if (actor?.sharpen_prompt) {
        // Find which dimension is weakest
        const dims = o.strength_dimensions ?? {}
        const weakestDim = Object.entries(dims).sort((a, b) => a[1] - b[1])[0]
        const dimLabel = weakestDim ? weakestDim[0].replace(/_/g, ' ') : 'evidence'

        result.push({
          id: String(++id),
          priority: id,
          type: 'Sharpen Outcome',
          who: `Ask ${actor.persona_name}`,
          question: actor.sharpen_prompt,
          why: `"${o.title}" scores ${o.strength_score} — weakest on ${dimLabel}. This question strengthens the case.`,
          impacts: [
            `Outcome → ~${Math.min(100, o.strength_score + 15)}`,
            o.horizon.toUpperCase(),
            dimLabel,
          ],
        })
      }
    }

    // 2. MEDDIC gaps
    const meddicDims = computeMeddicDimensions(painPoints, stakeholders, successMetrics, phase)
    const weakDims = meddicDims.filter(d => d.score <= 1)
    for (const dim of weakDims.slice(0, 2)) {
      const questions: Record<string, { question: string; who: string }> = {
        Pain: { question: 'What specific operational pain points occur most frequently, and what do they cost you?', who: 'Ask the primary contact' },
        Champion: { question: 'Who internally is most excited about solving this problem?', who: 'Ask the primary contact' },
        'Econ Buyer': { question: 'Who controls the budget for this kind of initiative?', who: 'Ask the champion' },
        Decision: { question: 'Walk me through how a decision like this typically gets approved.', who: 'Ask the sponsor' },
        Metrics: { question: 'How would you measure success in the first 90 days?', who: 'Ask the champion' },
        Timeline: { question: 'What\'s driving the timeline — is there a hard deadline or trigger event?', who: 'Ask the sponsor' },
      }
      const q = questions[dim.label]
      if (q && result.length < 5) {
        result.push({
          id: String(++id),
          priority: id,
          type: `MEDDIC Gap: ${dim.label}`,
          who: q.who,
          question: q.question,
          why: `${dim.label} is at "${dim.sublabel}" — needs to reach "Mapped" or higher to de-risk the deal.`,
          impacts: [`${dim.label} ●${dim.score > 0 ? '●' : '○'}→●●●`, 'Deal readiness'],
        })
      }
    }

    // 3. Unresolved tensions
    const tensions = outcomes.filter(o => o.tension_with)
    for (const t of tensions.slice(0, 1)) {
      if (result.length < 5) {
        result.push({
          id: String(++id),
          priority: id,
          type: 'Resolve Tension',
          who: 'Ask key stakeholders together',
          question: `"${t.title}" and "${t.tension_with?.outcome_title}" are in conflict. Which matters more at H1, or is there a version where both work?`,
          why: 'This tension is blocking both outcomes from advancing. Resolving it clears the path for H1 scope.',
          impacts: ['2 outcomes unblocked', 'H1 scope clarity'],
        })
      }
    }

    // 4. Missing baselines
    const noBaseline = outcomes.filter(o => (o.strength_dimensions?.observable ?? 0) < 10)
    if (noBaseline.length >= 3 && result.length < 5) {
      result.push({
        id: String(++id),
        priority: id,
        type: 'Get Baseline',
        who: 'Ask the ops team',
        question: 'Can you share the current volume numbers — how many times per week does this process run, and how long does each one take?',
        why: `${noBaseline.length} outcomes lack baseline metrics. Without "where are you today," we can\'t show the delta.`,
        impacts: [`${noBaseline.length} baselines set`, 'Metrics ●○→●●●', 'Savings confirmed'],
      })
    }

    return result.slice(0, 5)
  }, [outcomes, stakeholders, painPoints, successMetrics, phase])

  // Estimate belief improvement
  const currentBelief = salesIntel?.deal_readiness_score ?? 65
  const expectedImprovement = Math.min(95, currentBelief + items.length * 3)

  const summary = items.length > 0 ? `${items.length} priorities queued` : ''

  if (items.length === 0) {
    return (
      <CollapsibleSection title="Conversation Playbook" icon={<MessageCircle />} summary="">
        <div className="text-center py-6">
          <MessageCircle className="w-8 h-8 mx-auto mb-2 text-border" />
          <p className="text-sm text-text-placeholder">All outcomes are strong. No immediate conversation priorities.</p>
        </div>
      </CollapsibleSection>
    )
  }

  return (
    <CollapsibleSection title="Conversation Playbook" icon={<MessageCircle />} summary={summary} defaultOpen>
      <p className="text-[12px] text-text-placeholder mb-3">Priorities for your next meeting</p>

      <div className="space-y-2.5">
        {items.map((item, i) => (
          <div key={item.id} className="border border-border rounded-xl p-4 flex gap-3.5 transition-all hover:shadow-sm">
            <div className="w-7 h-7 rounded-lg bg-accent text-white text-[13px] font-bold flex items-center justify-center shrink-0">
              {i + 1}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider mb-0.5">
                {item.type}
              </div>
              <div className="text-[12px] font-semibold text-text-body mb-1.5">{item.who}</div>
              <div className="text-[13px] text-[#044159] italic leading-relaxed bg-accent/3 rounded-lg px-3 py-2 mb-2">
                &ldquo;{item.question}&rdquo;
              </div>
              <p className="text-[11px] text-text-placeholder leading-snug mb-1.5">
                <strong className="text-text-secondary">Why:</strong> {item.why}
              </p>
              <div className="flex flex-wrap gap-1">
                {item.impacts.map((impact, j) => (
                  <span key={j} className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-surface-subtle text-text-secondary">
                    {impact}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Expected improvement */}
      <div className="mt-3 text-center py-3 bg-brand-primary-light rounded-xl">
        <p className="text-[13px] text-text-body">
          After this meeting, expected readiness:{' '}
          <strong className="text-[#25785A]">{currentBelief} → ~{expectedImprovement}</strong>
        </p>
      </div>
    </CollapsibleSection>
  )
}
