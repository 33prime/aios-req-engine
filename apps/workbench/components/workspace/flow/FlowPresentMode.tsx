'use client'

import { useState, useEffect } from 'react'
import type { SolutionFlowStepSummary, SolutionFlowStepDetail, PersonaSummary } from '@/types/workspace'
import { SOLUTION_FLOW_PHASES } from '@/lib/solution-flow-constants'
import { PresentModeShell } from '@/components/workspace/shared/PresentModeShell'
import { getSolutionFlowStep } from '@/lib/api/admin'

interface FlowPresentModeProps {
  isOpen: boolean
  onClose: () => void
  steps: SolutionFlowStepSummary[]
  personas: PersonaSummary[]
  flowSummary: string
  projectId: string
}

export function FlowPresentMode({
  isOpen,
  onClose,
  steps,
  personas,
  flowSummary,
  projectId,
}: FlowPresentModeProps) {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [stepDetails, setStepDetails] = useState<Map<string, SolutionFlowStepDetail>>(new Map())
  const [fetching, setFetching] = useState(false)

  // Total: title + steps + summary
  const totalSlides = steps.length + 2

  // Fetch all step details on open
  useEffect(() => {
    if (!isOpen || stepDetails.size > 0 || fetching) return
    setFetching(true)
    Promise.allSettled(
      steps.map(s => getSolutionFlowStep(projectId, s.id))
    ).then(results => {
      const map = new Map<string, SolutionFlowStepDetail>()
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') map.set(steps[i].id, r.value)
      })
      setStepDetails(map)
      setFetching(false)
    })
  }, [isOpen, steps, projectId, stepDetails.size, fetching])

  // Reset slide on close
  useEffect(() => {
    if (!isOpen) {
      setCurrentSlide(0)
      setStepDetails(new Map())
    }
  }, [isOpen])

  const navigate = (dir: 1 | -1) => {
    setCurrentSlide(prev => Math.max(0, Math.min(totalSlides - 1, prev + dir)))
  }

  const renderSlide = () => {
    // Title slide
    if (currentSlide === 0) {
      return (
        <div className="text-center">
          <h1 className="text-[42px] font-bold text-white mb-2.5" style={{ letterSpacing: '-0.02em' }}>
            Living Blueprint
          </h1>
          <p className="text-lg leading-relaxed mb-9 max-w-[600px] mx-auto" style={{ color: 'rgba(255,255,255,0.5)' }}>
            {flowSummary || `${steps.length} solution steps across ${new Set(steps.map(s => s.phase)).size} phases`}
          </p>
          <div className="flex justify-center gap-7 mb-9">
            <Stat value={String(steps.length)} label="Steps" />
            <Stat value={String(personas.length)} label="Personas" />
            <Stat value={String(new Set(steps.map(s => s.phase)).size)} label="Phases" />
          </div>
          <p className="text-[13px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
            Press → to begin
          </p>
        </div>
      )
    }

    // Summary slide
    if (currentSlide === totalSlides - 1) {
      return (
        <div className="text-center">
          <h2 className="text-[32px] font-bold text-white mb-7" style={{ letterSpacing: '-0.01em' }}>
            Flow Summary
          </h2>
          <div className="grid grid-cols-3 gap-3 mb-8 text-left">
            {steps.map(s => {
              const phase = SOLUTION_FLOW_PHASES[s.phase]
              return (
                <div
                  key={s.id}
                  className="p-4 rounded-[9px]"
                  style={{ background: 'rgba(255,255,255,0.035)', border: '1px solid rgba(255,255,255,0.05)' }}
                >
                  <span
                    className="text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded inline-block mb-1.5"
                    style={{ background: 'rgba(63,175,122,0.1)', color: '#3FAF7A' }}
                  >
                    {phase?.label}
                  </span>
                  <div className="text-sm font-semibold text-white mb-1">{s.title}</div>
                  <div className="text-[11px] leading-snug" style={{ color: 'rgba(255,255,255,0.35)' }}>
                    {s.actors.join(', ')}
                  </div>
                </div>
              )
            })}
          </div>
          <div className="grid grid-cols-3 gap-3.5">
            <SumStat value={String(steps.length)} label="Total Steps" />
            <SumStat value={String(personas.length)} label="Personas Involved" />
            <SumStat value={String(steps.reduce((s, st) => s + st.info_field_count, 0))} label="Information Fields" />
          </div>
        </div>
      )
    }

    // Step slide
    const stepIndex = currentSlide - 1
    const s = steps[stepIndex]
    const d = stepDetails.get(s.id)
    const phase = SOLUTION_FLOW_PHASES[s.phase]

    const painBefore = d?.pain_points_addressed?.[0]
    const beforeText = painBefore ? (typeof painBefore === 'string' ? painBefore : painBefore.text) : null
    const afterText = d?.goals_addressed?.[0] || d?.success_criteria?.[0] || null

    return (
      <div>
        {/* Step header */}
        <div className="flex items-center gap-3 mb-2">
          <span
            className="text-[11px] font-semibold uppercase tracking-wide px-2.5 py-1 rounded"
            style={{ background: 'rgba(63,175,122,0.1)', color: '#3FAF7A' }}
          >
            {phase?.label}
          </span>
          <span className="text-[12px] font-medium" style={{ color: 'rgba(255,255,255,0.3)' }}>
            Step {s.step_index + 1} of {steps.length}
          </span>
        </div>

        <h2 className="text-[34px] font-bold text-white mb-2" style={{ letterSpacing: '-0.02em', lineHeight: 1.2 }}>
          {s.title}
        </h2>
        <p className="text-[15px] leading-relaxed mb-5" style={{ color: 'rgba(255,255,255,0.45)' }}>
          {s.goal}
        </p>

        {/* Narrative */}
        {d?.mock_data_narrative && (
          <div
            className="text-[15px] leading-[1.7] rounded-[10px] p-4.5 mb-5"
            style={{
              color: 'rgba(255,255,255,0.78)',
              background: 'rgba(255,255,255,0.035)',
              borderLeft: '3px solid #3FAF7A',
            }}
          >
            {d.mock_data_narrative}
          </div>
        )}

        {/* Before / After */}
        {(beforeText || afterText) && (
          <div
            className="grid overflow-hidden rounded-[9px] mb-5"
            style={{ gridTemplateColumns: '1fr auto 1fr', border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <div className="p-3.5" style={{ background: 'rgba(4,65,89,0.15)' }}>
              <div className="text-[10px] font-semibold uppercase tracking-wide mb-1.5" style={{ color: 'rgba(255,255,255,0.35)' }}>Before</div>
              <div className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>{beforeText || '—'}</div>
            </div>
            <div className="flex items-center justify-center px-2.5 text-lg" style={{ background: 'rgba(255,255,255,0.02)', color: '#3FAF7A' }}>→</div>
            <div className="p-3.5" style={{ background: 'rgba(63,175,122,0.08)' }}>
              <div className="text-[10px] font-semibold uppercase tracking-wide mb-1.5" style={{ color: '#3FAF7A' }}>After</div>
              <div className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>{afterText || '—'}</div>
            </div>
          </div>
        )}

        {/* Actors */}
        <div className="flex gap-2 mb-4">
          {s.actors.map(name => (
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

        {/* AI Role */}
        {(d?.ai_config?.role || d?.ai_config?.ai_role) && (
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
            {d?.ai_config?.role || d?.ai_config?.ai_role}
          </div>
        )}
      </div>
    )
  }

  return (
    <PresentModeShell
      isOpen={isOpen}
      onClose={onClose}
      totalSlides={totalSlides}
      currentSlide={currentSlide}
      onNavigate={navigate}
      counterLabel={
        currentSlide === 0
          ? 'Living Blueprint'
          : currentSlide === totalSlides - 1
            ? 'Summary'
            : `Step ${currentSlide} of ${steps.length}`
      }
    >
      {renderSlide()}
    </PresentModeShell>
  )
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="text-center">
      <div className="text-[28px] font-bold" style={{ color: '#3FAF7A' }}>{value}</div>
      <div className="text-[11px] uppercase tracking-wide mt-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>{label}</div>
    </div>
  )
}

function SumStat({ value, label }: { value: string; label: string }) {
  return (
    <div
      className="p-4.5 rounded-[9px] text-center"
      style={{ background: 'rgba(255,255,255,0.035)', border: '1px solid rgba(255,255,255,0.05)' }}
    >
      <div className="text-[26px] font-bold mb-1" style={{ color: '#3FAF7A' }}>{value}</div>
      <div className="text-[11px]" style={{ color: 'rgba(255,255,255,0.35)' }}>{label}</div>
    </div>
  )
}
