'use client'

import { useMemo } from 'react'
import type {
  SolutionFlowStepSummary,
  SolutionFlowStepDetail,
  DerivedAgent,
  PersonaSummary,
} from '@/types/workspace'
import {
  PHASE_ORDER,
  SOLUTION_FLOW_PHASES,
  LANE_CONFIG,
  PHASE_CARD_STYLE,
} from '@/lib/solution-flow-constants'

interface OnePagerViewProps {
  steps: SolutionFlowStepSummary[]
  stepDetails: Map<string, SolutionFlowStepDetail>
  agents?: DerivedAgent[]
  personas: PersonaSummary[]
  flowSummary: string
  projectName?: string
  onClose: () => void
}

export function OnePagerView({
  steps,
  stepDetails,
  agents,
  personas,
  flowSummary,
  projectName,
  onClose,
}: OnePagerViewProps) {
  const today = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })

  const stepsByPhase = useMemo(() => {
    const grouped: Record<string, SolutionFlowStepSummary[]> = {}
    for (const step of steps) {
      const phase = step.phase || 'core_experience'
      if (!grouped[phase]) grouped[phase] = []
      grouped[phase].push(step)
    }
    // Sort steps within each phase by step_index
    for (const phase of Object.keys(grouped)) {
      grouped[phase].sort((a, b) => a.step_index - b.step_index)
    }
    return grouped
  }, [steps])

  const activePhases = useMemo(
    () => PHASE_ORDER.filter(p => stepsByPhase[p]?.length),
    [stepsByPhase]
  )

  const avgAutomation = useMemo(() => {
    if (!agents?.length) return null
    const total = agents.reduce((sum, a) => sum + (a.automationRate ?? 0), 0)
    return Math.round(total / agents.length)
  }, [agents])

  return (
    <>
      <style jsx>{`
        @media print {
          .no-print {
            display: none !important;
          }
          .one-pager-root {
            box-shadow: none !important;
            max-width: 100% !important;
            padding: 0 !important;
          }
          .step-card {
            box-shadow: none !important;
            border-width: 1px !important;
          }
          .agent-card {
            box-shadow: none !important;
          }
          .phase-section + .phase-section {
            page-break-before: always;
          }
          @page {
            margin: 1cm;
          }
        }
      `}</style>

      <div
        className="one-pager-root fixed inset-0 z-[1100] overflow-y-auto"
        style={{ background: '#FFFFFF' }}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="no-print fixed top-4 right-4 z-10 w-8 h-8 flex items-center justify-center rounded-full cursor-pointer transition-colors"
          style={{
            background: '#F7FAFC',
            border: '1px solid #E2E8F0',
            color: '#718096',
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = '#EDF2F7'
            e.currentTarget.style.color = '#0A1E2F'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = '#F7FAFC'
            e.currentTarget.style.color = '#718096'
          }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>

        <div style={{ maxWidth: 900, margin: '0 auto', padding: '40px 32px 60px' }}>
          {/* ── Header ── */}
          <div style={{ borderBottom: '1px solid #E2E8F0', paddingBottom: 20, marginBottom: 28 }}>
            <h1 style={{ fontSize: 20, fontWeight: 700, color: '#0A1E2F', margin: 0, lineHeight: 1.3 }}>
              {projectName || 'Solution Blueprint'}
            </h1>
            <p style={{ fontSize: 11, color: '#718096', margin: '4px 0 0' }}>
              Generated {today}
            </p>
            {flowSummary && (
              <p style={{ fontSize: 13, color: '#4A5568', margin: '12px 0 0', lineHeight: 1.55 }}>
                {flowSummary}
              </p>
            )}
            <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
              <StatPill label="Steps" value={steps.length} />
              <StatPill label="Personas" value={personas.length} />
              <StatPill label="Phases" value={activePhases.length} />
            </div>
          </div>

          {/* ── Steps by Phase ── */}
          {activePhases.map((phase, phaseIdx) => {
            const phaseSteps = stepsByPhase[phase] || []
            const style = PHASE_CARD_STYLE[phase]
            const phaseConfig = SOLUTION_FLOW_PHASES[phase]
            const laneConfig = LANE_CONFIG[phase]
            const phaseColor = style?.idxColor || '#0A1E2F'

            return (
              <div
                key={phase}
                className={`phase-section${phaseIdx > 0 ? ' phase-section' : ''}`}
                style={{ marginBottom: 28 }}
              >
                {/* Phase header */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                  <div
                    style={{
                      width: 3,
                      height: 22,
                      borderRadius: 2,
                      background: phaseColor,
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: 14, fontWeight: 700, color: phaseColor }}>
                    {laneConfig?.label || phaseConfig?.fullLabel || phase}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      color: phaseColor,
                      background: `${phaseColor}10`,
                      padding: '2px 7px',
                      borderRadius: 10,
                    }}
                  >
                    {phaseSteps.length}
                  </span>
                </div>

                {/* Step cards */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {phaseSteps.map(step => {
                    const detail = stepDetails.get(step.id)
                    const aiConfig = detail?.ai_config
                    const storyHeadline = detail?.story_headline
                    const userActions = detail?.user_actions
                    const humanValue = detail?.human_value_statement

                    // Build transformation text
                    let transformBefore: string | null = null
                    let transformAfter: string | null = null
                    if (agents?.length) {
                      const matchingAgent = agents.find(a => a.sourceStepId === step.id)
                      if (matchingAgent?.transform) {
                        transformBefore = matchingAgent.transform.before
                        transformAfter = matchingAgent.transform.after
                      }
                    }

                    return (
                      <div
                        key={step.id}
                        className="step-card"
                        style={{
                          padding: '12px 14px',
                          borderRadius: 8,
                          border: '1px solid #E2E8F0',
                          borderLeft: `3px solid ${phaseColor}`,
                          background: '#FFFFFF',
                          pageBreakInside: 'avoid',
                        }}
                      >
                        {/* Title row */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          {/* Index badge */}
                          <div
                            style={{
                              width: 20,
                              height: 20,
                              borderRadius: '50%',
                              background: `${phaseColor}14`,
                              color: phaseColor,
                              fontSize: 10,
                              fontWeight: 700,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              flexShrink: 0,
                            }}
                          >
                            {step.step_index}
                          </div>
                          <span style={{ fontSize: 13, fontWeight: 700, color: '#0A1E2F', flex: 1 }}>
                            {step.title}
                          </span>
                          {/* Actors */}
                          <div style={{ display: 'flex', gap: 4, flexShrink: 0, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                            {step.actors?.map(actor => (
                              <span
                                key={actor}
                                style={{
                                  fontSize: 9,
                                  color: '#4A5568',
                                  background: '#F7FAFC',
                                  border: '1px solid #E2E8F0',
                                  borderRadius: 4,
                                  padding: '1px 5px',
                                  whiteSpace: 'nowrap',
                                }}
                              >
                                {actor}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Story headline */}
                        {storyHeadline && (
                          <p style={{ fontSize: 11, color: '#4A5568', fontStyle: 'italic', margin: '6px 0 0 28px', lineHeight: 1.45 }}>
                            {storyHeadline}
                          </p>
                        )}

                        {/* User actions */}
                        {userActions && userActions.length > 0 && (
                          <div style={{ margin: '5px 0 0 28px', display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                            {userActions.map((action, i) => (
                              <span key={i} style={{ fontSize: 10, color: '#2D3748' }}>
                                <span style={{ color: '#3FAF7A', marginRight: 3 }}>{'\u25B8'}</span>
                                {action}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Bottom row: transformation + AI badge */}
                        {(transformBefore || aiConfig) && (
                          <div
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              margin: '6px 0 0 28px',
                              gap: 12,
                            }}
                          >
                            {/* Transformation */}
                            {transformBefore && transformAfter ? (
                              <span style={{ fontSize: 10, color: '#718096', flex: 1, minWidth: 0 }}>
                                Before:{' '}
                                <span style={{ textDecoration: 'line-through', color: '#A0AEC0' }}>
                                  &ldquo;{transformBefore}&rdquo;
                                </span>
                                {' \u2192 '}
                                After:{' '}
                                <span style={{ color: '#3FAF7A' }}>
                                  &ldquo;{transformAfter}&rdquo;
                                </span>
                              </span>
                            ) : (
                              <span />
                            )}

                            {/* AI badge */}
                            {aiConfig?.agent_name && (
                              <span
                                style={{
                                  fontSize: 9,
                                  color: '#044159',
                                  background: 'rgba(4,65,89,0.06)',
                                  border: '1px solid rgba(4,65,89,0.12)',
                                  borderRadius: 10,
                                  padding: '2px 7px',
                                  whiteSpace: 'nowrap',
                                  flexShrink: 0,
                                }}
                              >
                                AI: {aiConfig.agent_name}
                                {aiConfig.automation_estimate != null && (
                                  <> &middot; {aiConfig.automation_estimate}%</>
                                )}
                              </span>
                            )}
                          </div>
                        )}

                        {/* Human value statement */}
                        {humanValue && (
                          <p style={{ fontSize: 10, color: '#2A8F5F', fontStyle: 'italic', margin: '5px 0 0 28px' }}>
                            {humanValue}
                          </p>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}

          {/* ── AI Team ── */}
          {agents && agents.length > 0 && (
            <div style={{ marginBottom: 28 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                <div
                  style={{
                    width: 3,
                    height: 22,
                    borderRadius: 2,
                    background: '#044159',
                    flexShrink: 0,
                  }}
                />
                <span style={{ fontSize: 14, fontWeight: 700, color: '#044159' }}>AI Team</span>
                <span
                  style={{
                    fontSize: 10,
                    fontWeight: 600,
                    color: '#044159',
                    background: 'rgba(4,65,89,0.08)',
                    padding: '2px 7px',
                    borderRadius: 10,
                  }}
                >
                  {agents.length}
                </span>
              </div>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(3, 1fr)',
                  gap: 10,
                }}
              >
                {agents.map(agent => (
                  <div
                    key={agent.id}
                    className="agent-card"
                    style={{
                      padding: '10px 12px',
                      borderRadius: 8,
                      border: '1px solid #E2E8F0',
                      background: '#FFFFFF',
                      pageBreakInside: 'avoid',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <span style={{ fontSize: 14 }}>{agent.icon}</span>
                      <span style={{ fontSize: 12, fontWeight: 700, color: '#0A1E2F', flex: 1 }}>
                        {agent.name}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                      <span
                        style={{
                          fontSize: 9,
                          color: '#044159',
                          background: 'rgba(4,65,89,0.06)',
                          padding: '1px 5px',
                          borderRadius: 4,
                          textTransform: 'capitalize',
                        }}
                      >
                        {agent.type}
                      </span>
                      <span style={{ fontSize: 9, color: '#3FAF7A', fontWeight: 600 }}>
                        {agent.automationRate}%
                      </span>
                    </div>
                    <p
                      style={{
                        fontSize: 10,
                        color: '#4A5568',
                        margin: 0,
                        lineHeight: 1.4,
                        overflow: 'hidden',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                      }}
                    >
                      {agent.role}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Statistics Footer ── */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: avgAutomation != null ? 'repeat(3, 1fr)' : 'repeat(2, 1fr)',
              gap: 10,
              marginBottom: 28,
            }}
          >
            <FooterStat label="Total Steps" value={steps.length} />
            <FooterStat label="Personas" value={personas.length} />
            {avgAutomation != null && <FooterStat label="Avg Automation" value={`${avgAutomation}%`} />}
          </div>

          {/* ── Download button ── */}
          <button
            onClick={() => window.print()}
            className="no-print"
            style={{
              width: '100%',
              padding: '12px 0',
              borderRadius: 8,
              border: 'none',
              background: '#3FAF7A',
              color: '#FFFFFF',
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background 150ms',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = '#2A8F5F')}
            onMouseLeave={e => (e.currentTarget.style.background = '#3FAF7A')}
          >
            Download as PDF
          </button>
        </div>
      </div>
    </>
  )
}

/* ── Small helpers ── */

function StatPill({ label, value }: { label: string; value: number }) {
  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        color: '#2D3748',
        background: '#F7FAFC',
        border: '1px solid #E2E8F0',
        borderRadius: 10,
        padding: '3px 9px',
      }}
    >
      {value} {label}
    </span>
  )
}

function FooterStat({ label, value }: { label: string; value: number | string }) {
  return (
    <div
      style={{
        padding: '14px 16px',
        borderRadius: 8,
        background: 'rgba(63,175,122,0.05)',
        border: '1px solid rgba(63,175,122,0.12)',
        textAlign: 'center',
      }}
    >
      <div style={{ fontSize: 20, fontWeight: 700, color: '#0A1E2F' }}>{value}</div>
      <div style={{ fontSize: 10, color: '#718096', marginTop: 2 }}>{label}</div>
    </div>
  )
}
