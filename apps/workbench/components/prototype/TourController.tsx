'use client'

import { useCallback, useEffect, useMemo, useReducer, useRef } from 'react'
import type { FeatureOverlay, TourPlan, TourPhase, TourStep, TourStepGroup, RouteFeatureMap } from '@/types/prototype'
import type { VpStep } from '@/types/api'
import type { PrototypeFrameHandle } from './PrototypeFrame'

interface TourControllerProps {
  overlays: FeatureOverlay[]
  vpSteps: VpStep[]
  routeFeatureMap: RouteFeatureMap
  frameRef: React.RefObject<PrototypeFrameHandle | null>
  isFrameReady: boolean
  onStepChange: (step: TourStep | null) => void
  onTourEnd: () => void
  /** When true, auto-start the tour once frame is ready */
  autoStart?: boolean
}

// --- Route inference from feature names + code paths ---

function inferRouteFromFeature(
  featureName: string,
  codePath: string | null,
  routeFeatureMap: RouteFeatureMap,
  featureId: string,
  handoffRoutes?: string[] | null
): string | null {
  // Level 0: persisted routes from HANDOFF.md (highest priority)
  if (handoffRoutes?.length) return handoffRoutes[0]

  // Level 1: check runtime route-feature map (built from bridge page-change events)
  for (const [route, features] of routeFeatureMap.entries()) {
    if (features.includes(featureId)) return route
  }

  // Level 2: derive from code_file_path (e.g., "app/(dashboard)/reports/page.tsx" → "/reports")
  if (codePath) {
    const routeMatch = codePath.match(/app\/(?:\([^)]+\)\/)?([^/]+)\//)
    if (routeMatch) return '/' + routeMatch[1]
  }

  return null
}

function extractKeywords(featureName: string): string[] {
  return featureName
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .split(/[\s-]+/)
    .filter((w) => w.length > 2)
}

// --- Tour plan builder ---

export function buildTourPlan(
  overlays: FeatureOverlay[],
  vpSteps: VpStep[],
  routeFeatureMap: RouteFeatureMap
): TourPlan {
  const vpFeatureRoles = new Map<string, 'core' | 'supporting'>()
  for (const step of vpSteps) {
    for (const ref of step.features_used || []) {
      vpFeatureRoles.set(ref.feature_id, ref.role)
    }
  }

  const vpGroupsMap = new Map<number, TourStepGroup>()
  const unmapped: TourStep[] = []

  for (const overlay of overlays) {
    const content = overlay.overlay_content
    if (!content) continue

    const featureId = overlay.feature_id || overlay.id

    // Parse VP step index from value_path_position string (e.g. "Step 3 of 7: ...")
    let vpIndex: number | null = null
    let vpLabel: string | null = null
    if (content.impact?.value_path_position) {
      const match = content.impact.value_path_position.match(/Step (\d+)/)
      if (match) vpIndex = parseInt(match[1], 10)
      vpLabel = content.impact.value_path_position
    }
    const role = vpFeatureRoles.get(featureId) || (vpIndex !== null ? 'supporting' : 'unmapped')

    const step: TourStep = {
      featureId,
      featureName: content.feature_name,
      description: content.overview?.prototype_summary || '',
      route: inferRouteFromFeature(content.feature_name, overlay.code_file_path, routeFeatureMap, featureId, overlay.handoff_routes),
      vpStepIndex: vpIndex,
      vpStepLabel: vpLabel,
      overlayId: overlay.id,
      featureRole: role,
      gaps: content.gaps || [],
    }

    if (vpIndex === null) {
      unmapped.push(step)
    } else {
      if (!vpGroupsMap.has(vpIndex)) {
        vpGroupsMap.set(vpIndex, {
          vpStepIndex: vpIndex,
          vpStepLabel: vpLabel || `Step ${vpIndex}`,
          steps: [],
        })
      }
      vpGroupsMap.get(vpIndex)!.steps.push(step)
    }
  }

  // Sort steps within groups: core first, then by confidence ascending
  for (const group of vpGroupsMap.values()) {
    group.steps.sort((a, b) => {
      if (a.featureRole === 'core' && b.featureRole !== 'core') return -1
      if (a.featureRole !== 'core' && b.featureRole === 'core') return 1
      const aOverlay = overlays.find((o) => o.id === a.overlayId)
      const bOverlay = overlays.find((o) => o.id === b.overlayId)
      return (aOverlay?.confidence ?? 1) - (bOverlay?.confidence ?? 1)
    })
  }

  const sortedGroups = Array.from(vpGroupsMap.entries())
    .sort(([a], [b]) => a - b)
    .map(([, group]) => group)

  const primaryGroups = sortedGroups.filter((g) => g.steps.some((s) => s.featureRole === 'core'))
  const secondaryGroups = sortedGroups.filter((g) => !g.steps.some((s) => s.featureRole === 'core'))
  const deepDiveGroups: TourStepGroup[] =
    unmapped.length > 0
      ? [{ vpStepIndex: -1, vpStepLabel: 'Unmapped Features', steps: unmapped }]
      : []

  const phases: Record<TourPhase, TourStepGroup[]> = {
    primary_flow: primaryGroups,
    secondary_flow: secondaryGroups,
    deep_dive: deepDiveGroups,
  }

  const flatSteps = [
    ...primaryGroups.flatMap((g) => g.steps),
    ...secondaryGroups.flatMap((g) => g.steps),
    ...unmapped,
  ]

  const totalQuestions = flatSteps.reduce((sum, s) => sum + s.gaps.length, 0)

  return { phases, flatSteps, totalSteps: flatSteps.length, totalQuestions }
}

// --- Reducer ---

type TourStatus = 'idle' | 'active' | 'paused'
type StepStatus = 'pending' | 'current' | 'completed' | 'skipped'

interface TourState {
  status: TourStatus
  currentIndex: number
  stepStatuses: StepStatus[]
  activePhase: TourPhase
  isPlaying: boolean
}

type TourAction =
  | { type: 'START'; totalSteps: number }
  | { type: 'STOP' }
  | { type: 'NEXT' }
  | { type: 'PREV' }
  | { type: 'JUMP_TO'; index: number }
  | { type: 'TOGGLE_PLAY' }
  | { type: 'SET_PHASE'; phase: TourPhase }
  | { type: 'MARK_SKIPPED'; index: number }

function tourReducer(state: TourState, action: TourAction): TourState {
  switch (action.type) {
    case 'START':
      return {
        status: 'active',
        currentIndex: 0,
        stepStatuses: Array(action.totalSteps).fill('pending').map((_, i) => (i === 0 ? 'current' : 'pending')),
        activePhase: 'primary_flow',
        isPlaying: false,
      }
    case 'STOP':
      return { status: 'idle', currentIndex: 0, stepStatuses: [], activePhase: 'primary_flow', isPlaying: false }
    case 'NEXT': {
      if (state.currentIndex >= state.stepStatuses.length - 1) return state
      const next = state.currentIndex + 1
      const statuses = [...state.stepStatuses]
      statuses[state.currentIndex] = 'completed'
      statuses[next] = 'current'
      return { ...state, currentIndex: next, stepStatuses: statuses }
    }
    case 'PREV': {
      if (state.currentIndex <= 0) return state
      const prev = state.currentIndex - 1
      const statuses = [...state.stepStatuses]
      statuses[state.currentIndex] = 'pending'
      statuses[prev] = 'current'
      return { ...state, currentIndex: prev, stepStatuses: statuses }
    }
    case 'JUMP_TO': {
      if (action.index < 0 || action.index >= state.stepStatuses.length) return state
      const statuses = [...state.stepStatuses]
      statuses[state.currentIndex] = state.currentIndex < action.index ? 'completed' : 'pending'
      statuses[action.index] = 'current'
      return { ...state, currentIndex: action.index, stepStatuses: statuses }
    }
    case 'TOGGLE_PLAY':
      return { ...state, isPlaying: !state.isPlaying }
    case 'SET_PHASE':
      return { ...state, activePhase: action.phase }
    case 'MARK_SKIPPED': {
      const statuses = [...state.stepStatuses]
      statuses[action.index] = 'skipped'
      return { ...state, stepStatuses: statuses }
    }
    default:
      return state
  }
}

const PHASE_LABELS: Record<TourPhase, string> = {
  primary_flow: 'Primary Flow',
  secondary_flow: 'Secondary',
  deep_dive: 'Deep Dive',
}

const STATUS_COLORS: Record<StepStatus, string> = {
  pending: 'bg-gray-200',
  current: 'bg-brand-primary',
  completed: 'bg-emerald-400',
  skipped: 'bg-amber-400',
}

export default function TourController({
  overlays,
  vpSteps,
  routeFeatureMap,
  frameRef,
  isFrameReady,
  onStepChange,
  onTourEnd,
  autoStart = false,
}: TourControllerProps) {
  const [state, dispatch] = useReducer(tourReducer, {
    status: 'idle',
    currentIndex: 0,
    stepStatuses: [],
    activePhase: 'primary_flow',
    isPlaying: false,
  })

  const autoAdvanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastRouteRef = useRef<string | null>(null)

  const plan = useMemo(
    () => buildTourPlan(overlays, vpSteps, routeFeatureMap),
    [overlays, vpSteps, routeFeatureMap]
  )

  const currentStep = state.status === 'active' ? plan.flatSteps[state.currentIndex] ?? null : null

  // Notify parent of step changes
  useEffect(() => {
    onStepChange(currentStep)
  }, [currentStep, onStepChange])

  // Send highlight command to iframe when step changes
  useEffect(() => {
    if (!currentStep || state.status !== 'active') return
    const frame = frameRef.current
    if (!frame) return

    const overlay = overlays.find((o) => o.id === currentStep.overlayId)
    const keywords = extractKeywords(currentStep.featureName)
    const highlightCmd = {
      type: 'aios:highlight-feature' as const,
      featureId: currentStep.featureId,
      featureName: currentStep.featureName,
      description: currentStep.description,
      stepLabel: `Step ${state.currentIndex + 1} of ${plan.totalSteps}`,
      componentName: overlay?.component_name || undefined,
      keywords,
    }

    // Navigate if needed
    if (currentStep.route && currentStep.route !== lastRouteRef.current) {
      frame.sendMessage({ type: 'aios:navigate', path: currentStep.route })
      lastRouteRef.current = currentStep.route
      // Delay highlight to let navigation complete
      const t = setTimeout(() => {
        frame.sendMessage(highlightCmd)
      }, 600)
      return () => clearTimeout(t)
    }

    frame.sendMessage(highlightCmd)
  }, [currentStep, state.status, state.currentIndex, plan.totalSteps, frameRef, overlays])

  // Auto-advance timer
  useEffect(() => {
    if (autoAdvanceTimer.current) {
      clearTimeout(autoAdvanceTimer.current)
      autoAdvanceTimer.current = null
    }
    if (state.isPlaying && state.status === 'active') {
      autoAdvanceTimer.current = setTimeout(() => {
        if (state.currentIndex < plan.totalSteps - 1) {
          dispatch({ type: 'NEXT' })
        } else {
          dispatch({ type: 'TOGGLE_PLAY' })
        }
      }, 12000)
    }
    return () => {
      if (autoAdvanceTimer.current) clearTimeout(autoAdvanceTimer.current)
    }
  }, [state.isPlaying, state.status, state.currentIndex, plan.totalSteps])

  const handleStart = useCallback(() => {
    dispatch({ type: 'START', totalSteps: plan.totalSteps })
  }, [plan.totalSteps])

  // Auto-start the tour when autoStart prop is set and frame is ready
  const autoStartRef = useRef(false)
  useEffect(() => {
    if (autoStart && isFrameReady && state.status === 'idle' && plan.totalSteps > 0 && !autoStartRef.current) {
      autoStartRef.current = true
      dispatch({ type: 'START', totalSteps: plan.totalSteps })
    }
  }, [autoStart, isFrameReady, state.status, plan.totalSteps])

  const handleStop = useCallback(() => {
    frameRef.current?.sendMessage({ type: 'aios:clear-highlights' })
    dispatch({ type: 'STOP' })
    onTourEnd()
  }, [frameRef, onTourEnd])

  const handleNext = useCallback(() => {
    if (state.currentIndex < plan.totalSteps - 1) {
      dispatch({ type: 'NEXT' })
    }
  }, [state.currentIndex, plan.totalSteps])

  const handlePrev = useCallback(() => {
    dispatch({ type: 'PREV' })
  }, [])

  // Handle highlight-not-found: auto-skip after 3s
  const handleHighlightNotFound = useCallback(() => {
    dispatch({ type: 'MARK_SKIPPED', index: state.currentIndex })
    const t = setTimeout(() => {
      if (state.currentIndex < plan.totalSteps - 1) {
        dispatch({ type: 'NEXT' })
      }
    }, 3000)
    return () => clearTimeout(t)
  }, [state.currentIndex, plan.totalSteps])

  // Expose not-found handler via effect
  useEffect(() => {
    // This is wired via the page component's onHighlightNotFound
  }, [handleHighlightNotFound])

  if (plan.totalSteps === 0) return null

  // Idle state: show start button
  if (state.status === 'idle') {
    return (
      <div className="bg-white border-b border-ui-cardBorder px-6 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm text-ui-bodyText">
            {plan.totalSteps} features to review
          </span>
        </div>
        <button
          onClick={handleStart}
          disabled={!isFrameReady}
          className="px-4 py-1.5 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-[#033344] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Start Guided Tour
        </button>
      </div>
    )
  }

  // Active state: control bar + progress
  const isLast = state.currentIndex >= plan.totalSteps - 1
  const isFirst = state.currentIndex <= 0

  return (
    <div className="bg-white border-b border-ui-cardBorder">
      {/* Control bar */}
      <div className="px-4 py-2 flex items-center gap-3">
        <button
          onClick={handlePrev}
          disabled={isFirst}
          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed text-ui-bodyText"
          title="Previous step"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 12L6 8L10 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>

        <div className="flex-1 min-w-0 text-center">
          <span className="text-sm font-medium text-ui-headingDark">
            Step {state.currentIndex + 1}/{plan.totalSteps}
            {currentStep && (
              <>
                <span className="text-ui-supportText mx-1.5">&middot;</span>
                <span className="text-ui-bodyText font-normal truncate">{currentStep.featureName}</span>
              </>
            )}
          </span>
          {currentStep?.vpStepLabel && (
            <span className="text-xs text-ui-supportText ml-2">({currentStep.vpStepLabel})</span>
          )}
        </div>

        <button
          onClick={handleNext}
          disabled={isLast}
          className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed text-ui-bodyText"
          title="Next step"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 4L10 8L6 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
        </button>

        <button
          onClick={() => dispatch({ type: 'TOGGLE_PLAY' })}
          className="p-1.5 rounded hover:bg-gray-100 text-ui-bodyText"
          title={state.isPlaying ? 'Pause auto-advance' : 'Auto-advance'}
        >
          {state.isPlaying ? (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="4" y="3" width="3" height="10" rx="0.5" fill="currentColor"/><rect x="9" y="3" width="3" height="10" rx="0.5" fill="currentColor"/></svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 3L13 8L4 13V3Z" fill="currentColor"/></svg>
          )}
        </button>

        <select
          value={state.activePhase}
          onChange={(e) => dispatch({ type: 'SET_PHASE', phase: e.target.value as TourPhase })}
          className="text-xs border border-ui-cardBorder rounded px-2 py-1 text-ui-bodyText bg-white"
        >
          {(Object.entries(PHASE_LABELS) as [TourPhase, string][]).map(([key, label]) => (
            <option key={key} value={key} disabled={plan.phases[key].length === 0}>
              {label} ({plan.phases[key].flatMap((g) => g.steps).length})
            </option>
          ))}
        </select>

        <button
          onClick={handleStop}
          className="p-1.5 rounded hover:bg-red-50 text-ui-supportText hover:text-red-600"
          title="End tour"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 4L12 12M12 4L4 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
        </button>
      </div>

      {/* Progress bar */}
      <div className="flex h-1 mx-4 mb-1 gap-px">
        {state.stepStatuses.map((s, i) => (
          <button
            key={i}
            className={`flex-1 rounded-full transition-colors ${STATUS_COLORS[s]} hover:opacity-80`}
            onClick={() => dispatch({ type: 'JUMP_TO', index: i })}
            title={plan.flatSteps[i]?.featureName}
          />
        ))}
      </div>
    </div>
  )
}
