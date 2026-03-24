'use client'

import type { AgentType } from '@/types/workspace'

interface Props {
  statement: string | null
  agentType: AgentType
  agentName: string
  automationRate: number
  humanPartner?: string
}

const GENERIC_STATEMENTS: Record<AgentType, string> = {
  classifier: 'Automates entity sorting and categorization so your team can focus on strategic decisions.',
  matcher: 'Surfaces hidden connections between requirements, saving hours of manual cross-referencing.',
  predictor: 'Forecasts outcomes and risks before they become problems, giving your team time to act.',
  watcher: 'Continuously monitors for anomalies and alerts, replacing manual spot-checks.',
  generator: 'Compiles structured reports and narratives from raw data in seconds, not hours.',
  processor: 'Transforms unstructured signals into actionable entities, eliminating manual data entry.',
  orchestrator: "Coordinates intelligent capabilities to achieve the product's goals.",
}

export function HumanValueCallout({ statement, agentType, agentName, automationRate, humanPartner }: Props) {
  const displayStatement = statement || GENERIC_STATEMENTS[agentType] || GENERIC_STATEMENTS.processor

  return (
    <div
      className="px-5 py-3"
      style={{ background: 'rgba(4,65,89,0.03)', borderLeft: '3px solid #044159' }}
    >
      <div className="text-[8px] font-semibold uppercase tracking-wide mb-1" style={{ color: '#A0AEC0' }}>
        Human Value
      </div>
      <div className="text-[11px] leading-relaxed" style={{ color: '#2D3748' }}>
        {displayStatement}
      </div>
      {humanPartner && (
        <div className="text-[9px] mt-1" style={{ color: '#718096' }}>
          Working with {humanPartner} &middot; {automationRate}% automated
        </div>
      )}
    </div>
  )
}
