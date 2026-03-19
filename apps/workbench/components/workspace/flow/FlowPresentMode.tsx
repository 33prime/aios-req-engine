'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import type { SolutionFlowStepSummary, SolutionFlowStepDetail, PersonaSummary, DerivedAgent } from '@/types/workspace'
import { PHASE_ORDER, SOLUTION_FLOW_PHASES, LANE_CONFIG } from '@/lib/solution-flow-constants'
import { PresentModeShell } from '@/components/workspace/shared/PresentModeShell'
import { PresentShareToolbar } from '@/components/workspace/shared/PresentShareToolbar'
import { OnePagerView } from '@/components/workspace/shared/OnePagerView'
import {
  HeroSlide, SplitSlide, DataSlide, AgentSpotlightSlide, DefaultSlide,
  classifySlideTemplate, PhaseTransitionSlide,
} from '@/components/workspace/shared/present-slides'
import type { SlideData } from '@/components/workspace/shared/present-slides'
import { getSolutionFlowStep } from '@/lib/api/admin'

interface FlowPresentModeProps {
  isOpen: boolean
  onClose: () => void
  steps: SolutionFlowStepSummary[]
  personas: PersonaSummary[]
  flowSummary: string
  projectId: string
  variant?: 'walkthrough' | 'onepager'
  agents?: DerivedAgent[]
  avgAutomation?: number
  projectName?: string
  stepDetailsMap?: Map<string, SolutionFlowStepDetail>
  starredStepIds?: Set<string>
}

const SLIDE_TEMPLATES = {
  hero: HeroSlide,
  split: SplitSlide,
  data: DataSlide,
  agent_spotlight: AgentSpotlightSlide,
  default: DefaultSlide,
}

export function FlowPresentMode({
  isOpen,
  onClose,
  steps,
  personas,
  flowSummary,
  projectId,
  variant = 'walkthrough',
  agents,
  avgAutomation = 0,
  projectName,
  stepDetailsMap: externalDetails,
  starredStepIds,
}: FlowPresentModeProps) {
  const [currentSlide, setCurrentSlide] = useState(0)
  const [stepDetails, setStepDetails] = useState<Map<string, SolutionFlowStepDetail>>(new Map())
  const [fetching, setFetching] = useState(false)
  const contentRef = useRef<HTMLDivElement>(null)

  // Use external details if provided, else fetch
  const details = externalDetails && externalDetails.size > 0 ? externalDetails : stepDetails

  // Fetch step details on open (if no external details)
  useEffect(() => {
    if (!isOpen || (externalDetails && externalDetails.size > 0) || stepDetails.size > 0 || fetching) return
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
  }, [isOpen, steps, projectId, stepDetails.size, fetching, externalDetails])

  // Reset slide on close
  useEffect(() => {
    if (!isOpen) {
      setCurrentSlide(0)
      if (!externalDetails) setStepDetails(new Map())
    }
  }, [isOpen, externalDetails])

  // Build slide array with phase transitions
  const slides = useMemo(() => {
    const result: Array<{ type: 'title' | 'transition' | 'step' | 'summary'; data?: unknown }> = []

    // Title slide
    result.push({ type: 'title' })

    // Steps grouped by phase with transitions
    let lastPhase = ''
    for (const step of steps) {
      if (step.phase !== lastPhase) {
        const phaseSteps = steps.filter(s => s.phase === step.phase)
        result.push({
          type: 'transition',
          data: {
            phase: step.phase,
            stepCount: phaseSteps.length,
            phaseIndex: PHASE_ORDER.indexOf(step.phase as typeof PHASE_ORDER[number]),
          },
        })
        lastPhase = step.phase
      }
      result.push({ type: 'step', data: step })
    }

    // Summary slide
    result.push({ type: 'summary' })

    return result
  }, [steps])

  const totalSlides = slides.length

  const navigate = (dir: 1 | -1) => {
    setCurrentSlide(prev => Math.max(0, Math.min(totalSlides - 1, prev + dir)))
  }

  const handleDownloadPDF = useCallback(() => {
    // Switch to onepager and print (if already in onepager, just print)
    if (variant === 'onepager') {
      window.print()
    } else {
      // Close walkthrough and re-open as onepager
      // For simplicity, just call window.print on current view
      window.print()
    }
  }, [variant])

  const handleScreenshot = useCallback(() => {
    // Handled by PresentShareToolbar internally
  }, [])

  const toolbar = (
    <PresentShareToolbar
      onDownloadPDF={handleDownloadPDF}
      onScreenshot={handleScreenshot}
      contentRef={contentRef}
    />
  )

  // One-Pager mode
  if (variant === 'onepager') {
    return (
      <PresentModeShell
        isOpen={isOpen}
        onClose={onClose}
        totalSlides={0}
        currentSlide={0}
        onNavigate={() => {}}
        counterLabel={projectName ? `${projectName} — Solution Blueprint` : 'Solution Blueprint'}
        variant="onepager"
        toolbar={toolbar}
      >
        <OnePagerView
          steps={steps}
          stepDetails={details}
          agents={agents}
          personas={personas}
          flowSummary={flowSummary}
          projectName={projectName}
          onClose={onClose}
        />
      </PresentModeShell>
    )
  }

  // Walkthrough mode
  const renderSlide = () => {
    const slide = slides[currentSlide]
    if (!slide) return null

    // Title slide
    if (slide.type === 'title') {
      return (
        <div className="text-center">
          <h1 className="text-[42px] font-bold text-white mb-2.5" style={{ letterSpacing: '-0.02em' }}>
            {projectName ? `${projectName}` : 'Living Blueprint'}
          </h1>
          <p className="text-lg leading-relaxed mb-9 max-w-[600px] mx-auto" style={{ color: 'rgba(255,255,255,0.5)' }}>
            {flowSummary || `${steps.length} solution steps across ${new Set(steps.map(s => s.phase)).size} phases`}
          </p>
          <div className="flex justify-center gap-7 mb-9">
            <Stat value={String(steps.length)} label="Steps" />
            <Stat value={String(personas.length)} label="Personas" />
            {agents && agents.length > 0 && <Stat value={String(agents.length)} label="AI Agents" />}
            {avgAutomation > 0 && <Stat value={`${avgAutomation}%`} label="Automated" />}
          </div>
          <p className="text-[13px]" style={{ color: 'rgba(255,255,255,0.2)' }}>
            Press &rarr; to begin
          </p>
        </div>
      )
    }

    // Phase transition
    if (slide.type === 'transition') {
      const { phase, stepCount, phaseIndex } = slide.data as { phase: string; stepCount: number; phaseIndex: number }
      const lane = LANE_CONFIG[phase]
      return (
        <PhaseTransitionSlide
          phaseName={phase}
          phaseLabel={lane?.label || phase}
          subtitle={lane?.subtitle || ''}
          stepCount={stepCount}
          phaseIndex={phaseIndex}
        />
      )
    }

    // Summary slide
    if (slide.type === 'summary') {
      return (
        <div className="text-center">
          <h2 className="text-[32px] font-bold text-white mb-7" style={{ letterSpacing: '-0.01em' }}>
            {projectName ? `${projectName} — Summary` : 'Flow Summary'}
          </h2>
          <div className="grid grid-cols-3 gap-3 mb-8 text-left">
            {steps.map(s => {
              const phase = SOLUTION_FLOW_PHASES[s.phase]
              const d = details.get(s.id)
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
                    {d?.story_headline || s.goal}
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

    // Step slide — use template classification
    const stepData = slide.data as SolutionFlowStepSummary
    const d = details.get(stepData.id)
    const stepIdx = steps.indexOf(stepData)
    const template = classifySlideTemplate(stepData, d ?? null)
    const SlideComponent = SLIDE_TEMPLATES[template]

    const slideData: SlideData = {
      step: stepData,
      detail: d ?? null,
      stepIndex: stepIdx,
      totalSteps: steps.length,
    }

    return <SlideComponent {...slideData} />
  }

  const currentSlideData = slides[currentSlide]
  const counterLabel = currentSlideData?.type === 'title'
    ? (projectName || 'Living Blueprint')
    : currentSlideData?.type === 'summary'
      ? 'Summary'
      : currentSlideData?.type === 'transition'
        ? 'Phase Transition'
        : `Step ${slides.slice(0, currentSlide + 1).filter(s => s.type === 'step').length} of ${steps.length}`

  return (
    <PresentModeShell
      isOpen={isOpen}
      onClose={onClose}
      totalSlides={totalSlides}
      currentSlide={currentSlide}
      onNavigate={navigate}
      counterLabel={counterLabel}
      toolbar={toolbar}
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
