'use client'

import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react'
import { ChevronLeft, ChevronRight, X } from 'lucide-react'
import type { EpicOverlayPlan, EpicTourPhase } from '@/types/epic-overlay'

interface EpicTourControllerProps {
  epicPlan: EpicOverlayPlan
  onPhaseChange: (phase: EpicTourPhase) => void
  onEpicChange: (epicIndex: number | null) => void
  onCardChange: (cardIndex: number | null) => void
  /** Emitted when the tour wants to navigate the iframe to a route */
  onRouteChange?: (route: string | null) => void
  autoStart?: boolean
  /** Per-card confirmation status for progress dots */
  confirmedSet?: Set<string>
}

// --- Flattened card for navigation ---

interface TourCard {
  phase: EpicTourPhase
  index: number // Index within phase
  label: string
  route?: string | null
  /** All routes for richer navigation fallback */
  allRoutes?: string[]
  /** Key for confirmation lookup: "vision:0", "ai_flow:1", etc. */
  confirmKey: string
}

function buildCardList(plan: EpicOverlayPlan): TourCard[] {
  const cards: TourCard[] = []
  for (const epic of plan.vision_epics) {
    cards.push({
      phase: 'vision_journey',
      index: epic.epic_index,
      label: epic.title || `Epic ${epic.epic_index}`,
      route: epic.primary_route,
      allRoutes: epic.all_routes,
      confirmKey: `vision:${epic.epic_index}`,
    })
  }
  for (let i = 0; i < plan.ai_flow_cards.length; i++) {
    cards.push({
      phase: 'ai_deep_dive',
      index: i,
      label: plan.ai_flow_cards[i].title,
      route: plan.ai_flow_cards[i].route,
      confirmKey: `ai_flow:${i}`,
    })
  }
  for (const hc of plan.horizon_cards) {
    cards.push({
      phase: 'horizons',
      index: hc.horizon,
      label: hc.title,
      confirmKey: `horizon:${hc.horizon}`,
    })
  }
  // Cap discovery at 3
  const discoverySlice = plan.discovery_threads.slice(0, 3)
  for (let i = 0; i < discoverySlice.length; i++) {
    cards.push({
      phase: 'discovery',
      index: i,
      label: discoverySlice[i].theme,
      confirmKey: `discovery:${i}`,
    })
  }
  return cards
}

// --- Reducer ---

type TourStatus = 'idle' | 'active'

interface EpicTourState {
  status: TourStatus
  currentIndex: number
  activePhase: EpicTourPhase
}

type EpicTourAction =
  | { type: 'START' }
  | { type: 'STOP' }
  | { type: 'NEXT'; total: number }
  | { type: 'PREV' }
  | { type: 'JUMP_TO'; index: number }
  | { type: 'SET_PHASE'; phase: EpicTourPhase }

function epicTourReducer(state: EpicTourState, action: EpicTourAction): EpicTourState {
  switch (action.type) {
    case 'START':
      return { status: 'active', currentIndex: 0, activePhase: 'vision_journey' }
    case 'STOP':
      return { status: 'idle', currentIndex: 0, activePhase: 'vision_journey' }
    case 'NEXT':
      if (state.currentIndex >= action.total - 1) return state
      return { ...state, currentIndex: state.currentIndex + 1 }
    case 'PREV':
      if (state.currentIndex <= 0) return state
      return { ...state, currentIndex: state.currentIndex - 1 }
    case 'JUMP_TO':
      return { ...state, currentIndex: action.index }
    case 'SET_PHASE':
      return { ...state, activePhase: action.phase }
    default:
      return state
  }
}

const PHASE_LABELS: Record<EpicTourPhase, string> = {
  vision_journey: 'Vision',
  ai_deep_dive: 'AI',
  horizons: 'Horizons',
  discovery: 'Discovery',
}

const PHASE_COLORS: Record<EpicTourPhase, string> = {
  vision_journey: 'bg-brand-primary',
  ai_deep_dive: 'bg-[#0A1E2F]',
  horizons: 'bg-[#37352f]',
  discovery: 'bg-[#666666]',
}

export default function EpicTourController({
  epicPlan,
  onPhaseChange,
  onEpicChange,
  onCardChange,
  onRouteChange,
  autoStart = false,
  confirmedSet,
}: EpicTourControllerProps) {
  const [state, dispatch] = useReducer(epicTourReducer, {
    status: 'idle',
    currentIndex: 0,
    activePhase: 'vision_journey',
  })

  const autoStartRef = useRef(false)

  const cards = useMemo(() => buildCardList(epicPlan), [epicPlan])

  const currentCard = state.status === 'active' ? cards[state.currentIndex] ?? null : null

  // Notify parent of phase/card changes
  useEffect(() => {
    if (currentCard) {
      onPhaseChange(currentCard.phase)
      onCardChange(state.currentIndex)
      if (currentCard.phase === 'vision_journey') {
        onEpicChange(currentCard.index)
      } else {
        onEpicChange(null)
      }
    } else {
      onCardChange(null)
      onEpicChange(null)
    }
  }, [currentCard, state.currentIndex, onPhaseChange, onCardChange, onEpicChange])

  // Navigate iframe when card changes — emit route to parent
  useEffect(() => {
    if (!currentCard || state.status !== 'active') return
    const targetRoute = currentCard.route || currentCard.allRoutes?.[0] || null
    onRouteChange?.(targetRoute)
  }, [currentCard, state.status, onRouteChange])

  // Auto-start
  useEffect(() => {
    if (autoStart && state.status === 'idle' && cards.length > 0 && !autoStartRef.current) {
      autoStartRef.current = true
      dispatch({ type: 'START' })
    }
  }, [autoStart, state.status, cards.length])

  const handleStart = useCallback(() => {
    dispatch({ type: 'START' })
  }, [])

  const handleStop = useCallback(() => {
    onRouteChange?.(null)
    dispatch({ type: 'STOP' })
  }, [onRouteChange])

  const handleNext = useCallback(() => {
    dispatch({ type: 'NEXT', total: cards.length })
  }, [cards.length])

  const handlePrev = useCallback(() => {
    dispatch({ type: 'PREV' })
  }, [])

  // Jump to phase
  const jumpToPhase = useCallback(
    (phase: EpicTourPhase) => {
      const idx = cards.findIndex((c) => c.phase === phase)
      if (idx >= 0) {
        dispatch({ type: 'JUMP_TO', index: idx })
        dispatch({ type: 'SET_PHASE', phase })
      }
    },
    [cards]
  )

  if (cards.length === 0) return null

  // Idle state — minimal single line
  if (state.status === 'idle') {
    return (
      <div className="bg-white border-b border-border px-4 py-1.5 flex items-center justify-between">
        <span className="text-xs text-[#666666]">
          {epicPlan.vision_epics.length} epics · {epicPlan.ai_flow_cards.length} AI · {Math.min(epicPlan.discovery_threads.length, 3)} threads
        </span>
        <button
          onClick={handleStart}
          className="px-3 py-1 bg-brand-primary text-white text-xs font-medium rounded-lg hover:bg-[#25785A] transition-all"
        >
          Start Tour
        </button>
      </div>
    )
  }

  // Active state — compact single bar + thin progress
  const isLast = state.currentIndex >= cards.length - 1
  const isFirst = state.currentIndex <= 0

  const phaseSegments = (['vision_journey', 'ai_deep_dive', 'horizons', 'discovery'] as EpicTourPhase[])
    .map((phase) => ({
      phase,
      count: cards.filter((c) => c.phase === phase).length,
    }))
    .filter((s) => s.count > 0)

  // Phase-local counter: "Epic 2 of 7" not "2/16"
  const phaseCards = cards.filter((c) => c.phase === currentCard?.phase)
  const phaseLocalIndex = currentCard ? phaseCards.indexOf(currentCard) + 1 : 0
  const phaseTotal = phaseCards.length

  return (
    <div className="bg-white border-b border-border">
      {/* Single compact bar: pills | nav | close */}
      <div className="px-3 py-1 flex items-center gap-2">
        {/* Phase pills — compact */}
        <div className="flex items-center gap-0.5 bg-[#F4F4F4] rounded-lg p-0.5">
          {phaseSegments.map(({ phase }) => {
            const isActivePhase = currentCard?.phase === phase
            return (
              <button
                key={phase}
                onClick={() => jumpToPhase(phase)}
                className={`px-2 py-1 text-[11px] font-medium rounded-md transition-colors ${
                  isActivePhase
                    ? 'bg-white text-[#0A1E2F] shadow-sm'
                    : 'text-[#666666] hover:text-text-body'
                }`}
              >
                {PHASE_LABELS[phase]}
              </button>
            )
          })}
        </div>

        {/* Nav arrows + label */}
        <div className="flex items-center gap-1 flex-1 min-w-0 justify-center">
          <button
            onClick={handlePrev}
            disabled={isFirst}
            className="p-1 rounded hover:bg-[#F4F4F4] disabled:opacity-30 text-[#37352f]"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
          <span className="text-[11px] font-medium text-[#37352f] truncate max-w-[200px]">
            {phaseLocalIndex}/{phaseTotal} · {currentCard?.label}
          </span>
          <button
            onClick={handleNext}
            disabled={isLast}
            className="p-1 rounded hover:bg-[#F4F4F4] disabled:opacity-30 text-[#37352f]"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Close */}
        <button
          onClick={handleStop}
          className="p-1 rounded hover:bg-[#F4F4F4] text-text-placeholder hover:text-[#666666]"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Thin progress bar */}
      <div className="flex h-1 mx-3 mb-0.5 gap-px">
        {cards.map((card, i) => {
          const isCurrent = i === state.currentIndex
          const isConfirmed = confirmedSet?.has(card.confirmKey)
          const isPast = i < state.currentIndex
          const color = isCurrent
            ? PHASE_COLORS[card.phase]
            : isConfirmed
              ? 'bg-[#25785A]'
              : isPast
                ? 'bg-[#25785A]/40'
                : 'bg-gray-200'
          return (
            <button
              key={i}
              className={`flex-1 rounded-full transition-colors ${color} hover:opacity-80`}
              onClick={() => dispatch({ type: 'JUMP_TO', index: i })}
              title={card.label}
            />
          )
        })}
      </div>
    </div>
  )
}
