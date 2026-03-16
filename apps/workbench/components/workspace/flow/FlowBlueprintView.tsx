'use client'

import { useState, useMemo, useCallback } from 'react'
import type { SolutionFlowOverview, SolutionFlowStepSummary, PersonaSummary, FlowHorizon } from '@/types/workspace'
import { useWeightedLayout, getSizeClass, type LayoutItem } from '@/hooks/useWeightedLayout'
import { PHASE_ORDER, SOLUTION_FLOW_PHASES } from '@/lib/solution-flow-constants'
import { FlowStationCard } from './FlowStationCard'
import { FlowStepModal } from './FlowStepModal'
import { FlowHorizonsPanel } from './FlowHorizonsPanel'
import { FlowPresentMode } from './FlowPresentMode'

interface FlowBlueprintViewProps {
  projectId: string
  flow: SolutionFlowOverview | null | undefined
  personas: PersonaSummary[]
  onGenerateFlow: () => void
}

function calcStepWeight(step: SolutionFlowStepSummary): number {
  return (
    step.actors.length * 10 +
    step.info_field_count * 6 +
    step.open_question_count * 5 +
    (step.confidence_breakdown?.known || 0) * 3
  )
}

function getPersonaColor(name: string): string {
  const palette = ['#3FAF7A', '#044159', '#2D6B4A', '#0A1E2F']
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return palette[Math.abs(hash) % palette.length]
}

export function FlowBlueprintView({
  projectId,
  flow,
  personas,
  onGenerateFlow,
}: FlowBlueprintViewProps) {
  const [activeStepId, setActiveStepId] = useState<string | null>(null)
  const [activePersona, setActivePersona] = useState<number | null>(null)
  const [horizonsOpen, setHorizonsOpen] = useState(false)
  const [presentMode, setPresentMode] = useState(false)

  const steps = flow?.steps || []

  // Build layout items: group steps by phase into columns
  const layoutItems: LayoutItem[] = useMemo(() => {
    if (!steps.length) return []

    // Group by phase
    const phaseGroups: Record<string, SolutionFlowStepSummary[]> = {}
    steps.forEach(s => {
      if (!phaseGroups[s.phase]) phaseGroups[s.phase] = []
      phaseGroups[s.phase].push(s)
    })

    // Assign columns based on phase order
    const items: LayoutItem[] = []
    let colIndex = 0
    PHASE_ORDER.forEach(phase => {
      const group = phaseGroups[phase]
      if (!group?.length) return
      group.forEach((step, rowIndex) => {
        items.push({
          id: step.id,
          weight: calcStepWeight(step),
          column: colIndex,
          row: rowIndex,
        })
      })
      colIndex++
    })

    return items
  }, [steps])

  const { positions, totalWidth, heroId } = useWeightedLayout(layoutItems)

  const activeStep = steps.find(s => s.id === activeStepId) || null
  const isPersonaFiltered = activePersona !== null

  const handleCloseModal = useCallback(() => setActiveStepId(null), [])

  const togglePersona = useCallback((index: number) => {
    setActivePersona(prev => prev === index ? null : index)
  }, [])

  // Unique personas from step actors
  const personaList = useMemo(() => {
    const seen = new Set<string>()
    const list: { name: string; color: string; initials: string }[] = []
    personas.forEach(p => {
      if (!seen.has(p.name)) {
        seen.add(p.name)
        list.push({
          name: p.name,
          color: getPersonaColor(p.name),
          initials: p.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase(),
        })
      }
    })
    return list
  }, [personas])

  // Horizon count for button badge
  const horizonSteps = useMemo(() => {
    // Count steps by phase for horizon grouping
    const h2 = steps.filter(s => s.phase === 'output').length
    const h3 = steps.filter(s => s.phase === 'admin').length
    return h2 + h3
  }, [steps])

  // Empty state
  if (!flow || !steps.length) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-2xl" style={{ background: 'rgba(63,175,122,0.08)' }}>
            🌊
          </div>
          <h3 className="text-lg font-semibold mb-2" style={{ color: '#1D1D1F' }}>
            Living Blueprint
          </h3>
          <p className="text-sm mb-6" style={{ color: '#7B7B7B' }}>
            Generate your Solution Flow to see the Living Blueprint — a visual journey map of your solution steps flowing left-to-right as weighted stations.
          </p>
          <button
            onClick={onGenerateFlow}
            className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-colors"
            style={{ background: '#3FAF7A' }}
            onMouseEnter={e => { e.currentTarget.style.background = '#33a06d' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#3FAF7A' }}
          >
            Generate Solution Flow
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      {/* Header Bar */}
      <div
        className="flex-shrink-0 px-8 pt-4 pb-3"
        style={{ background: '#0A1E2F' }}
      >
        {/* Top row: thesis + pills */}
        <div className="flex items-start gap-6 mb-3">
          <p className="text-[15px] font-normal leading-relaxed flex-1 max-w-[720px]" style={{ color: 'rgba(255,255,255,0.82)' }}>
            {flow.summary ? (
              <>
                {flow.summary.split(/(\b\d+\b)/g).map((part, i) =>
                  /\d+/.test(part) ? (
                    <em key={i} className="not-italic font-medium" style={{ color: '#3FAF7A' }}>{part}</em>
                  ) : part
                )}
              </>
            ) : (
              <span>Your <em className="not-italic font-medium" style={{ color: '#3FAF7A' }}>Solution Flow</em>: {steps.length} steps across {new Set(steps.map(s => s.phase)).size} phases</span>
            )}
          </p>

          <div className="flex gap-3 flex-shrink-0">
            <div className="flex flex-col items-center px-3.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[17px] font-bold leading-tight" style={{ color: '#3FAF7A' }}>{steps.length}</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Steps</span>
            </div>
            <div className="flex flex-col items-center px-3.5 py-1.5 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[17px] font-bold leading-tight" style={{ color: '#3FAF7A' }}>{personaList.length}</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Personas</span>
            </div>
          </div>
        </div>

        {/* Bottom row: persona pills + buttons */}
        <div className="flex items-center gap-2.5">
          <div className="flex gap-1.5 flex-1">
            {personaList.map((p, i) => (
              <button
                key={p.name}
                onClick={() => togglePersona(i)}
                className="flex items-center gap-1.5 py-0.5 pl-0.5 pr-2.5 rounded-full text-[11px] font-medium transition-all"
                style={{
                  border: `1px solid ${activePersona === i ? p.color : 'rgba(255,255,255,0.1)'}`,
                  background: activePersona === i ? 'rgba(255,255,255,0.08)' : 'transparent',
                  color: activePersona === i ? '#fff' : 'rgba(255,255,255,0.55)',
                }}
              >
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold text-white flex-shrink-0"
                  style={{ background: p.color }}
                >
                  {p.initials}
                </div>
                {p.name.split(' ')[0]}
              </button>
            ))}
          </div>

          {/* Horizons button */}
          <button
            onClick={() => setHorizonsOpen(!horizonsOpen)}
            className="px-3.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all"
            style={{
              border: `1px solid ${horizonsOpen ? 'rgba(63,175,122,0.35)' : 'rgba(255,255,255,0.12)'}`,
              background: horizonsOpen ? 'rgba(63,175,122,0.08)' : 'transparent',
              color: horizonsOpen ? '#3FAF7A' : 'rgba(255,255,255,0.45)',
            }}
          >
            Horizons
          </button>

          {/* Present button */}
          <button
            onClick={() => setPresentMode(true)}
            className="px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all"
            style={{
              border: '1px solid rgba(63,175,122,0.35)',
              background: 'rgba(63,175,122,0.08)',
              color: '#3FAF7A',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(63,175,122,0.18)'
              e.currentTarget.style.borderColor = '#3FAF7A'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(63,175,122,0.08)'
              e.currentTarget.style.borderColor = 'rgba(63,175,122,0.35)'
            }}
          >
            Present
          </button>
        </div>
      </div>

      {/* Horizons Panel */}
      <FlowHorizonsPanel
        projectId={projectId}
        isOpen={horizonsOpen}
        steps={steps}
        onStepClick={(stepId) => {
          setHorizonsOpen(false)
          setActiveStepId(stepId)
        }}
      />

      {/* Canvas */}
      <div className="flex-1 overflow-auto relative">
        <div
          className="relative"
          style={{ minWidth: totalWidth, minHeight: 520, padding: '20px 0' }}
        >
          {/* Waterline gradient */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'linear-gradient(90deg, #FAFAFA 0%, rgba(63,175,122,0.015) 30%, rgba(63,175,122,0.025) 60%, rgba(63,175,122,0.04) 100%)',
            }}
          />

          {/* Station cards */}
          {steps.map((step, i) => {
            const pos = positions.get(step.id)
            if (!pos) return null

            const item = layoutItems.find(li => li.id === step.id)
            const weight = item?.weight ?? 0

            const isDimmed = isPersonaFiltered && !step.actors.includes(personaList[activePersona!]?.name)

            return (
              <FlowStationCard
                key={step.id}
                step={step}
                position={pos}
                sizeClass={getSizeClass(weight, step.id === heroId)}
                personas={personas}
                isSelected={step.id === activeStepId}
                isDimmed={isDimmed}
                onClick={() => setActiveStepId(step.id)}
                animationDelay={i * 70}
              />
            )
          })}
        </div>
      </div>

      {/* Step Modal */}
      {activeStep && (
        <FlowStepModal
          projectId={projectId}
          step={activeStep}
          isOpen={!!activeStepId}
          onClose={handleCloseModal}
          personas={personas}
        />
      )}

      {/* Present Mode */}
      <FlowPresentMode
        isOpen={presentMode}
        onClose={() => setPresentMode(false)}
        steps={steps}
        personas={personas}
        flowSummary={flow.summary || ''}
        projectId={projectId}
      />
    </div>
  )
}
