'use client'

import { useState, useMemo } from 'react'
import { Plus, Building2, Check, AlertCircle } from 'lucide-react'
import { useBRDData, useOutcomesTab, useCollaborationCurrent, useSalesIntel, useProjectStakeholders } from '@/lib/hooks/use-api'
import { ClientPortalModal } from '@/components/collaboration/ClientPortalModal'

interface DealReadinessHeroProps {
  projectId: string
}

const PHASE_LABELS: Record<string, string> = {
  pre_discovery: 'Pre-Discovery',
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  proposal: 'Proposal',
  closed: 'Closed',
}

// ── 6-Dimension Readiness Model ──

interface ReadinessDimension {
  key: string
  label: string
  score: number // 0-4
  sublabel: string
}

function scoreToSublabel(score: number): string {
  if (score === 0) return 'Not started'
  if (score === 1) return 'Emerging'
  if (score === 2) return 'Developing'
  if (score === 3) return 'Strong'
  return 'Complete'
}

function computeReadinessDimensions(
  outcomes: Array<{ strength_score: number; confirmation_status: string; evidence?: Array<{ direction: string }> }>,
  stakeholders: Array<{ stakeholder_type?: string | null; confirmation_status?: string | null }>,
  painPoints: { length: number },
  goals: { length: number },
  successMetrics: Array<{ monetary_value_low?: number | null; monetary_value_high?: number | null; monetary_confidence?: number | null }>,
  features: { length: number },
  workflowPairs: { length: number },
  allEntities: { personas: number; features: number; workflows: number; constraints: number },
): ReadinessDimension[] {
  // VALUE: Do we understand WHY? (outcomes + macro + drivers)
  let valueScore = 0
  if (outcomes.length > 0) valueScore = 1
  if (outcomes.length >= 3) valueScore = 2
  const avgStrength = outcomes.length ? outcomes.reduce((s, o) => s + o.strength_score, 0) / outcomes.length : 0
  if (avgStrength >= 60) valueScore = 3
  if (avgStrength >= 75 && outcomes.length >= 3) valueScore = 4

  // REQUIREMENTS: Do we know WHAT to build? (features + workflows + personas)
  let reqScore = 0
  if (allEntities.features > 0 || allEntities.workflows > 0) reqScore = 1
  if (allEntities.features >= 5 && allEntities.personas >= 2) reqScore = 2
  if (allEntities.features >= 5 && allEntities.workflows >= 2 && allEntities.personas >= 3) reqScore = 3
  if (reqScore >= 3 && workflowPairs.length >= 2) reqScore = 4

  // INVESTMENT: Do we know COST/RETURN? (monetary values + ROI)
  let investScore = 0
  const withMoney = successMetrics.filter(m => m.monetary_value_low || m.monetary_value_high)
  if (withMoney.length > 0) investScore = 1
  if (withMoney.length >= 2) investScore = 2
  const highConfidence = withMoney.filter(m => (m.monetary_confidence ?? 0) >= 0.7)
  if (highConfidence.length >= 2) investScore = 3
  if (highConfidence.length >= 3 && workflowPairs.length >= 2) investScore = 4

  // STAKEHOLDERS: Do we know WHO? (MEDDIC coverage)
  let stakeholderScore = 0
  if (stakeholders.length > 0) stakeholderScore = 1
  const hasChampion = stakeholders.some(s => s.stakeholder_type === 'champion')
  const hasSponsor = stakeholders.some(s => s.stakeholder_type === 'sponsor')
  if (hasChampion || hasSponsor) stakeholderScore = 2
  if (hasChampion && stakeholders.length >= 3) stakeholderScore = 3
  if (hasChampion && hasSponsor && stakeholders.some(s => s.confirmation_status === 'confirmed_client')) stakeholderScore = 4

  // OUTCOMES: Are outcomes STRONG? (strength + evidence + actor coverage)
  let outcomeScore = 0
  if (outcomes.length > 0) outcomeScore = 1
  const strong = outcomes.filter(o => o.strength_score >= 70)
  if (strong.length >= 2) outcomeScore = 2
  const withEvidence = outcomes.filter(o => (o.evidence?.length ?? 0) > 0)
  if (strong.length >= 3 && withEvidence.length >= 2) outcomeScore = 3
  if (strong.length >= outcomes.length * 0.8 && withEvidence.length >= outcomes.length * 0.5) outcomeScore = 4

  // VALIDATION: Has the client CONFIRMED? (confirmation across entities)
  let validationScore = 0
  const confirmedOutcomes = outcomes.filter(o => o.confirmation_status === 'confirmed_consultant' || o.confirmation_status === 'confirmed_client')
  if (confirmedOutcomes.length > 0) validationScore = 1
  if (confirmedOutcomes.length >= outcomes.length * 0.3) validationScore = 2
  const clientConfirmed = outcomes.filter(o => o.confirmation_status === 'confirmed_client')
  if (clientConfirmed.length > 0) validationScore = 3
  if (clientConfirmed.length >= outcomes.length * 0.5) validationScore = 4

  return [
    { key: 'value', label: 'Value', score: valueScore, sublabel: scoreToSublabel(valueScore) },
    { key: 'requirements', label: 'Requirements', score: reqScore, sublabel: scoreToSublabel(reqScore) },
    { key: 'investment', label: 'Investment', score: investScore, sublabel: scoreToSublabel(investScore) },
    { key: 'stakeholders', label: 'Stakeholders', score: stakeholderScore, sublabel: scoreToSublabel(stakeholderScore) },
    { key: 'outcomes', label: 'Outcomes', score: outcomeScore, sublabel: scoreToSublabel(outcomeScore) },
    { key: 'validation', label: 'Validation', score: validationScore, sublabel: scoreToSublabel(validationScore) },
  ]
}

// ── Working / Risk ──

function computeWorkingRisks(
  outcomes: Array<{ strength_score: number; confirmation_status: string; tension_with?: { outcome_id: string; outcome_title: string } | null }>,
  stakeholders: Array<{ stakeholder_type?: string | null; confirmation_status?: string | null; name: string }>,
  dimensions: ReadinessDimension[],
) {
  const working: string[] = []
  const risks: string[] = []

  // Strong outcomes
  const strongOutcomes = outcomes.filter(o => o.strength_score >= 70)
  if (strongOutcomes.length > 0) {
    working.push(`${strongOutcomes.length} outcome${strongOutcomes.length > 1 ? 's' : ''} with strong evidence`)
  }

  // Champion
  const champions = stakeholders.filter(s => s.stakeholder_type === 'champion')
  if (champions.length > 0) {
    const confirmed = champions.some(s => s.confirmation_status === 'confirmed_consultant' || s.confirmation_status === 'confirmed_client')
    working.push(`Champion: ${champions[0].name}${confirmed ? ' (confirmed)' : ''}`)
  } else {
    risks.push('No champion identified')
  }

  // Client confirmations
  const clientConfirmed = outcomes.filter(o => o.confirmation_status === 'confirmed_client')
  if (clientConfirmed.length > 0) {
    working.push(`${clientConfirmed.length} outcome${clientConfirmed.length > 1 ? 's' : ''} confirmed by client`)
  }

  // Weak dimensions
  const weakDims = dimensions.filter(d => d.score <= 1)
  for (const d of weakDims.slice(0, 2)) {
    risks.push(`${d.label}: ${d.sublabel.toLowerCase()}`)
  }

  // Tensions
  const tensions = outcomes.filter(o => o.tension_with)
  if (tensions.length > 0) {
    risks.push(`${tensions.length} outcome tension${tensions.length > 1 ? 's' : ''} unresolved`)
  }

  // Weak outcomes
  const weakOutcomes = outcomes.filter(o => o.strength_score > 0 && o.strength_score < 70)
  if (weakOutcomes.length > 0) {
    risks.push(`${weakOutcomes.length} outcome${weakOutcomes.length > 1 ? 's' : ''} need sharpening`)
  }

  return { working: working.slice(0, 3), risks: risks.slice(0, 3) }
}

// ── Readiness Pill ──

function ReadinessPill({ dim }: { dim: ReadinessDimension }) {
  return (
    <div className="flex items-center gap-2 bg-surface-subtle rounded-full px-3 py-1.5">
      <span className="text-[10px] font-semibold text-text-secondary uppercase tracking-wider whitespace-nowrap">
        {dim.label}
      </span>
      <div className="flex items-center gap-[3px]">
        {[0, 1, 2, 3].map(i => (
          <span
            key={i}
            className={`w-[7px] h-[7px] rounded-full transition-colors ${
              i < dim.score ? 'bg-brand-primary' : 'bg-border'
            }`}
          />
        ))}
      </div>
      <span className="text-[10px] text-text-placeholder whitespace-nowrap">{dim.sublabel}</span>
    </div>
  )
}

// ── Main Component ──

export function DealReadinessHero({ projectId }: DealReadinessHeroProps) {
  const { data: brd } = useBRDData(projectId)
  const { data: outcomesTab } = useOutcomesTab(projectId)
  const { data: collab, mutate } = useCollaborationCurrent(projectId)
  const { data: salesIntel } = useSalesIntel(projectId)
  const { data: stakeholderData } = useProjectStakeholders(projectId)
  const [showInvite, setShowInvite] = useState(false)

  const companyName = brd?.business_context?.company_name || salesIntel?.client_name || 'Client'
  const industry = brd?.business_context?.industry || salesIntel?.client_industry
  const macroOutcome = outcomesTab?.macro_outcome
  const vision = brd?.business_context?.vision
  const phase = collab?.collaboration_phase
  const projectType = brd?.project_type
  const clientsInvited = collab?.portal_sync?.clients_invited ?? 0
  const clientsActive = collab?.portal_sync?.clients_active ?? 0

  const initials = companyName
    .split(/\s+/)
    .slice(0, 2)
    .map((w: string) => w[0])
    .join('')
    .toUpperCase()

  const outcomes = useMemo(() => {
    const raw = outcomesTab?.outcomes
    if (!Array.isArray(raw)) return []
    return raw as Array<{
      id: string; title: string; confirmation_status: string; strength_score: number;
      evidence?: Array<{ direction: string }>; tension_with?: { outcome_id: string; outcome_title: string } | null
    }>
  }, [outcomesTab])

  const stakeholders = useMemo(() => {
    return (stakeholderData?.stakeholders ?? brd?.stakeholders ?? []) as Array<{
      stakeholder_type?: string | null; confirmation_status?: string | null; name: string
    }>
  }, [stakeholderData, brd])

  const painPoints = brd?.business_context?.pain_points ?? []
  const goals = brd?.business_context?.goals ?? []
  const successMetrics = brd?.business_context?.success_metrics ?? []
  const workflowPairs = brd?.workflow_pairs ?? []

  const allEntities = useMemo(() => ({
    personas: (brd?.actors?.length ?? 0),
    features: ((brd?.requirements?.must_have?.length ?? 0) + (brd?.requirements?.should_have?.length ?? 0) + (brd?.requirements?.could_have?.length ?? 0)),
    workflows: workflowPairs.length,
    constraints: (brd?.constraints?.length ?? 0),
  }), [brd, workflowPairs])

  // 6 readiness dimensions
  const dimensions = useMemo(
    () => computeReadinessDimensions(outcomes, stakeholders, painPoints, goals, successMetrics, [], workflowPairs, allEntities),
    [outcomes, stakeholders, painPoints, goals, successMetrics, workflowPairs, allEntities]
  )

  // Composite score: average of all 6 dimensions, scaled to 100
  const readinessScore = useMemo(() => {
    const total = dimensions.reduce((s, d) => s + d.score, 0)
    return Math.round((total / (dimensions.length * 4)) * 100)
  }, [dimensions])

  // Working / Risks
  const { working, risks } = useMemo(
    () => computeWorkingRisks(outcomes, stakeholders, dimensions),
    [outcomes, stakeholders, dimensions]
  )

  const hasData = outcomes.length > 0 || painPoints.length > 0

  return (
    <>
      <div className="bg-white rounded-2xl border border-border shadow-sm p-5">
        {/* Row 1: Identity */}
        <div className="flex items-center gap-3.5 flex-wrap">
          <div className="w-11 h-11 rounded-xl bg-accent flex items-center justify-center text-white font-bold text-sm shrink-0">
            {initials || <Building2 className="w-5 h-5" />}
          </div>
          <h2 className="text-lg font-semibold text-text-body truncate">{companyName}</h2>
          {industry && (
            <span className="px-2.5 py-0.5 rounded-full bg-surface-subtle text-[11px] font-medium text-text-secondary">
              {industry}
            </span>
          )}
          {phase && (
            <span className="px-2.5 py-0.5 rounded-full bg-brand-primary-light text-[11px] font-semibold text-brand-primary">
              {PHASE_LABELS[phase] || phase}
            </span>
          )}
          {projectType && projectType !== 'new_product' && (
            <span className="px-2.5 py-0.5 rounded-full bg-accent/6 text-[11px] font-medium text-accent">
              {projectType === 'internal' ? 'Internal' : projectType === 'market_product' ? 'Market' : projectType}
            </span>
          )}
          <div className="ml-auto flex items-center gap-3">
            {clientsInvited > 0 && (
              <div className="flex items-center gap-1.5 text-sm text-text-secondary">
                <span className={`w-2 h-2 rounded-full ${clientsActive > 0 ? 'bg-brand-primary' : 'bg-border'}`} />
                <span className="font-medium">{clientsInvited} invited</span>
              </div>
            )}
            <button
              onClick={() => setShowInvite(true)}
              className="border border-dashed border-border rounded-xl px-3 py-1.5 text-[12px] text-brand-primary hover:bg-brand-primary-light transition-colors font-medium flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Invite
            </button>
          </div>
        </div>

        {/* Vision / Macro outcome */}
        {(macroOutcome || vision) && (
          <p className="mt-2.5 text-[13px] text-text-secondary line-clamp-2 pl-[54px]">
            {String(macroOutcome || vision || '')}
          </p>
        )}

        {/* Readiness Section */}
        {hasData && (
          <div className="mt-4 pt-4 border-t border-border">
            {/* Score + Dimensions */}
            <div className="flex items-center gap-4 mb-4">
              <div className="shrink-0 text-center">
                <div className="text-[28px] font-bold text-text-body leading-none">
                  {readinessScore}
                </div>
                <div className="text-[9px] font-semibold text-text-placeholder uppercase tracking-wider mt-1">
                  Readiness
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {dimensions.map(dim => (
                  <ReadinessPill key={dim.key} dim={dim} />
                ))}
              </div>
            </div>

            {/* Working / Risks */}
            {(working.length > 0 || risks.length > 0) && (
              <div className="grid grid-cols-2 gap-4">
                {working.length > 0 && (
                  <div>
                    <div className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider mb-2">
                      What&apos;s Working
                    </div>
                    {working.map((item, i) => (
                      <div key={i} className="flex items-start gap-2 mb-1.5">
                        <Check className="w-3.5 h-3.5 text-brand-primary shrink-0 mt-0.5" />
                        <span className="text-[12px] text-text-secondary leading-snug">{item}</span>
                      </div>
                    ))}
                  </div>
                )}
                {risks.length > 0 && (
                  <div>
                    <div className="text-[10px] font-semibold text-text-placeholder uppercase tracking-wider mb-2">
                      What&apos;s At Risk
                    </div>
                    {risks.map((item, i) => (
                      <div key={i} className="flex items-start gap-2 mb-1.5">
                        <AlertCircle className="w-3.5 h-3.5 text-text-placeholder shrink-0 mt-0.5" />
                        <span className="text-[12px] text-text-secondary leading-snug">{item}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Empty state */}
        {!hasData && (
          <div className="mt-4 pt-4 border-t border-border">
            <div className="flex items-center gap-2 text-text-placeholder">
              <Building2 className="w-4 h-4" />
              <span className="text-sm">Feed signals to build project readiness.</span>
            </div>
          </div>
        )}
      </div>

      <ClientPortalModal
        projectId={projectId}
        projectName={companyName}
        isOpen={showInvite}
        onClose={() => setShowInvite(false)}
        onRefresh={() => mutate()}
      />
    </>
  )
}
