'use client'

interface MeddicDimension {
  label: string
  score: number // 0-4
  sublabel: string
}

interface MeddicTrackerProps {
  dimensions: MeddicDimension[]
}

function scoreToSublabel(score: number): string {
  if (score === 0) return 'Unknown'
  if (score === 1) return 'Identified'
  if (score === 2) return 'Mapped'
  if (score === 3) return 'Strong'
  return 'Confirmed'
}

function DimensionPill({ label, score, sublabel }: MeddicDimension) {
  return (
    <div className="flex items-center gap-2 bg-surface-subtle rounded-full px-3 py-1.5">
      <span className="text-[11px] font-semibold text-text-secondary uppercase tracking-wider whitespace-nowrap">
        {label}
      </span>
      <div className="flex items-center gap-0.5">
        {[0, 1, 2, 3].map((i) => (
          <span
            key={i}
            className={`w-2 h-2 rounded-full ${
              i < score ? 'bg-brand-primary' : 'bg-border'
            }`}
          />
        ))}
      </div>
      <span className="text-[10px] text-text-placeholder whitespace-nowrap">
        {sublabel}
      </span>
    </div>
  )
}

export function MeddicTracker({ dimensions }: MeddicTrackerProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {dimensions.map((dim) => (
        <DimensionPill key={dim.label} {...dim} />
      ))}
    </div>
  )
}

// Scoring helpers — compute MEDDIC dimensions from existing data
export function computeMeddicDimensions(
  painPoints: Array<{ severity?: string | null; business_impact?: string | null; current_workaround?: string | null; frequency?: string | null; confirmation_status?: string | null }>,
  stakeholders: Array<{ stakeholder_type?: string | null; win_conditions?: string[] | null; engagement_strategy?: string | null; confirmation_status?: string | null; decision_authority?: string | null }>,
  successMetrics: Array<{ monetary_value_low?: number | null; monetary_value_high?: number | null; monetary_confidence?: number | null; confirmation_status?: string | null }>,
  collaborationPhase?: string | null,
): MeddicDimension[] {
  // Pain: 0=none, 1=has pains, 2=has severity+impact, 3=has workarounds/frequency, 4=any confirmed_client
  let painScore = 0
  if (painPoints.length > 0) {
    painScore = 1
    if (painPoints.some(p => p.severity && p.business_impact)) painScore = 2
    if (painPoints.some(p => p.current_workaround || p.frequency)) painScore = 3
    if (painPoints.some(p => p.confirmation_status === 'confirmed_client')) painScore = 4
  }

  // Champion: stakeholders with type=champion
  const champions = stakeholders.filter(s => s.stakeholder_type === 'champion')
  let championScore = 0
  if (champions.length > 0) {
    championScore = 1
    if (champions.some(c => c.win_conditions && c.win_conditions.length > 0)) championScore = 2
    if (champions.some(c => c.engagement_strategy)) championScore = 3
    if (champions.some(c => c.confirmation_status === 'confirmed_client')) championScore = 4
  }

  // Economic Buyer: stakeholders with type=sponsor
  const sponsors = stakeholders.filter(s => s.stakeholder_type === 'sponsor')
  let econScore = 0
  if (sponsors.length > 0) {
    econScore = 1
    if (sponsors.some(s => s.decision_authority)) econScore = 2
    if (sponsors.some(s => s.engagement_strategy)) econScore = 3
    if (sponsors.some(s => s.confirmation_status === 'confirmed_client')) econScore = 4
  }

  // Decision Process: stakeholders with decision_authority
  const decisionHolders = stakeholders.filter(s => s.decision_authority)
  let decisionScore = 0
  if (decisionHolders.length > 0) {
    decisionScore = 1
    const blockers = stakeholders.filter(s => s.stakeholder_type === 'blocker')
    if (blockers.length > 0) decisionScore = 2
    if (decisionHolders.length >= 2) decisionScore = 3
    if (decisionHolders.some(s => s.confirmation_status === 'confirmed_client')) decisionScore = 4
  }

  // Metrics: success_metrics
  let metricsScore = 0
  if (successMetrics.length > 0) {
    metricsScore = 1
    if (successMetrics.some(m => m.monetary_value_low || m.monetary_value_high)) metricsScore = 2
    if (successMetrics.some(m => (m.monetary_confidence ?? 0) > 0.7)) metricsScore = 3
    if (successMetrics.some(m => m.confirmation_status === 'confirmed_client')) metricsScore = 4
  }

  // Timeline: phase progression
  const phaseMap: Record<string, number> = {
    pre_discovery: 0,
    discovery: 1,
    validation: 2,
    prototype: 3,
    proposal: 4,
    closed: 4,
  }
  const timelineScore = phaseMap[collaborationPhase ?? ''] ?? 0

  return [
    { label: 'Pain', score: painScore, sublabel: scoreToSublabel(painScore) },
    { label: 'Champion', score: championScore, sublabel: scoreToSublabel(championScore) },
    { label: 'Econ Buyer', score: econScore, sublabel: scoreToSublabel(econScore) },
    { label: 'Decision', score: decisionScore, sublabel: scoreToSublabel(decisionScore) },
    { label: 'Metrics', score: metricsScore, sublabel: scoreToSublabel(metricsScore) },
    { label: 'Timeline', score: timelineScore, sublabel: scoreToSublabel(timelineScore) },
  ]
}
