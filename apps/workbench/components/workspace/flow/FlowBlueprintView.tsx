'use client'

import { useState, useMemo, useCallback, useEffect, useRef } from 'react'
import type { SolutionFlowOverview, SolutionFlowStepSummary, SolutionFlowStepDetail, PersonaSummary, FeatureBRDSummary, VpStepBRDSummary, DataEntityBRDSummary } from '@/types/workspace'
import { batchGetSolutionFlowSteps, generateSolutionFlow } from '@/lib/api/admin'
import { PHASE_ORDER, LANE_CONFIG, PHASE_CARD_STYLE } from '@/lib/solution-flow-constants'
import { useAgentDerivation } from '@/hooks/useAgentDerivation'
import { FlowStationCard } from './FlowStationCard'
import { FlowDetailPanel } from './FlowDetailPanel'
import { FlowPreviewModal } from './FlowPreviewModal'
import { FlowHorizonsPanel } from './FlowHorizonsPanel'
import { FlowPresentMode } from './FlowPresentMode'

interface FlowBlueprintViewProps {
  projectId: string
  flow: SolutionFlowOverview | null | undefined
  personas: PersonaSummary[]
  onGenerateFlow: () => void
  projectName?: string
  brdFeatures?: FeatureBRDSummary[]
  brdWorkflows?: VpStepBRDSummary[]
  brdDataEntities?: DataEntityBRDSummary[]
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
  projectName,
  brdFeatures,
  brdWorkflows,
  brdDataEntities,
}: FlowBlueprintViewProps) {
  const [activeStepId, setActiveStepId] = useState<string | null>(null)
  const [activePersona, setActivePersona] = useState<number | null>(null)
  const [horizonsOpen, setHorizonsOpen] = useState(false)
  const [presentMode, setPresentMode] = useState(false)
  const [presentVariant, setPresentVariant] = useState<'walkthrough' | 'onepager'>('walkthrough')
  const [previewOpen, setPreviewOpen] = useState(false)
  const [presentMenuOpen, setPresentMenuOpen] = useState(false)
  const [starredStepIds, setStarredStepIds] = useState<Set<string>>(new Set())
  const [highlightReelOpen, setHighlightReelOpen] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generateError, setGenerateError] = useState<string | null>(null)

  // Batch-fetched step details
  const [stepDetails, setStepDetails] = useState<Record<string, SolutionFlowStepDetail>>({})

  const steps = flow?.steps || []

  // Batch fetch all step details on mount / when steps change
  useEffect(() => {
    if (!steps.length) return
    const ids = steps.map(s => s.id)
    batchGetSolutionFlowSteps(projectId, ids)
      .then(resp => setStepDetails(resp.steps))
      .catch(() => {})
  }, [projectId, steps])

  // Group steps by phase
  const phaseGroups = useMemo(() => {
    const groups: Record<string, SolutionFlowStepSummary[]> = {}
    PHASE_ORDER.forEach(p => { groups[p] = [] })
    steps.forEach(s => {
      if (groups[s.phase]) groups[s.phase].push(s)
    })
    return groups
  }, [steps])

  const activeStep = steps.find(s => s.id === activeStepId) || null
  const activeDetail = activeStepId ? stepDetails[activeStepId] || null : null
  const isPersonaFiltered = activePersona !== null

  const handleClosePanel = useCallback(() => {
    setPreviewOpen(false)
    setActiveStepId(null)
  }, [])

  const handleClosePreview = useCallback(() => {
    setPreviewOpen(false)
  }, [])

  const togglePersona = useCallback((index: number) => {
    setActivePersona(prev => prev === index ? null : index)
  }, [])

  const handleDetailRefresh = useCallback((detail: SolutionFlowStepDetail) => {
    setStepDetails(prev => ({ ...prev, [detail.id]: detail }))
  }, [])

  // Agent derivation for combined present mode
  const stepDetailsMap = useMemo(() => {
    const map = new Map<string, SolutionFlowStepDetail>()
    Object.entries(stepDetails).forEach(([id, d]) => map.set(id, d))
    return map
  }, [stepDetails])
  const { agents, avgAutomation } = useAgentDerivation(flow, stepDetailsMap)

  const toggleStar = useCallback((stepId: string) => {
    setStarredStepIds(prev => {
      const next = new Set(prev)
      if (next.has(stepId)) next.delete(stepId)
      else next.add(stepId)
      return next
    })
  }, [])

  // ESC hierarchy: preview first, then panel
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (previewOpen) {
          setPreviewOpen(false)
        } else if (activeStepId) {
          setActiveStepId(null)
        }
      }
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [previewOpen, activeStepId])

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

  // Value momentum: % of steps with confirmed or known confidence
  const momentum = useMemo(() => {
    if (!steps.length) return 0
    const scored = steps.filter(s =>
      s.confirmation_status === 'confirmed_client' ||
      s.confirmation_status === 'confirmed_consultant' ||
      (s.confidence_breakdown?.known || 0) > 0
    ).length
    return Math.round((scored / steps.length) * 100)
  }, [steps])

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true)
    setGenerateError(null)
    try {
      await generateSolutionFlow(projectId)
      onGenerateFlow() // triggers data refetch
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Generation failed'
      // Parse 422 readiness errors
      if (msg.includes('not ready') || msg.includes('422')) {
        setGenerateError('Not enough confirmed data yet. Confirm more features, workflows, and personas in the BRD first.')
      } else {
        setGenerateError(msg)
      }
    } finally {
      setIsGenerating(false)
    }
  }, [projectId, onGenerateFlow])

  // Empty state
  if (!flow || !steps.length) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-0">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center text-2xl" style={{ background: 'rgba(63,175,122,0.08)' }}>
            {isGenerating ? '' : ''}
          </div>
          <h3 className="text-lg font-semibold mb-2" style={{ color: '#1D1D1F' }}>
            {isGenerating ? 'Generating your Living Blueprint...' : 'Living Blueprint'}
          </h3>
          {isGenerating ? (
            <div className="space-y-3">
              <p className="text-sm" style={{ color: '#7B7B7B' }}>
                Analyzing workflows, features, constraints, and intelligence data...
              </p>
              <div className="flex items-center justify-center gap-2">
                <div className="w-2 h-2 rounded-full bg-[#3FAF7A] animate-pulse" />
                <span className="text-xs" style={{ color: '#A0AEC0' }}>This takes about 20 seconds</span>
              </div>
            </div>
          ) : (
            <>
              <p className="text-sm mb-4" style={{ color: '#7B7B7B' }}>
                Generate your Solution Flow to see the Living Blueprint — a visual journey map showing how every feature, workflow, and persona comes together.
              </p>
              {generateError && (
                <div className="mb-4 px-4 py-2.5 rounded-lg text-[12px] text-left" style={{ background: 'rgba(220,80,80,0.06)', border: '1px solid rgba(220,80,80,0.15)', color: '#9B2C2C' }}>
                  {generateError}
                </div>
              )}
              <button
                onClick={handleGenerate}
                disabled={isGenerating}
                className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white transition-colors"
                style={{ background: '#3FAF7A' }}
                onMouseEnter={e => { e.currentTarget.style.background = '#33a06d' }}
                onMouseLeave={e => { e.currentTarget.style.background = '#3FAF7A' }}
              >
                Generate Solution Flow
              </button>
            </>
          )}
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
        {/* Top row: thesis + action buttons */}
        <div className="flex items-center gap-6 mb-3">
          <div
            className="text-[13px] font-normal leading-snug flex-1 min-w-0"
            style={{
              color: 'rgba(255,255,255,0.78)',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
            }}
          >
            {flow.summary || `Your Solution Flow: ${steps.length} steps across ${new Set(steps.map(s => s.phase)).size} phases`}
          </div>

          <div className="flex gap-2 flex-shrink-0">
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

            {/* Present dropdown */}
            <div className="relative">
              <button
                onClick={() => setPresentMenuOpen(!presentMenuOpen)}
                className="px-4 py-1.5 rounded-lg text-[11px] font-semibold transition-all flex items-center gap-1.5"
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
                  if (!presentMenuOpen) {
                    e.currentTarget.style.background = 'rgba(63,175,122,0.08)'
                    e.currentTarget.style.borderColor = 'rgba(63,175,122,0.35)'
                  }
                }}
              >
                Present
                <span className="text-[9px]">{presentMenuOpen ? '\u25B4' : '\u25BE'}</span>
              </button>
              {presentMenuOpen && (
                <>
                  <div className="fixed inset-0 z-[50]" onClick={() => setPresentMenuOpen(false)} />
                  <div
                    className="absolute right-0 top-full mt-1 z-[51] rounded-lg overflow-hidden"
                    style={{ background: 'rgba(10,30,47,0.95)', border: '1px solid rgba(255,255,255,0.10)', minWidth: 180, boxShadow: '0 8px 24px rgba(0,0,0,0.3)' }}
                  >
                    <button
                      onClick={() => { setPresentVariant('walkthrough'); setPresentMode(true); setPresentMenuOpen(false) }}
                      className="w-full text-left px-3.5 py-2.5 text-[11px] transition-colors"
                      style={{ color: 'rgba(255,255,255,0.7)' }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                    >
                      <div className="font-semibold mb-0.5">Walkthrough</div>
                      <div className="text-[9px]" style={{ color: 'rgba(255,255,255,0.35)' }}>Full slide deck, one step at a time</div>
                    </button>
                    <button
                      onClick={() => { setPresentVariant('onepager'); setPresentMode(true); setPresentMenuOpen(false) }}
                      className="w-full text-left px-3.5 py-2.5 text-[11px] transition-colors"
                      style={{ color: 'rgba(255,255,255,0.7)', borderTop: '1px solid rgba(255,255,255,0.06)' }}
                      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                      onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                    >
                      <div className="font-semibold mb-0.5">One-Pager</div>
                      <div className="text-[9px]" style={{ color: 'rgba(255,255,255,0.35)' }}>Printable overview, downloadable as PDF</div>
                    </button>
                    {starredStepIds.size > 0 && (
                      <button
                        onClick={() => { setHighlightReelOpen(true); setPresentMenuOpen(false) }}
                        className="w-full text-left px-3.5 py-2.5 text-[11px] transition-colors"
                        style={{ color: 'rgba(255,255,255,0.7)', borderTop: '1px solid rgba(255,255,255,0.06)' }}
                        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)' }}
                        onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
                      >
                        <div className="font-semibold mb-0.5">Highlight Reel <span className="text-[9px] ml-1 px-1.5 py-0.5 rounded" style={{ background: 'rgba(63,175,122,0.15)', color: '#3FAF7A' }}>{starredStepIds.size}</span></div>
                        <div className="text-[9px]" style={{ color: 'rgba(255,255,255,0.35)' }}>Starred steps only</div>
                      </button>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Bottom row: persona pills + stats */}
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

          {/* Stats pills */}
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[13px] font-bold" style={{ color: '#3FAF7A' }}>{steps.length}</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Steps</span>
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}>
              <span className="text-[13px] font-bold" style={{ color: '#3FAF7A' }}>{personaList.length}</span>
              <span className="text-[9px] uppercase tracking-wide font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>Personas</span>
            </div>
          </div>
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

      {/* Phase Lane Canvas */}
      <div className="flex-1 overflow-auto relative">
        <div className="relative min-h-full flex flex-col">
          {/* Phase lanes */}
          <div className="flex flex-1 gap-px" style={{ minHeight: 480 }}>
            {PHASE_ORDER.map(phase => {
              const lane = LANE_CONFIG[phase]
              const cardStyle = PHASE_CARD_STYLE[phase]
              const stepsInPhase = phaseGroups[phase] || []
              if (!lane) return null

              return (
                <div
                  key={phase}
                  className="relative flex flex-col min-w-0"
                  style={{ flex: lane.flex, padding: '0 10px' }}
                >
                  {/* Lane background wash */}
                  <div
                    className="absolute inset-0 pointer-events-none"
                    style={{ background: cardStyle.laneWash }}
                  />

                  {/* Lane header */}
                  <div className="relative z-[1] flex-shrink-0 px-1.5 pt-3.5 pb-2.5">
                    <div
                      className="text-[9px] font-bold uppercase tracking-widest mb-[2px]"
                      style={{ color: cardStyle.labelColor }}
                    >
                      {lane.label}
                    </div>
                    <div className="text-[10px] leading-snug" style={{ color: cardStyle.sublabelColor }}>
                      {lane.subtitle}
                    </div>
                  </div>

                  {/* Cards */}
                  <div className="relative z-[1] flex-1 flex flex-col gap-2 pb-3.5 justify-center">
                    {stepsInPhase.map((step, i) => {
                      const isDimmed = isPersonaFiltered && !step.actors.includes(personaList[activePersona!]?.name)
                      return (
                        <FlowStationCard
                          key={step.id}
                          step={step}
                          detail={stepDetails[step.id] || null}
                          personas={personas}
                          isSelected={step.id === activeStepId}
                          isDimmed={isDimmed}
                          onClick={() => setActiveStepId(step.id)}
                          animationDelay={step.step_index * 60}
                          isStarred={starredStepIds.has(step.id)}
                          onToggleStar={() => toggleStar(step.id)}
                        />
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Value Momentum Strip */}
          <div
            className="flex items-center px-8 gap-3 flex-shrink-0"
            style={{ height: 34, background: '#fff', borderTop: '1px solid #E2E8F0' }}
          >
            <span className="text-[8px] font-semibold uppercase tracking-wide whitespace-nowrap" style={{ color: '#A0AEC0' }}>
              Value Momentum
            </span>
            <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: '#EDF2F7' }}>
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{
                  width: `${momentum}%`,
                  background: 'linear-gradient(90deg, #044159 0%, #3FAF7A 100%)',
                }}
              />
            </div>
            <span className="text-[11px] font-bold" style={{ color: '#3FAF7A' }}>
              {momentum}%
            </span>
          </div>
        </div>
      </div>

      {/* Detail Panel */}
      {activeStep && (
        <FlowDetailPanel
          projectId={projectId}
          step={activeStep}
          detail={activeDetail}
          isOpen={!!activeStepId}
          onClose={handleClosePanel}
          onPreview={() => setPreviewOpen(true)}
          onDetailRefresh={handleDetailRefresh}
          brdFeatures={brdFeatures}
          brdWorkflows={brdWorkflows}
          brdDataEntities={brdDataEntities}
        />
      )}

      {/* Preview Modal */}
      {activeStep && activeDetail && previewOpen && (
        <FlowPreviewModal
          step={activeStep}
          detail={activeDetail}
          isOpen={previewOpen}
          onClose={handleClosePreview}
          personas={personas}
          projectName={projectName}
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
        variant={presentVariant}
        agents={agents}
        avgAutomation={avgAutomation}
        projectName={projectName}
        stepDetailsMap={stepDetailsMap}
        starredStepIds={starredStepIds}
      />

      {/* Highlight Reel */}
      {highlightReelOpen && (
        <FlowPresentMode
          isOpen={highlightReelOpen}
          onClose={() => setHighlightReelOpen(false)}
          steps={steps.filter(s => starredStepIds.has(s.id))}
          personas={personas}
          flowSummary="Highlight Reel"
          projectId={projectId}
          variant="walkthrough"
          agents={agents}
          avgAutomation={avgAutomation}
          projectName={projectName}
          stepDetailsMap={stepDetailsMap}
          starredStepIds={starredStepIds}
        />
      )}
    </div>
  )
}
