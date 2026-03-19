'use client'

/**
 * AgentOutputRenderer — Maps agent_type to styled card renderers.
 *
 * Renders the structured output from the execute_agent_demo Haiku chain
 * as visually rich cards for the Try It panel.
 */

import type { AgentType } from '@/types/workspace'

interface Props {
  agentType: AgentType
  output: Record<string, unknown>
  executionTimeMs: number
  hideFooter?: boolean
}

// ── Confidence badge ────────────────────────────────────────────

function ConfBadge({ value }: { value: number }) {
  const pct = Math.round(value * 100)
  const color =
    pct >= 80 ? '#1B6B3A' : pct >= 50 ? '#8B6914' : '#9B2C2C'
  const bg =
    pct >= 80
      ? 'rgba(63,175,122,0.12)'
      : pct >= 50
        ? 'rgba(212,160,23,0.12)'
        : 'rgba(220,80,80,0.12)'

  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold"
      style={{ color, background: bg }}
    >
      {pct}%
    </span>
  )
}

// ── Severity badge (for watcher) ────────────────────────────────

function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, { color: string; bg: string }> = {
    critical: { color: '#9B2C2C', bg: 'rgba(220,80,80,0.12)' },
    warning: { color: '#8B6914', bg: 'rgba(212,160,23,0.12)' },
    advisory: { color: '#044159', bg: 'rgba(4,65,89,0.10)' },
  }
  const s = map[severity] || map.advisory

  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide"
      style={{ color: s.color, background: s.bg }}
    >
      {severity}
    </span>
  )
}

// ── Classifier output ───────────────────────────────────────────

function ClassifierOutput({ output }: { output: Record<string, unknown> }) {
  const entities = (output.entities || []) as Array<{
    name: string
    category: string
    confidence: number
    evidence: string
    reasoning: string
  }>
  const summary = output.summary as string

  return (
    <div className="space-y-3">
      {summary && (
        <p className="text-[12px] text-[#4A5568] leading-relaxed">{summary}</p>
      )}
      {entities.map((e, i) => (
        <div
          key={i}
          className="rounded-lg p-3"
          style={{ background: 'rgba(4,65,89,0.04)', border: '1px solid rgba(4,65,89,0.08)' }}
        >
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <span className="text-[12px] font-semibold text-[#0A1E2F]">{e.name}</span>
              <span
                className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                style={{ background: 'rgba(63,175,122,0.12)', color: '#1B6B3A' }}
              >
                {e.category}
              </span>
            </div>
            <ConfBadge value={e.confidence} />
          </div>
          <p className="text-[11px] text-[#718096] italic mb-1">&ldquo;{e.evidence}&rdquo;</p>
          <p className="text-[11px] text-[#4A5568]">{e.reasoning}</p>
        </div>
      ))}
    </div>
  )
}

// ── Matcher output ──────────────────────────────────────────────

function MatcherOutput({ output }: { output: Record<string, unknown> }) {
  const matches = (output.matches || []) as Array<{
    source: string
    target: string
    similarity: number
    match_type: string
    reasoning: string
  }>
  const unmatched = (output.unmatched || []) as string[]
  const summary = output.summary as string

  return (
    <div className="space-y-3">
      {summary && (
        <p className="text-[12px] text-[#4A5568] leading-relaxed">{summary}</p>
      )}
      {matches.map((m, i) => (
        <div
          key={i}
          className="rounded-lg p-3"
          style={{ background: 'rgba(4,65,89,0.04)', border: '1px solid rgba(4,65,89,0.08)' }}
        >
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[12px] font-semibold text-[#0A1E2F]">{m.source}</span>
            <span className="text-[10px] text-[#A0AEC0]">→</span>
            <span className="text-[12px] font-semibold text-[#3FAF7A]">{m.target}</span>
            <ConfBadge value={m.similarity} />
            <span className="text-[10px] text-[#718096]">{m.match_type}</span>
          </div>
          <p className="text-[11px] text-[#4A5568]">{m.reasoning}</p>
        </div>
      ))}
      {unmatched.length > 0 && (
        <div className="pt-1">
          <p className="text-[10px] font-medium text-[#A0AEC0] uppercase tracking-wide mb-1">Unmatched</p>
          <div className="flex flex-wrap gap-1">
            {unmatched.map((u, i) => (
              <span
                key={i}
                className="px-2 py-0.5 rounded text-[10px] text-[#718096]"
                style={{ background: 'rgba(0,0,0,0.04)' }}
              >
                {u}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Predictor output ────────────────────────────────────────────

function PredictorOutput({ output }: { output: Record<string, unknown> }) {
  const predictions = (output.predictions || []) as Array<{
    prediction: string
    confidence: number
    timeframe: string
    risk_factors: string[]
    evidence_basis: string
  }>
  const outlook = output.overall_outlook as string

  return (
    <div className="space-y-3">
      {outlook && (
        <p className="text-[12px] text-[#4A5568] leading-relaxed">{outlook}</p>
      )}
      {predictions.map((p, i) => (
        <div
          key={i}
          className="rounded-lg p-3"
          style={{ background: 'rgba(4,65,89,0.04)', border: '1px solid rgba(4,65,89,0.08)' }}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[12px] font-semibold text-[#0A1E2F] flex-1">{p.prediction}</span>
            <ConfBadge value={p.confidence} />
          </div>
          <div className="flex items-center gap-3 mb-1.5">
            <span className="text-[10px] text-[#718096]">⏱ {p.timeframe}</span>
          </div>
          <p className="text-[11px] text-[#4A5568] mb-1.5">{p.evidence_basis}</p>
          {p.risk_factors.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {p.risk_factors.map((r, j) => (
                <span
                  key={j}
                  className="px-1.5 py-0.5 rounded text-[10px]"
                  style={{ background: 'rgba(220,80,80,0.08)', color: '#9B2C2C' }}
                >
                  {r}
                </span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Watcher output ──────────────────────────────────────────────

function WatcherOutput({ output }: { output: Record<string, unknown> }) {
  const alerts = (output.alerts || []) as Array<{
    title: string
    severity: string
    description: string
    recommended_action: string
    evidence: string
  }>
  const riskLevel = output.risk_level as string
  const summary = output.summary as string

  return (
    <div className="space-y-3">
      {summary && (
        <div className="flex items-center gap-2">
          <p className="text-[12px] text-[#4A5568] leading-relaxed flex-1">{summary}</p>
          {riskLevel && (
            <SeverityBadge severity={riskLevel} />
          )}
        </div>
      )}
      {alerts.map((a, i) => (
        <div
          key={i}
          className="rounded-lg p-3"
          style={{
            background:
              a.severity === 'critical'
                ? 'rgba(220,80,80,0.04)'
                : a.severity === 'warning'
                  ? 'rgba(212,160,23,0.04)'
                  : 'rgba(4,65,89,0.04)',
            border: `1px solid ${
              a.severity === 'critical'
                ? 'rgba(220,80,80,0.15)'
                : a.severity === 'warning'
                  ? 'rgba(212,160,23,0.15)'
                  : 'rgba(4,65,89,0.08)'
            }`,
          }}
        >
          <div className="flex items-center gap-2 mb-1.5">
            <SeverityBadge severity={a.severity} />
            <span className="text-[12px] font-semibold text-[#0A1E2F]">{a.title}</span>
          </div>
          <p className="text-[11px] text-[#4A5568] mb-1.5">{a.description}</p>
          <p className="text-[11px] text-[#718096] italic mb-1.5">&ldquo;{a.evidence}&rdquo;</p>
          <div
            className="rounded px-2 py-1.5 text-[11px] font-medium"
            style={{ background: 'rgba(63,175,122,0.08)', color: '#1B6B3A' }}
          >
            → {a.recommended_action}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Generator output ────────────────────────────────────────────

function GeneratorOutput({ output }: { output: Record<string, unknown> }) {
  const sections = (output.sections || []) as Array<{
    heading: string
    content: string
    source_basis: string
    confidence: number
  }>
  const narrative = output.narrative as string

  return (
    <div className="space-y-3">
      {narrative && (
        <p className="text-[12px] text-[#4A5568] leading-relaxed">{narrative}</p>
      )}
      {sections.map((s, i) => (
        <div
          key={i}
          className="rounded-lg p-3"
          style={{
            background: 'rgba(63,175,122,0.03)',
            borderLeft: '3px solid #3FAF7A',
          }}
        >
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[12px] font-semibold text-[#0A1E2F]">{s.heading}</span>
            <ConfBadge value={s.confidence} />
          </div>
          <p className="text-[12px] text-[#2D3748] leading-relaxed mb-1.5">{s.content}</p>
          <p className="text-[10px] text-[#A0AEC0]">Based on: {s.source_basis}</p>
        </div>
      ))}
    </div>
  )
}

// ── Processor output ────────────────────────────────────────────

function ProcessorOutput({ output }: { output: Record<string, unknown> }) {
  const entities = (output.entities || []) as Array<{
    name: string
    type: string
    confidence: number
    evidence: string
  }>
  const probes = (output.probes || []) as Array<{
    question: string
    rationale: string
    target: string
  }>
  const summary = output.summary as string

  return (
    <div className="space-y-3">
      {summary && (
        <p className="text-[12px] text-[#4A5568] leading-relaxed">{summary}</p>
      )}

      {entities.length > 0 && (
        <div>
          <p className="text-[10px] font-medium text-[#A0AEC0] uppercase tracking-wide mb-2">
            Extracted Entities
          </p>
          <div className="space-y-2">
            {entities.map((e, i) => (
              <div
                key={i}
                className="flex items-center gap-2 rounded-lg px-3 py-2"
                style={{ background: 'rgba(4,65,89,0.04)', border: '1px solid rgba(4,65,89,0.08)' }}
              >
                <span
                  className="px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0"
                  style={{ background: 'rgba(63,175,122,0.12)', color: '#1B6B3A' }}
                >
                  {e.type}
                </span>
                <span className="text-[12px] font-medium text-[#0A1E2F] flex-1">{e.name}</span>
                <ConfBadge value={e.confidence} />
              </div>
            ))}
          </div>
        </div>
      )}

      {probes.length > 0 && (
        <div>
          <p className="text-[10px] font-medium text-[#A0AEC0] uppercase tracking-wide mb-2">
            Discovery Probes
          </p>
          <div className="space-y-2">
            {probes.map((p, i) => (
              <div
                key={i}
                className="rounded-lg p-3"
                style={{ background: 'rgba(212,160,23,0.04)', borderLeft: '3px solid #D4A017' }}
              >
                <p className="text-[12px] font-medium text-[#0A1E2F] mb-1">{p.question}</p>
                <p className="text-[11px] text-[#4A5568] mb-1">{p.rationale}</p>
                <p className="text-[10px] text-[#8B6914]">Ask: {p.target}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main renderer ───────────────────────────────────────────────

const RENDERERS: Record<AgentType, React.FC<{ output: Record<string, unknown> }>> = {
  classifier: ClassifierOutput,
  matcher: MatcherOutput,
  predictor: PredictorOutput,
  watcher: WatcherOutput,
  generator: GeneratorOutput,
  processor: ProcessorOutput,
}

export function AgentOutputRenderer({ agentType, output, executionTimeMs, hideFooter }: Props) {
  const Renderer = RENDERERS[agentType]

  if (!Renderer) {
    return (
      <div className="p-4 text-[12px] text-[#718096]">
        Unknown agent type: {agentType}
      </div>
    )
  }

  // Check for error
  if (output.error) {
    return (
      <div className="p-4 rounded-lg" style={{ background: 'rgba(220,80,80,0.06)' }}>
        <p className="text-[12px] text-[#9B2C2C]">{output.error as string}</p>
      </div>
    )
  }

  return (
    <div>
      <Renderer output={output} />
      {!hideFooter && (
        <div className="mt-3 pt-2 border-t border-[rgba(0,0,0,0.06)] flex items-center justify-between">
          <span className="text-[10px] text-[#A0AEC0]">
            Processed in {executionTimeMs}ms
          </span>
          <span className="text-[10px] text-[#A0AEC0]">
            Readytogo Agents
          </span>
        </div>
      )}
    </div>
  )
}
