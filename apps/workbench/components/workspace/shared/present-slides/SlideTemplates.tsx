'use client'

import type { SolutionFlowStepDetail } from '@/types/workspace'
import { SOLUTION_FLOW_PHASES, PATTERN_LABELS } from '@/lib/solution-flow-constants'
import { getPatternRenderer } from '@/components/workspace/flow/patterns'

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export interface SlideData {
  step: {
    title: string
    goal: string
    actors: string[]
    step_index: number
    phase: string
    info_field_count: number
    confidence_breakdown?: Record<string, number>
  }
  detail: SolutionFlowStepDetail | null
  stepIndex: number
  totalSteps: number
}

// ---------------------------------------------------------------------------
// Shared small components
// ---------------------------------------------------------------------------

function PhaseBadge({ phase }: { phase: string }) {
  const p = SOLUTION_FLOW_PHASES[phase]
  return (
    <span
      className="text-[11px] font-semibold uppercase tracking-wide px-2.5 py-1 rounded inline-block"
      style={{ background: 'rgba(63,175,122,0.1)', color: '#3FAF7A' }}
    >
      {p?.label ?? phase}
    </span>
  )
}

function StepCounter({ index, total }: { index: number; total: number }) {
  return (
    <span className="text-[12px] font-medium" style={{ color: 'rgba(255,255,255,0.3)' }}>
      Step {index + 1} of {total}
    </span>
  )
}

function ActorPills({ actors }: { actors: string[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {actors.map(name => (
        <div
          key={name}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white"
            style={{ background: '#3FAF7A' }}
          >
            {name.split(' ').map(w => w[0]).join('').slice(0, 2)}
          </div>
          <span className="text-xs font-medium" style={{ color: 'rgba(255,255,255,0.6)' }}>{name}</span>
        </div>
      ))}
    </div>
  )
}

function ValueCallout({ text }: { text: string }) {
  return (
    <div
      className="text-[13px] leading-relaxed rounded-[9px] px-4 py-3"
      style={{
        background: 'rgba(63,175,122,0.08)',
        borderLeft: '3px solid #3FAF7A',
        color: 'rgba(255,255,255,0.78)',
      }}
    >
      {text}
    </div>
  )
}

function BeforeAfterGrid({ beforeText, afterText, wide }: { beforeText: string | null; afterText: string | null; wide?: boolean }) {
  if (!beforeText && !afterText) return null
  return (
    <div
      className={`grid overflow-hidden rounded-[9px] ${wide ? 'w-full' : ''}`}
      style={{ gridTemplateColumns: '1fr auto 1fr', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      <div className="p-3.5" style={{ background: 'rgba(4,65,89,0.15)' }}>
        <div className="text-[10px] font-semibold uppercase tracking-wide mb-1.5" style={{ color: 'rgba(255,255,255,0.35)' }}>Before</div>
        <div className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>{beforeText || '\u2014'}</div>
      </div>
      <div className="flex items-center justify-center px-2.5 text-lg" style={{ background: 'rgba(255,255,255,0.02)', color: '#3FAF7A' }}>{'\u2192'}</div>
      <div className="p-3.5" style={{ background: 'rgba(63,175,122,0.08)' }}>
        <div className="text-[10px] font-semibold uppercase tracking-wide mb-1.5" style={{ color: '#3FAF7A' }}>After</div>
        <div className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>{afterText || '\u2014'}</div>
      </div>
    </div>
  )
}

// Helper to extract before/after text from detail
function extractBeforeAfter(d: SolutionFlowStepDetail | null) {
  const painBefore = d?.pain_points_addressed?.[0]
  const beforeText = painBefore ? (typeof painBefore === 'string' ? painBefore : painBefore.text) : null
  const afterText = d?.goals_addressed?.[0] || d?.success_criteria?.[0] || null
  return { beforeText, afterText }
}

// ---------------------------------------------------------------------------
// Template 1: HeroSlide
// ---------------------------------------------------------------------------

export function HeroSlide({ step, detail, stepIndex, totalSteps }: SlideData) {
  const { beforeText, afterText } = extractBeforeAfter(detail)
  const valueStatement = detail?.human_value_statement || detail?.ai_config?.human_value_statement

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <PhaseBadge phase={step.phase} />
        <StepCounter index={stepIndex} total={totalSteps} />
      </div>

      {/* Story headline */}
      <h2
        className="text-[28px] font-bold text-white mb-5"
        style={{ letterSpacing: '-0.02em', lineHeight: 1.25 }}
      >
        {detail?.story_headline}
      </h2>

      {/* Before / After - full width */}
      <div className="mb-5">
        <BeforeAfterGrid beforeText={beforeText} afterText={afterText} wide />
      </div>

      {/* Value statement callout */}
      {valueStatement && (
        <div className="mt-5">
          <ValueCallout text={valueStatement} />
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Template 2: SplitSlide
// ---------------------------------------------------------------------------

export function SplitSlide({ step, detail, stepIndex, totalSteps }: SlideData) {
  const PatternComponent = detail?.implied_pattern
    ? getPatternRenderer(detail.implied_pattern)
    : null
  const patternLabel = detail?.implied_pattern ? PATTERN_LABELS[detail.implied_pattern] || detail.implied_pattern : ''
  const fields = (detail?.information_fields || []).map(f => ({
    name: f.name,
    type: f.type,
    mock_value: f.mock_value,
    confidence: f.confidence,
  }))

  return (
    <div className="flex gap-6" style={{ minHeight: 0 }}>
      {/* Left column - 55% */}
      <div className="flex flex-col" style={{ flex: '0 0 55%' }}>
        <div className="flex items-center gap-3 mb-3">
          <PhaseBadge phase={step.phase} />
          <StepCounter index={stepIndex} total={totalSteps} />
        </div>

        <h2
          className="text-[28px] font-bold text-white mb-2"
          style={{ letterSpacing: '-0.02em', lineHeight: 1.25 }}
        >
          {step.title}
        </h2>
        <p className="text-[14px] leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.45)' }}>
          {step.goal}
        </p>

        {/* User actions */}
        {detail?.user_actions && detail.user_actions.length > 0 && (
          <ul className="space-y-1.5 mb-4">
            {detail.user_actions.map((action, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px]" style={{ color: 'rgba(255,255,255,0.7)' }}>
                <span style={{ color: '#3FAF7A', lineHeight: '1.4' }}>{'\u25B8'}</span>
                <span>{action}</span>
              </li>
            ))}
          </ul>
        )}

        {/* Actor pills */}
        <ActorPills actors={step.actors} />
      </div>

      {/* Right column - 45% pattern preview */}
      <div style={{ flex: '0 0 45%' }}>
        {/* Mini browser chrome */}
        <div
          className="rounded-t-[8px] flex items-center gap-1.5 px-3 py-2"
          style={{ background: 'rgba(255,255,255,0.06)' }}
        >
          <div className="w-[7px] h-[7px] rounded-full" style={{ background: '#FF5F57' }} />
          <div className="w-[7px] h-[7px] rounded-full" style={{ background: '#FEBC2E' }} />
          <div className="w-[7px] h-[7px] rounded-full" style={{ background: '#28C840' }} />
          <span className="text-[10px] ml-2 font-medium" style={{ color: 'rgba(255,255,255,0.3)' }}>
            {patternLabel}
          </span>
        </div>

        {/* Pattern render area */}
        <div
          className="rounded-b-[8px] overflow-hidden"
          style={{
            background: 'rgba(255,255,255,0.025)',
            border: '1px solid rgba(255,255,255,0.06)',
            borderTop: 'none',
            width: '100%',
            height: 220,
          }}
        >
          {PatternComponent && detail && (
            <div style={{ width: 300, height: 220, overflow: 'hidden' }}>
              <div style={{ transform: 'scale(0.55)', transformOrigin: 'top left' }}>
                <PatternComponent
                  fields={fields}
                  step={{ title: step.title, actors: step.actors }}
                  detail={detail}
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Template 3: DataSlide
// ---------------------------------------------------------------------------

const CONFIDENCE_COLORS: Record<string, string> = {
  known: '#3FAF7A',
  inferred: 'rgba(10,30,47,0.6)',
  guess: '#BBBBBB',
  unknown: '#555555',
}

export function DataSlide({ step, detail, stepIndex, totalSteps }: SlideData) {
  const fields = detail?.information_fields || []
  const displayFields = fields.filter(f => f.type === 'displayed' || f.type === 'computed').slice(0, 5)
  // If not enough displayed/computed, fill with captured
  const kpiFields = displayFields.length >= 3
    ? displayFields
    : [...displayFields, ...fields.filter(f => !displayFields.includes(f)).slice(0, 5 - displayFields.length)]

  const breakdown = step.confidence_breakdown || {}
  const total = Object.values(breakdown).reduce((s, v) => s + v, 0) || 1
  const knownCount = (breakdown.known || 0)
  const confirmedPct = total > 0 ? Math.round((knownCount / total) * 100) : 0

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <PhaseBadge phase={step.phase} />
        <StepCounter index={stepIndex} total={totalSteps} />
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded-full ml-auto"
          style={{ background: 'rgba(63,175,122,0.1)', color: '#3FAF7A' }}
        >
          {fields.length} fields
        </span>
      </div>

      <h2
        className="text-[28px] font-bold text-white mb-1.5"
        style={{ letterSpacing: '-0.02em', lineHeight: 1.25 }}
      >
        {step.title}
      </h2>
      <p className="text-[14px] leading-relaxed mb-6" style={{ color: 'rgba(255,255,255,0.45)' }}>
        {step.goal}
      </p>

      {/* KPI cards */}
      <div className="flex gap-2.5 mb-6">
        {kpiFields.map((f, i) => (
          <div
            key={i}
            className="flex-1 p-3.5 rounded-[9px] min-w-0"
            style={{ background: 'rgba(255,255,255,0.035)', border: '1px solid rgba(255,255,255,0.05)' }}
          >
            <div
              className="text-[18px] font-bold mb-1 truncate"
              style={{ color: '#3FAF7A' }}
            >
              {f.mock_value || '\u2014'}
            </div>
            <div className="text-[10px] uppercase tracking-wide truncate" style={{ color: 'rgba(255,255,255,0.4)' }}>
              {f.name}
            </div>
          </div>
        ))}
      </div>

      {/* Confidence bar */}
      <div className="mb-3">
        <div className="flex rounded-full overflow-hidden h-[6px]" style={{ background: 'rgba(255,255,255,0.05)' }}>
          {(['known', 'inferred', 'guess', 'unknown'] as const).map(level => {
            const count = breakdown[level] || 0
            if (count === 0) return null
            const pct = (count / total) * 100
            return (
              <div
                key={level}
                style={{ width: `${pct}%`, background: CONFIDENCE_COLORS[level] }}
              />
            )
          })}
        </div>
      </div>

      {/* Label */}
      <div className="text-[12px]" style={{ color: 'rgba(255,255,255,0.35)' }}>
        {fields.length} data points &middot; {confirmedPct}% confirmed
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Template 4: AgentSpotlightSlide
// ---------------------------------------------------------------------------

const AGENT_ICON_MAP: Record<string, string> = {
  classifier: '\u25C8',
  matcher: '\u2B22',
  predictor: '\u25C7',
  watcher: '\u25C9',
  generator: '\u25C6',
  processor: '\u2B21',
}

export function AgentSpotlightSlide({ step, detail }: SlideData) {
  const ai = detail?.ai_config
  if (!ai) return null

  const agentType = ai.agent_type || 'processor'
  const icon = AGENT_ICON_MAP[agentType] || '\u25C6'
  const automationPct = ai.automation_estimate ?? 0
  const behaviors = ai.behaviors || []
  const valueStatement = detail?.human_value_statement || ai.human_value_statement

  // SVG donut params
  const radius = 44
  const circumference = 2 * Math.PI * radius
  const filledLength = (automationPct / 100) * circumference
  const gapLength = circumference - filledLength

  return (
    <div className="flex gap-8 items-start">
      {/* Left: agent identity + donut */}
      <div className="flex flex-col items-center" style={{ flex: '0 0 180px' }}>
        {/* Agent icon */}
        <div
          className="w-16 h-16 rounded-full flex items-center justify-center text-[28px] mb-4"
          style={{ background: 'rgba(63,175,122,0.1)', color: '#3FAF7A' }}
        >
          {icon}
        </div>

        {/* Automation donut */}
        <div className="relative" style={{ width: 110, height: 110 }}>
          <svg width="110" height="110" viewBox="0 0 110 110">
            {/* Background ring */}
            <circle
              cx="55" cy="55" r={radius}
              fill="none"
              stroke="rgba(255,255,255,0.06)"
              strokeWidth="7"
            />
            {/* Filled ring */}
            <circle
              cx="55" cy="55" r={radius}
              fill="none"
              stroke="#3FAF7A"
              strokeWidth="7"
              strokeDasharray={`${filledLength} ${gapLength}`}
              strokeDashoffset={circumference * 0.25}
              strokeLinecap="round"
              style={{ transition: 'stroke-dasharray 0.6s ease' }}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[20px] font-bold text-white">{automationPct}%</span>
            <span className="text-[9px] uppercase tracking-wide" style={{ color: 'rgba(255,255,255,0.35)' }}>automated</span>
          </div>
        </div>
      </div>

      {/* Right: name, role, behaviors, value */}
      <div className="flex-1 min-w-0">
        <h2
          className="text-[28px] font-bold text-white mb-1"
          style={{ letterSpacing: '-0.02em', lineHeight: 1.25 }}
        >
          {ai.agent_name}
        </h2>
        <p className="text-[14px] mb-5" style={{ color: 'rgba(255,255,255,0.45)' }}>
          {ai.role || ai.ai_role || step.goal}
        </p>

        {/* Behaviors */}
        {behaviors.length > 0 && (
          <ul className="space-y-1.5 mb-5">
            {behaviors.map((b, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px]" style={{ color: 'rgba(255,255,255,0.7)' }}>
                <span style={{ color: '#3FAF7A', lineHeight: '1.4' }}>{'\u25B8'}</span>
                <span>{b}</span>
              </li>
            ))}
          </ul>
        )}

        {/* Value statement */}
        {valueStatement && <ValueCallout text={valueStatement} />}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Template 5: DefaultSlide
// ---------------------------------------------------------------------------

export function DefaultSlide({ step, detail, stepIndex, totalSteps }: SlideData) {
  const { beforeText, afterText } = extractBeforeAfter(detail)
  const narrative = detail?.story_headline || (detail?.mock_data_narrative ? detail.mock_data_narrative.split('. ')[0] + '.' : null)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-2">
        <PhaseBadge phase={step.phase} />
        <StepCounter index={stepIndex} total={totalSteps} />
      </div>

      <h2
        className="text-[34px] font-bold text-white mb-2"
        style={{ letterSpacing: '-0.02em', lineHeight: 1.2 }}
      >
        {step.title}
      </h2>
      <p className="text-[15px] leading-relaxed mb-5" style={{ color: 'rgba(255,255,255,0.45)' }}>
        {step.goal}
      </p>

      {/* Narrative */}
      {narrative && (
        <div
          className="text-[15px] leading-[1.7] rounded-[10px] p-4.5 mb-5"
          style={{
            color: 'rgba(255,255,255,0.78)',
            background: 'rgba(255,255,255,0.035)',
            borderLeft: '3px solid #3FAF7A',
          }}
        >
          {narrative}
        </div>
      )}

      {/* Before / After */}
      {(beforeText || afterText) && (
        <div className="mb-5">
          <BeforeAfterGrid beforeText={beforeText} afterText={afterText} />
        </div>
      )}

      {/* Actors */}
      <div className="mb-4">
        <ActorPills actors={step.actors} />
      </div>

      {/* AI Role */}
      {(detail?.ai_config?.role || detail?.ai_config?.ai_role) && (
        <div
          className="text-[13px] leading-relaxed p-3.5 rounded-[9px]"
          style={{
            color: 'rgba(255,255,255,0.55)',
            fontStyle: 'italic',
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.04)',
          }}
        >
          <span style={{ color: '#3FAF7A', fontWeight: 600, fontStyle: 'normal' }}>AI: </span>
          {detail?.ai_config?.role || detail?.ai_config?.ai_role}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Classifier
// ---------------------------------------------------------------------------

export function classifySlideTemplate(
  step: { info_field_count: number; confidence_breakdown?: Record<string, number> },
  detail: SolutionFlowStepDetail | null
): 'hero' | 'split' | 'data' | 'agent_spotlight' | 'default' {
  // Hero: story headline + both before & after present
  if (detail?.story_headline) {
    const painBefore = detail.pain_points_addressed?.[0]
    const hasAfter = !!(detail.goals_addressed?.[0])
    if (painBefore && hasAfter) return 'hero'
  }

  // Split: implied pattern + has information fields
  if (detail?.implied_pattern && detail.information_fields && detail.information_fields.length > 0) {
    return 'split'
  }

  // Data: 4+ information fields
  if (detail?.information_fields && detail.information_fields.length >= 4) {
    return 'data'
  }

  // Agent spotlight: ai_config.agent_name + behaviors
  if (detail?.ai_config?.agent_name && detail.ai_config.behaviors && detail.ai_config.behaviors.length > 0) {
    return 'agent_spotlight'
  }

  return 'default'
}
