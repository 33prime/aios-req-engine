/**
 * BuildCinematicView — Cinematic build progress experience.
 *
 * Replaces the static 4-step checklist with a rich, animated view
 * driven by structured build_log events from the backend pipeline.
 *
 * Four phases:
 *   discovery → architecture → building → live
 *
 * Each phase renders distinct animated content based on real data
 * streamed from the build pipeline.
 */

'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import type {
  BuildLogEntry,
  BuildPipelineStatus,
  Phase0CompleteData,
  PayloadAssembledData,
  ArchitectureCompleteData,
  ScreenBuiltData,
} from '@/types/prototype'

// ── Phase derivation ──

type CinematicPhase = 'discovery' | 'architecture' | 'building' | 'live'

function derivePhase(
  buildLog: BuildLogEntry[],
  status: BuildPipelineStatus,
): CinematicPhase {
  if (status === 'completed' || status === 'failed') return 'live'
  const types = new Set(buildLog.map((e) => e.type).filter(Boolean))
  if (types.has('deploy_complete')) return 'live'
  if (types.has('architecture_complete') || types.has('screen_built')) return 'building'
  if (types.has('phase0_complete') || types.has('payload_assembled')) return 'architecture'
  return 'discovery'
}

// ── Helpers ──

function findEvent(log: BuildLogEntry[], type: string): BuildLogEntry | undefined {
  return log.find((e) => e.type === type)
}

function findAllEvents(log: BuildLogEntry[], type: string): BuildLogEntry[] {
  return log.filter((e) => e.type === type)
}

// ── Entity chip colors ──

const ENTITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  feature: { bg: 'rgba(63,175,122,0.10)', text: '#3FAF7A', border: 'rgba(63,175,122,0.25)' },
  persona: { bg: 'rgba(74,158,255,0.10)', text: '#4A9EFF', border: 'rgba(74,158,255,0.25)' },
  flow: { bg: 'rgba(167,139,250,0.10)', text: '#A78BFA', border: 'rgba(167,139,250,0.25)' },
  epic: { bg: 'rgba(245,166,35,0.10)', text: '#F5A623', border: 'rgba(245,166,35,0.25)' },
}

// ── Component ──

interface BuildCinematicViewProps {
  status: BuildPipelineStatus
  buildLog: BuildLogEntry[]
  onCancel: () => void
}

export default function BuildCinematicView({
  status,
  buildLog,
  onCancel,
}: BuildCinematicViewProps) {
  const phase = derivePhase(buildLog, status)
  const isFailed = status === 'failed'

  return (
    <div className="relative h-full w-full overflow-hidden bg-[#0A1E2F]">
      {/* Keyframes for screen build animation */}
      <style>{`
        @keyframes glowSweep {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
      `}</style>
      {/* Blueprint grid background */}
      <div
        className="absolute inset-0 opacity-60"
        style={{
          backgroundImage:
            'linear-gradient(rgba(63,175,122,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(63,175,122,0.08) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />
      <div
        className="absolute inset-0"
        style={{
          background: 'radial-gradient(ellipse at center, transparent 30%, #0A1E2F 80%)',
        }}
      />

      {/* Phase bar */}
      <PhaseBar phase={phase} isFailed={isFailed} />

      {/* Phase content */}
      <div className="relative z-[1] flex h-full flex-col items-center justify-center px-8">
        {phase === 'discovery' && <DiscoveryPhase buildLog={buildLog} />}
        {phase === 'architecture' && <ArchitecturePhase buildLog={buildLog} />}
        {phase === 'building' && <BuildingPhase buildLog={buildLog} />}
        {phase === 'live' && <LivePhase isFailed={isFailed} />}
      </div>

      {/* Narration + Stats bar */}
      <NarrationBar buildLog={buildLog} phase={phase} />

      {/* Cancel button */}
      {status !== 'completed' && status !== 'failed' && (
        <button
          onClick={onCancel}
          className="absolute bottom-5 right-6 z-10 text-xs text-[#6B7D8D] underline underline-offset-2 transition-colors hover:text-red-400"
        >
          Cancel build
        </button>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════
// Phase Bar
// ══════════════════════════════════════════════

const PHASE_LABELS: { key: CinematicPhase; label: string }[] = [
  { key: 'discovery', label: 'Analyze' },
  { key: 'architecture', label: 'Architect' },
  { key: 'building', label: 'Build' },
  { key: 'live', label: 'Go Live' },
]

function PhaseBar({ phase, isFailed }: { phase: CinematicPhase; isFailed: boolean }) {
  const phaseIdx = PHASE_LABELS.findIndex((p) => p.key === phase)

  return (
    <div className="absolute left-1/2 top-6 z-10 flex -translate-x-1/2 items-center gap-0 rounded-xl border border-white/[0.08] bg-black/30 px-2 py-1.5 backdrop-blur-xl">
      {PHASE_LABELS.map((p, i) => {
        const isActive = i === phaseIdx
        const isDone = i < phaseIdx
        const dotClass = isActive
          ? 'bg-[#3FAF7A] shadow-[0_0_8px_rgba(63,175,122,0.4)]'
          : isDone
            ? 'bg-[#3FAF7A]'
            : 'bg-[#6B7D8D]'
        const textClass = isActive || isDone ? 'text-[#3FAF7A]' : 'text-[#6B7D8D]'

        return (
          <div key={p.key} className="flex items-center">
            {i > 0 && <div className="mx-1 h-px w-5 bg-white/[0.08]" />}
            <div className={`flex items-center gap-1.5 rounded-lg px-3 py-1 text-[11px] font-medium ${isActive ? 'bg-[rgba(63,175,122,0.15)]' : ''} ${textClass}`}>
              <div className={`h-1.5 w-1.5 rounded-full ${dotClass}`} />
              {p.label}
              {isFailed && isActive && <span className="ml-1 text-red-400">!</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ══════════════════════════════════════════════
// Discovery Phase
// ══════════════════════════════════════════════

function DiscoveryPhase({ buildLog }: { buildLog: BuildLogEntry[] }) {
  const [visibleCount, setVisibleCount] = useState(0)

  // Pulsing dots animation
  useEffect(() => {
    const iv = setInterval(() => {
      setVisibleCount((c) => (c < 3 ? c + 1 : 0))
    }, 500)
    return () => clearInterval(iv)
  }, [])

  return (
    <div className="flex flex-col items-center">
      <div className="mb-2 flex h-16 w-16 items-center justify-center rounded-full bg-[rgba(63,175,122,0.1)]">
        <svg className="h-8 w-8 animate-pulse text-[#3FAF7A]" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
        </svg>
      </div>
      <h3 className="mb-1 text-sm font-semibold text-[#E8ECF0]">Analyzing Discovery Data</h3>
      <p className="text-xs text-[#6B7D8D]">
        Scanning confirmed entities
        {'.'.repeat(visibleCount)}
      </p>
    </div>
  )
}

// ══════════════════════════════════════════════
// Architecture Phase
// ══════════════════════════════════════════════

function ArchitecturePhase({ buildLog }: { buildLog: BuildLogEntry[] }) {
  const phase0 = findEvent(buildLog, 'phase0_complete')?.data as Phase0CompleteData | undefined
  const payloadData = findEvent(buildLog, 'payload_assembled')?.data as PayloadAssembledData | undefined
  const archData = findEvent(buildLog, 'architecture_complete')?.data as ArchitectureCompleteData | undefined

  // Stagger entity chips appearance
  const [chipCount, setChipCount] = useState(0)
  const totalChips = (phase0?.epics?.length ?? 0) + (payloadData ? 3 : 0)

  useEffect(() => {
    if (chipCount >= totalChips) return
    const t = setTimeout(() => setChipCount((c) => c + 1), 200)
    return () => clearTimeout(t)
  }, [chipCount, totalChips])

  // Entity summary chips
  const entityChips: { label: string; count: number; type: string }[] = []
  if (payloadData) {
    entityChips.push({ label: 'Features', count: payloadData.feature_count, type: 'feature' })
    entityChips.push({ label: 'Personas', count: payloadData.persona_count, type: 'persona' })
    entityChips.push({ label: 'Flow Steps', count: payloadData.flow_step_count, type: 'flow' })
  } else if (phase0) {
    entityChips.push({ label: 'Features', count: phase0.feature_count, type: 'feature' })
  }

  return (
    <div className="flex flex-col items-center gap-6">
      {/* Entity counts */}
      <div className="flex flex-wrap justify-center gap-3">
        {entityChips.map((chip, i) => {
          const colors = ENTITY_COLORS[chip.type] || ENTITY_COLORS.feature
          return (
            <div
              key={chip.type}
              className="transition-all duration-500"
              style={{
                opacity: i < chipCount ? 1 : 0,
                transform: i < chipCount ? 'translateY(0)' : 'translateY(8px)',
              }}
            >
              <div
                className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium"
                style={{ background: colors.bg, color: colors.text, border: `1px solid ${colors.border}` }}
              >
                <AnimatedCounter target={chip.count} />
                <span>{chip.label}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Epic clusters */}
      {phase0?.epics && phase0.epics.length > 0 && (
        <div className="flex flex-wrap justify-center gap-2">
          {phase0.epics.map((epic, i) => {
            const offset = entityChips.length
            const colors = ENTITY_COLORS.epic
            return (
              <div
                key={epic.name}
                className="transition-all duration-500"
                style={{
                  opacity: i + offset < chipCount ? 1 : 0,
                  transform: i + offset < chipCount ? 'scale(1)' : 'scale(0.8)',
                }}
              >
                <div
                  className="rounded-md px-2.5 py-1 text-[10px] font-medium"
                  style={{ background: colors.bg, color: colors.text, border: `1px solid ${colors.border}` }}
                >
                  {epic.name}
                  <span className="ml-1 opacity-60">({epic.feature_count})</span>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Architecture planning indicator */}
      {!archData && (
        <div className="mt-2 flex items-center gap-2 text-xs text-[#6B7D8D]">
          <div className="h-3 w-3 animate-spin rounded-full border border-[#3FAF7A] border-t-transparent" />
          Planning architecture...
        </div>
      )}

      {/* Architecture result — nav sections */}
      {archData && (
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          {archData.sections.map((section, i) => (
            <SectionChip key={section.label} label={section.label} screenCount={section.screen_count} delay={i * 150} />
          ))}
        </div>
      )}
    </div>
  )
}

function SectionChip({ label, screenCount, delay }: { label: string; screenCount: number; delay: number }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  return (
    <div
      className="rounded-md border border-white/[0.08] bg-white/[0.04] px-2.5 py-1 text-[10px] text-[#9AABB8] backdrop-blur-sm transition-all duration-500"
      style={{ opacity: visible ? 1 : 0, transform: visible ? 'translateX(0)' : 'translateX(-12px)' }}
    >
      {label}
      <span className="ml-1 text-[#6B7D8D]">{screenCount}</span>
    </div>
  )
}

// ══════════════════════════════════════════════
// Building Phase
// ══════════════════════════════════════════════

function BuildingPhase({ buildLog }: { buildLog: BuildLogEntry[] }) {
  const archData = findEvent(buildLog, 'architecture_complete')?.data as ArchitectureCompleteData | undefined
  const screenEvents = findAllEvents(buildLog, 'screen_built')
  const builtRoutes = useMemo(() => new Set(screenEvents.map((e) => (e.data as ScreenBuiltData)?.route)), [screenEvents])

  const screens = archData?.screens ?? []
  const totalScreens = archData?.total_screens ?? screens.length

  // Stagger screen_built event reveals even if they arrive in a batch
  const [revealedCount, setRevealedCount] = useState(0)
  const prevBuiltCountRef = useRef(0)

  useEffect(() => {
    if (builtRoutes.size <= prevBuiltCountRef.current) return
    // New screens arrived — stagger their reveal
    const newCount = builtRoutes.size
    const diff = newCount - prevBuiltCountRef.current
    prevBuiltCountRef.current = newCount

    for (let i = 0; i < diff; i++) {
      setTimeout(() => {
        setRevealedCount((c) => c + 1)
      }, i * 400)
    }
  }, [builtRoutes.size])

  // Build a map of which screens are revealed
  const revealedRoutes = useMemo(() => {
    const routes = new Set<string>()
    const builtArr = screenEvents.map((e) => (e.data as ScreenBuiltData)?.route).filter(Boolean)
    for (let i = 0; i < Math.min(revealedCount, builtArr.length); i++) {
      routes.add(builtArr[i])
    }
    return routes
  }, [revealedCount, screenEvents])

  // Currently building = first built but not yet revealed
  const currentlyBuilding = useMemo(() => {
    const builtArr = screenEvents.map((e) => (e.data as ScreenBuiltData)?.route).filter(Boolean)
    if (revealedCount < builtArr.length) return builtArr[revealedCount]
    // If all built are revealed but we haven't finished, the next unbuilt screen is "building"
    const nextUnbuilt = screens.find((s) => !builtRoutes.has(s.route))
    return nextUnbuilt?.route ?? null
  }, [revealedCount, screenEvents, screens, builtRoutes])

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="mb-1 text-center">
        <h3 className="text-sm font-semibold text-[#E8ECF0]">Building Screens</h3>
        <p className="text-xs text-[#6B7D8D]">
          {revealedCount} of {totalScreens} screens complete
        </p>
      </div>

      {/* Screen grid */}
      <div className="grid max-w-2xl grid-cols-3 gap-3 sm:grid-cols-4">
        {screens.map((screen) => {
          const isBuilt = revealedRoutes.has(screen.route)
          const isActive = screen.route === currentlyBuilding

          return (
            <ScreenCard
              key={screen.route}
              name={screen.name}
              route={screen.route}
              isBuilt={isBuilt}
              isActive={isActive}
            />
          )
        })}
      </div>
    </div>
  )
}

function ScreenCard({
  name,
  route,
  isBuilt,
  isActive,
}: {
  name: string
  route: string
  isBuilt: boolean
  isActive: boolean
}) {
  return (
    <div
      className={`relative flex h-[90px] w-[140px] flex-col items-center justify-center overflow-hidden rounded-lg border transition-all duration-500 ${
        isBuilt
          ? 'border-[rgba(63,175,122,0.3)] bg-[rgba(63,175,122,0.06)]'
          : isActive
            ? 'border-[#3FAF7A] shadow-[0_0_20px_rgba(63,175,122,0.15)]'
            : 'border-dashed border-[rgba(63,175,122,0.2)] bg-[rgba(63,175,122,0.03)]'
      }`}
    >
      {/* Glow sweep animation for active screen */}
      {isActive && (
        <div
          className="absolute inset-0 rounded-lg"
          style={{
            background: 'linear-gradient(90deg, transparent, rgba(63,175,122,0.08), transparent)',
            backgroundSize: '200% 100%',
            animation: 'glowSweep 2s ease-in-out infinite',
          }}
        />
      )}

      {/* Wireframe placeholder when built */}
      {isBuilt && (
        <div className="absolute inset-1.5 flex flex-col gap-1 opacity-40">
          <div className="h-[3px] w-3/5 rounded-sm bg-white/[0.08]" />
          <div className="h-2 w-4/5 rounded-sm bg-white/[0.05]" />
          <div className="flex gap-1">
            <div className="h-5 flex-1 rounded-sm bg-white/[0.04]" />
            <div className="h-5 flex-1 rounded-sm bg-white/[0.04]" />
          </div>
          <div className="h-3 w-full rounded-sm bg-white/[0.04]" />
        </div>
      )}

      <span className="relative z-[1] text-[10px] font-semibold text-[#9AABB8]">{name}</span>
      <span className="relative z-[1] font-mono text-[9px] text-[#6B7D8D]">{route}</span>

      {/* Progress bar */}
      <div className="absolute bottom-1 left-1 right-1 h-[2px] overflow-hidden rounded-sm bg-white/[0.06]">
        <div
          className="h-full rounded-sm bg-[#3FAF7A] transition-all duration-700"
          style={{ width: isBuilt ? '100%' : isActive ? '60%' : '0%' }}
        />
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════
// Live Phase
// ══════════════════════════════════════════════

function LivePhase({ isFailed }: { isFailed: boolean }) {
  const [revealed, setRevealed] = useState(false)
  const [cardsVisible, setCardsVisible] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => setRevealed(true), 300)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!revealed) return
    if (cardsVisible >= 5) return
    const t = setTimeout(() => setCardsVisible((c) => c + 1), 200)
    return () => clearTimeout(t)
  }, [revealed, cardsVisible])

  if (isFailed) {
    return (
      <div className="flex flex-col items-center gap-3">
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-red-500/10">
          <svg className="h-8 w-8 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        </div>
        <h3 className="text-sm font-semibold text-[#E8ECF0]">Build Failed</h3>
        <p className="max-w-xs text-center text-xs text-[#6B7D8D]">
          Something went wrong during the build. Check the error details and try again.
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Browser frame mockup */}
      <div
        className={`w-[560px] overflow-hidden rounded-xl border transition-all duration-1000 ${
          revealed
            ? 'scale-100 border-[rgba(63,175,122,0.3)] shadow-[0_0_60px_rgba(63,175,122,0.15)]'
            : 'scale-95 border-white/[0.08] shadow-none'
        }`}
        style={{ background: '#0D2A3D' }}
      >
        {/* Title bar */}
        <div className="flex h-7 items-center gap-1.5 border-b border-white/[0.08] bg-black/30 px-3">
          <div className="h-2 w-2 rounded-full bg-white/10" />
          <div className="h-2 w-2 rounded-full bg-white/10" />
          <div className="h-2 w-2 rounded-full bg-white/10" />
          <span className="flex-1 text-center font-mono text-[10px] text-[#6B7D8D]">
            Your Prototype
          </span>
        </div>

        {/* Content preview */}
        <div className="flex" style={{ height: 280 }}>
          {/* Sidebar */}
          <div className="w-28 border-r border-white/[0.08] bg-black/20 p-2">
            {['Dashboard', 'Clients', 'Analytics', 'Settings'].map((item, i) => (
              <div
                key={item}
                className={`mb-0.5 rounded px-2 py-1 text-[9px] ${i === 0 ? 'bg-[rgba(63,175,122,0.15)] text-[#3FAF7A]' : 'text-[#6B7D8D]'}`}
              >
                {item}
              </div>
            ))}
          </div>

          {/* Main content area */}
          <div className="flex flex-1 flex-col gap-2 p-3">
            {/* Hero card */}
            <div
              className="rounded-md border border-[rgba(63,175,122,0.2)] transition-all duration-500"
              style={{
                height: 60,
                background: 'linear-gradient(135deg, rgba(63,175,122,0.15), rgba(63,175,122,0.05))',
                opacity: cardsVisible >= 1 ? 1 : 0,
                transform: cardsVisible >= 1 ? 'translateY(0)' : 'translateY(8px)',
              }}
            />
            {/* Content cards */}
            {[2, 3, 4, 5].map((n) => (
              <div
                key={n}
                className="rounded-md border border-white/[0.08] bg-white/[0.03] transition-all duration-400"
                style={{
                  height: 32,
                  opacity: cardsVisible >= n ? 1 : 0,
                  transform: cardsVisible >= n ? 'translateY(0)' : 'translateY(8px)',
                }}
              />
            ))}
          </div>
        </div>
      </div>

      {/* Status badge */}
      <div
        className="flex items-center gap-2 transition-opacity duration-600"
        style={{ opacity: revealed ? 1 : 0 }}
      >
        <div className="flex items-center gap-1.5 text-xs font-semibold text-[#3FAF7A]">
          <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
          Your prototype is live
        </div>
      </div>
    </div>
  )
}

// ══════════════════════════════════════════════
// Narration Bar
// ══════════════════════════════════════════════

function NarrationBar({ buildLog, phase }: { buildLog: BuildLogEntry[]; phase: CinematicPhase }) {
  const narration = useMemo(() => {
    // Derive narration text from the latest relevant events
    const payloadData = findEvent(buildLog, 'payload_assembled')?.data as PayloadAssembledData | undefined
    const phase0 = findEvent(buildLog, 'phase0_complete')?.data as Phase0CompleteData | undefined
    const archData = findEvent(buildLog, 'architecture_complete')?.data as ArchitectureCompleteData | undefined
    const screenEvents = findAllEvents(buildLog, 'screen_built')
    const pipelineComplete = findEvent(buildLog, 'pipeline_complete')

    if (pipelineComplete) {
      return 'Build complete — going live'
    }
    if (screenEvents.length > 0 && archData) {
      return `${screenEvents.length} of ${archData.total_screens} screens built`
    }
    if (archData) {
      return `${archData.total_screens} screens planned across ${archData.sections.length} sections`
    }
    if (payloadData) {
      return `Found ${payloadData.feature_count} features, ${payloadData.persona_count} personas, ${payloadData.flow_step_count} flow steps`
    }
    if (phase0) {
      const epicCount = phase0.epics?.length ?? 0
      return `${phase0.feature_count} features clustered into ${epicCount} epics`
    }
    if (phase === 'discovery') {
      return 'Readytogo Agents analyzing discovery data...'
    }
    return ''
  }, [buildLog, phase])

  // Stats from available data
  const payloadData = findEvent(buildLog, 'payload_assembled')?.data as PayloadAssembledData | undefined
  const phase0 = findEvent(buildLog, 'phase0_complete')?.data as Phase0CompleteData | undefined
  const archData = findEvent(buildLog, 'architecture_complete')?.data as ArchitectureCompleteData | undefined
  const screenEvents = findAllEvents(buildLog, 'screen_built')

  const featureCount = payloadData?.feature_count ?? phase0?.feature_count ?? 0
  const personaCount = payloadData?.persona_count ?? 0
  const epicCount = phase0?.epics?.length ?? 0
  const screenCount = screenEvents.length || archData?.total_screens || 0

  return (
    <>
      {/* Narration text */}
      {narration && (
        <div className="absolute bottom-16 left-1/2 z-10 max-w-md -translate-x-1/2 text-center text-xs text-[#9AABB8] transition-opacity duration-400">
          {narration}
        </div>
      )}

      {/* Stats ticker */}
      {(featureCount > 0 || personaCount > 0) && (
        <div className="absolute bottom-5 left-1/2 z-10 flex -translate-x-1/2 items-center gap-5 rounded-lg border border-white/[0.08] bg-black/30 px-5 py-2 backdrop-blur-xl">
          {featureCount > 0 && (
            <StatItem value={featureCount} label="features" color="#3FAF7A" />
          )}
          {personaCount > 0 && (
            <StatItem value={personaCount} label="personas" color="#4A9EFF" />
          )}
          {epicCount > 0 && (
            <StatItem value={epicCount} label="epics" color="#F5A623" />
          )}
          {screenCount > 0 && (
            <StatItem value={screenCount} label="screens" color="#A78BFA" />
          )}
        </div>
      )}
    </>
  )
}

function StatItem({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div className="flex items-center gap-1.5 text-[11px] text-[#6B7D8D]">
      <AnimatedCounter target={value} color={color} />
      {label}
    </div>
  )
}

// ══════════════════════════════════════════════
// Animated Counter
// ══════════════════════════════════════════════

function AnimatedCounter({ target, color }: { target: number; color?: string }) {
  const [current, setCurrent] = useState(0)
  const prevTarget = useRef(0)

  useEffect(() => {
    if (target === prevTarget.current) return
    prevTarget.current = target

    const start = current
    const diff = target - start
    if (diff === 0) return

    const steps = Math.min(Math.abs(diff), 20)
    const stepTime = Math.max(40, 600 / steps)
    let step = 0

    const iv = setInterval(() => {
      step++
      const progress = step / steps
      const eased = 1 - Math.pow(1 - progress, 3) // easeOutCubic
      setCurrent(Math.round(start + diff * eased))
      if (step >= steps) {
        clearInterval(iv)
        setCurrent(target)
      }
    }, stepTime)

    return () => clearInterval(iv)
  }, [target]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <span
      className="min-w-[18px] text-right font-mono text-sm font-bold tabular-nums"
      style={{ color: color ?? 'inherit' }}
    >
      {current}
    </span>
  )
}
