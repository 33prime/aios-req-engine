'use client'

import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { Target, Users, GitBranch, Sparkles, Loader2 } from 'lucide-react'
import { useSurfaces, useOutcomesTab } from '@/lib/hooks/use-api'
import { generateSurfaces } from '@/lib/api'
import { SurfaceDrawer } from './SurfaceDrawer'
import type { SolutionSurface } from '@/types/workspace'

// ══════════════════════════════════════════════════════════
// Color palette for outcomes
// ══════════════════════════════════════════════════════════

const OC_COLORS = [
  { fill: '#3FAF7A', bg: 'rgba(63,175,122,0.045)', bd: 'rgba(63,175,122,0.18)', light: 'rgba(63,175,122,0.09)' },
  { fill: '#044159', bg: 'rgba(4,65,89,0.04)', bd: 'rgba(4,65,89,0.16)', light: 'rgba(4,65,89,0.07)' },
  { fill: '#C49A1A', bg: 'rgba(196,154,26,0.035)', bd: 'rgba(196,154,26,0.18)', light: 'rgba(196,154,26,0.07)' },
  { fill: '#0A1E2F', bg: 'rgba(10,30,47,0.025)', bd: 'rgba(10,30,47,0.13)', light: 'rgba(10,30,47,0.05)' },
  { fill: '#2D6B4A', bg: 'rgba(45,107,74,0.04)', bd: 'rgba(45,107,74,0.16)', light: 'rgba(45,107,74,0.07)' },
  { fill: '#6B4A2D', bg: 'rgba(107,74,45,0.04)', bd: 'rgba(107,74,45,0.16)', light: 'rgba(107,74,45,0.07)' },
]

const PERSONA_COLORS: Record<string, string> = {}
const PALETTE = ['#3FAF7A', '#044159', '#0A1E2F', '#2D6B4A', '#C49A1A', '#6B4A2D']
let pIdx = 0
function getPersonaColor(name: string) {
  if (!PERSONA_COLORS[name]) { PERSONA_COLORS[name] = PALETTE[pIdx % PALETTE.length]; pIdx++ }
  return PERSONA_COLORS[name]
}

// ══════════════════════════════════════════════════════════
// Types
// ══════════════════════════════════════════════════════════

interface Outcome {
  id: string
  title: string
  horizon: string
  strength_score: number
  actors: Array<{ persona_name: string }>
}

interface ConvergenceMapProps {
  projectId: string
}

type ViewMode = 'outcomes' | 'actors'
type TimeMode = 'now' | 'evolution'

// ══════════════════════════════════════════════════════════
// Layout computation
// ══════════════════════════════════════════════════════════

function computeLayout(
  surfaces: SolutionSurface[],
  outcomes: Outcome[],
  timeMode: TimeMode,
) {
  // Position outcomes on the left
  const visOc = timeMode === 'now' ? outcomes.filter(o => o.horizon === 'h1') : outcomes
  const ocPositions: Record<string, { x: number; y: number }> = {}
  visOc.forEach((o, i) => {
    ocPositions[o.id] = { x: 30, y: 40 + i * 155 }
  })

  // Position surfaces by horizon columns
  const visSf = timeMode === 'now'
    ? surfaces.filter(s => s.horizon === 'h1')
    : surfaces

  const h1 = visSf.filter(s => s.horizon === 'h1')
  const h2 = visSf.filter(s => s.horizon === 'h2')
  const h3 = visSf.filter(s => s.horizon === 'h3')

  const sfPositions: Record<string, { x: number; y: number }> = {}

  // H1: two columns
  const h1Col1 = h1.slice(0, Math.ceil(h1.length / 2))
  const h1Col2 = h1.slice(Math.ceil(h1.length / 2))
  h1Col1.forEach((s, i) => { sfPositions[s.id] = { x: 340, y: 30 + i * 190 } })
  h1Col2.forEach((s, i) => { sfPositions[s.id] = { x: 620, y: 30 + i * 190 } })

  // H2
  h2.forEach((s, i) => { sfPositions[s.id] = { x: 920, y: 30 + i * 175 } })

  // H3
  h3.forEach((s, i) => { sfPositions[s.id] = { x: 1200, y: 60 + i * 175 } })

  // Use stored positions if available, otherwise computed
  visSf.forEach(s => {
    if (s.position_x > 0 || s.position_y > 0) {
      sfPositions[s.id] = { x: s.position_x, y: s.position_y }
    }
  })

  return { ocPositions, sfPositions, visOc, visSf }
}

// ══════════════════════════════════════════════════════════
// Main component
// ══════════════════════════════════════════════════════════

export function ConvergenceMap({ projectId }: ConvergenceMapProps) {
  const { data: surfacesData, isLoading: surfacesLoading, mutate: mutateSurfaces } = useSurfaces(projectId)
  const { data: outcomesData } = useOutcomesTab(projectId)

  const [viewMode, setViewMode] = useState<ViewMode>('outcomes')
  const [timeMode, setTimeMode] = useState<TimeMode>('now')
  const [selectedSurface, setSelectedSurface] = useState<string | null>(null)
  const [selectedOutcome, setSelectedOutcome] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)

  // Pan & zoom state
  const [scale, setScale] = useState(0.78)
  const [pan, setPan] = useState({ x: 20, y: 20 })
  const isPanning = useRef(false)
  const panStart = useRef({ x: 0, y: 0 })
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLDivElement>(null)

  const surfaces = surfacesData?.surfaces ?? []
  const outcomes: Outcome[] = useMemo(() => {
    const raw = (outcomesData as Record<string, unknown>)?.outcomes as Outcome[] | undefined
    return (raw ?? []).slice(0, 6)
  }, [outcomesData])

  const layout = useMemo(
    () => computeLayout(surfaces, outcomes, timeMode),
    [surfaces, outcomes, timeMode],
  )

  // ── Helpers ──
  const getOcColor = useCallback((idx: number) => OC_COLORS[idx % OC_COLORS.length], [])

  const uniqueActors = useCallback((sf: SolutionSurface) => {
    const actors = new Set<string>()
    sf.linked_outcome_ids.forEach(oid => {
      const oc = outcomes.find(o => o.id === oid)
      oc?.actors?.forEach(a => actors.add(a.persona_name))
    })
    return actors
  }, [outcomes])

  const isXP = useCallback((sf: SolutionSurface) => uniqueActors(sf).size >= 2, [uniqueActors])

  const isDimmed = useCallback((sf: SolutionSurface) => {
    if (selectedOutcome && !sf.linked_outcome_ids.includes(selectedOutcome)) return true
    return false
  }, [selectedOutcome])

  const isOcDimmed = useCallback((oc: Outcome) => {
    if (selectedOutcome && selectedOutcome !== oc.id) return true
    if (selectedSurface) {
      const sf = surfaces.find(s => s.id === selectedSurface)
      if (sf && !sf.linked_outcome_ids.includes(oc.id)) return true
    }
    return false
  }, [selectedOutcome, selectedSurface, surfaces])

  // ── Pan / Zoom ──
  const applyTransform = useCallback(() => {
    if (canvasRef.current) {
      canvasRef.current.style.transform = `translate(${pan.x}px,${pan.y}px) scale(${scale})`
    }
  }, [pan, scale])

  useEffect(() => { applyTransform() }, [applyTransform])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const d = e.deltaY > 0 ? -0.05 : 0.05
    setScale(prev => {
      const next = Math.max(0.25, Math.min(2, prev + d))
      const rect = wrapRef.current?.getBoundingClientRect()
      if (rect) {
        const mx = e.clientX - rect.left
        const my = e.clientY - rect.top
        setPan(p => ({
          x: mx - (mx - p.x) * (next / prev),
          y: my - (my - p.y) * (next / prev),
        }))
      }
      return next
    })
  }, [])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.target === wrapRef.current || e.target === canvasRef.current || (e.target as HTMLElement).tagName === 'svg') {
      isPanning.current = true
      panStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
      if (selectedSurface) setSelectedSurface(null)
    }
  }, [pan, selectedSurface])

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isPanning.current) {
      setPan({ x: e.clientX - panStart.current.x, y: e.clientY - panStart.current.y })
    }
  }, [])

  const handleMouseUp = useCallback(() => { isPanning.current = false }, [])

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [handleMouseMove, handleMouseUp])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setSelectedSurface(null)
        setSelectedOutcome(null)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // ── Fit view ──
  const fitView = useCallback(() => {
    if (!wrapRef.current) return
    const all = [
      ...layout.visOc.map((_, i) => ({ x: 30, y: 40 + i * 155, w: 200, h: 140 })),
      ...layout.visSf.map(s => {
        const pos = layout.sfPositions[s.id] || { x: 0, y: 0 }
        return { x: pos.x, y: pos.y, w: 300, h: 180 }
      }),
    ]
    if (!all.length) return
    const pad = 60
    let mx = Infinity, my = Infinity, Mx = -Infinity, My = -Infinity
    all.forEach(n => { mx = Math.min(mx, n.x); my = Math.min(my, n.y); Mx = Math.max(Mx, n.x + n.w); My = Math.max(My, n.y + n.h) })
    const w = Mx - mx + pad * 2, h = My - my + pad * 2
    const cw = wrapRef.current.clientWidth - (selectedSurface ? 430 : 0)
    const ch = wrapRef.current.clientHeight
    const newScale = Math.min(cw / w, ch / h, 0.95)
    setPan({
      x: (cw - (Mx - mx) * newScale) / 2 - mx * newScale,
      y: Math.max(20, (ch - (My - my) * newScale) / 2 - my * newScale),
    })
    setScale(newScale)
  }, [layout, selectedSurface])

  useEffect(() => { fitView() }, [timeMode, surfaces.length])

  // ── Generate ──
  const handleGenerate = useCallback(async () => {
    setIsGenerating(true)
    try {
      await generateSurfaces(projectId, true)
      mutateSurfaces()
    } finally {
      setIsGenerating(false)
    }
  }, [projectId, mutateSurfaces])

  // ── SVG connections ──
  const renderConnections = useCallback(() => {
    const paths: JSX.Element[] = []
    if (viewMode !== 'outcomes') return paths

    layout.visOc.forEach((oc, oi) => {
      const ocPos = layout.ocPositions[oc.id]
      if (!ocPos) return
      const color = getOcColor(oi)

      layout.visSf.forEach(sf => {
        if (!sf.linked_outcome_ids.includes(oc.id)) return
        const sfPos = layout.sfPositions[sf.id]
        if (!sfPos) return

        const ox = ocPos.x + 200, oy = ocPos.y + 70
        const px = sfPos.x, py = sfPos.y + 80
        let opacity = 0.12, sw = 1.5

        if (selectedOutcome === oc.id) { opacity = 0.45; sw = 2.5 }
        else if (selectedOutcome) { opacity = 0.02; sw = 1 }
        else if (selectedSurface === sf.id) { opacity = 0.4; sw = 2.5 }
        else if (selectedSurface) { opacity = 0.02; sw = 1 }

        const cpx = Math.max(60, Math.abs(px - ox) * 0.35)
        const d = `M${ox},${oy} C${ox + cpx},${oy} ${px - cpx},${py} ${px},${py}`

        paths.push(
          <path
            key={`${oc.id}-${sf.id}`}
            d={d}
            fill="none"
            stroke={color.fill}
            strokeWidth={sw}
            opacity={opacity}
            markerEnd="url(#ah)"
          />
        )
      })
    })

    // Evolution lines (evo mode)
    if (timeMode === 'evolution') {
      layout.visSf.forEach(sf => {
        if (!sf.evolves_from_id) return
        const from = layout.visSf.find(s => s.id === sf.evolves_from_id)
        if (!from) return
        const fromPos = layout.sfPositions[from.id]
        const toPos = layout.sfPositions[sf.id]
        if (!fromPos || !toPos) return

        const fx = fromPos.x + 280, fy = fromPos.y + 80
        const tx = toPos.x, ty = toPos.y + 80
        const cpx = Math.max(40, (tx - fx) * 0.35)
        const d = `M${fx},${fy} C${fx + cpx},${fy} ${tx - cpx},${ty} ${tx},${ty}`

        paths.push(
          <path
            key={`evo-${sf.id}`}
            d={d}
            fill="none"
            stroke="#044159"
            strokeWidth={1.5}
            strokeDasharray="6 4"
            opacity={0.22}
            markerEnd="url(#ah-evo)"
          />
        )
      })
    }

    return paths
  }, [layout, viewMode, timeMode, selectedOutcome, selectedSurface, getOcColor])

  // ── Empty state ──
  if (surfacesLoading && !surfaces.length) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex items-center gap-2 text-[13px] text-text-placeholder">
          <Loader2 className="w-4 h-4 animate-spin" />
          Loading convergence map...
        </div>
      </div>
    )
  }

  if (!surfaces.length) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-[rgba(63,175,122,0.06)] flex items-center justify-center">
          <GitBranch className="w-7 h-7 text-[#3FAF7A]" />
        </div>
        <div className="text-center">
          <div className="text-[15px] font-semibold text-[#1D1D1F] mb-1">No solution surfaces yet</div>
          <p className="text-[12px] text-[#718096] max-w-md leading-relaxed">
            Solution surfaces are generated from your outcomes, features, and workflows.
            They show how everything converges into the screens your users will experience.
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
        >
          {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {isGenerating ? 'Generating...' : 'Generate Solution Surfaces'}
        </button>
      </div>
    )
  }

  // ── Size classes ──
  const szClass = (sf: SolutionSurface) => {
    const n = sf.linked_outcome_ids.length
    return n >= 3 ? 'w-[300px]' : n >= 2 ? 'w-[260px]' : 'w-[220px]'
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#E5E5E5] bg-white flex-shrink-0">
        {/* View toggle */}
        <div className="flex rounded-md overflow-hidden border border-[#E5E5E5]">
          <button
            onClick={() => { setViewMode('outcomes'); setSelectedOutcome(null) }}
            className={`flex items-center gap-1.5 px-3 py-1 text-[11px] font-semibold transition-colors ${
              viewMode === 'outcomes' ? 'bg-[#E8F5E9] text-[#25785A]' : 'text-[#A0AEC0] hover:text-[#666]'
            }`}
          >
            <Target className="w-3 h-3" /> Outcomes
          </button>
          <button
            onClick={() => { setViewMode('actors'); setSelectedOutcome(null) }}
            className={`flex items-center gap-1.5 px-3 py-1 text-[11px] font-semibold transition-colors ${
              viewMode === 'actors' ? 'bg-[rgba(4,65,89,0.06)] text-[#044159]' : 'text-[#A0AEC0] hover:text-[#666]'
            }`}
          >
            <Users className="w-3 h-3" /> Actors
          </button>
        </div>

        <div className="w-px h-4 bg-[#E5E5E5]" />

        {/* Stats */}
        <div className="flex gap-3 text-[10px]">
          <span><b className="text-[#3FAF7A]">{layout.visOc.length}</b> <span className="text-[#A0AEC0] uppercase tracking-wide font-semibold">Outcomes</span></span>
          <span><b className="text-[#3FAF7A]">{layout.visSf.filter(s => s.horizon !== 'h3').length}</b> <span className="text-[#A0AEC0] uppercase tracking-wide font-semibold">Surfaces</span></span>
          <span><b className="text-[#3FAF7A]">{layout.visSf.filter(s => isXP(s)).length}</b> <span className="text-[#A0AEC0] uppercase tracking-wide font-semibold">Cross-Persona</span></span>
        </div>

        <div className="flex-1" />

        {/* Time toggle */}
        <div className="flex rounded-md overflow-hidden border border-[#E5E5E5]">
          <button
            onClick={() => setTimeMode('now')}
            className={`px-3 py-1 text-[11px] font-semibold transition-colors ${
              timeMode === 'now' ? 'bg-[#E8F5E9] text-[#25785A]' : 'text-[#A0AEC0] hover:text-[#666]'
            }`}
          >
            Now
          </button>
          <button
            onClick={() => setTimeMode('evolution')}
            className={`px-3 py-1 text-[11px] font-semibold transition-colors ${
              timeMode === 'evolution' ? 'bg-[rgba(63,175,122,0.08)] text-[#25785A]' : 'text-[#A0AEC0] hover:text-[#666]'
            }`}
          >
            Evolution
          </button>
        </div>

        <button onClick={fitView} className="px-2.5 py-1 text-[10px] font-semibold text-[#A0AEC0] border border-[#E5E5E5] rounded-md hover:text-[#666] hover:border-[#ccc] transition-colors">
          Fit
        </button>
        <span className="text-[9px] text-[#A0AEC0] font-mono w-8 text-right">{Math.round(scale * 100)}%</span>
      </div>

      {/* Canvas + Drawer */}
      <div className="flex-1 flex overflow-hidden">
        {/* Canvas area */}
        <div
          ref={wrapRef}
          className="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing"
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
        >
          {/* Timeline bar (evolution mode) */}
          {timeMode === 'evolution' && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-0 pointer-events-none">
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-2 h-2 rounded-full border-2 border-[#3FAF7A] bg-[rgba(63,175,122,0.1)]" />
                <span className="text-[7px] font-bold uppercase tracking-wider text-[#3FAF7A]">Now</span>
              </div>
              <div className="w-16 h-[1.5px] bg-gradient-to-r from-[#3FAF7A] to-[#044159] -mb-3" />
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-2 h-2 rounded-full border-2 border-[#044159] bg-[rgba(4,65,89,0.06)]" />
                <span className="text-[7px] font-bold uppercase tracking-wider text-[#044159]">Next</span>
              </div>
              <div className="w-16 h-[1.5px] bg-gradient-to-r from-[#044159] to-[#C49A1A] -mb-3" />
              <div className="flex flex-col items-center gap-0.5">
                <div className="w-2 h-2 rounded-full border-2 border-[#C49A1A] bg-[rgba(196,154,26,0.06)]" />
                <span className="text-[7px] font-bold uppercase tracking-wider text-[#C49A1A]">Vision</span>
              </div>
            </div>
          )}

          <div
            ref={canvasRef}
            className="absolute top-0 left-0 origin-top-left w-[4000px] h-[3000px]"
          >
            {/* SVG connections */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-[1]">
              <defs>
                <marker id="ah" markerWidth="6" markerHeight="5" refX="5" refY="2.5" orient="auto">
                  <path d="M0,.5 L5,2.5 L0,4.5" fill="rgba(0,0,0,.08)" />
                </marker>
                <marker id="ah-evo" markerWidth="6" markerHeight="5" refX="5" refY="2.5" orient="auto">
                  <path d="M0,.5 L5,2.5 L0,4.5" fill="rgba(4,65,89,.3)" />
                </marker>
              </defs>
              {renderConnections()}
            </svg>

            {/* Outcome nodes (left side) */}
            {viewMode === 'outcomes' && layout.visOc.map((oc, oi) => {
              const pos = layout.ocPositions[oc.id]
              if (!pos) return null
              const c = getOcColor(oi)
              const dim = isOcDimmed(oc)
              const sel = selectedOutcome === oc.id
              const strDots = [20, 40, 60, 80, 100].map(t => (
                <div key={t} className="w-[3.5px] h-[3.5px] rounded-full" style={{ background: oc.strength_score >= t ? c.fill : 'rgba(0,0,0,.05)' }} />
              ))
              const hzStyle = oc.horizon === 'h1'
                ? 'bg-[rgba(63,175,122,0.08)] text-[#2D6B4A]'
                : 'bg-[rgba(4,65,89,0.06)] text-[#044159]'
              const actor = oc.actors?.[0]?.persona_name || ''

              return (
                <div
                  key={oc.id}
                  className={`absolute w-[200px] rounded-[9px] p-[9px_11px] cursor-pointer z-[3] border-[1.5px] transition-all duration-200 ${
                    dim ? 'opacity-[0.06] pointer-events-none' : ''
                  } ${sel ? 'shadow-[0_0_0_2px_#3FAF7A,0_4px_16px_rgba(63,175,122,0.10)]' : 'hover:shadow-[0_4px_16px_rgba(0,0,0,0.05)]'}`}
                  style={{
                    left: pos.x, top: pos.y,
                    background: c.bg,
                    borderColor: dim ? 'transparent' : c.bd,
                  }}
                  onClick={() => setSelectedOutcome(selectedOutcome === oc.id ? null : oc.id)}
                >
                  <div className="flex items-start gap-1.5 mb-1">
                    <div className="min-w-[20px] h-[20px] rounded-[5px] flex items-center justify-center text-[8px] font-extrabold text-white flex-shrink-0" style={{ background: c.fill }}>
                      {oi + 1}
                    </div>
                    <div>
                      <div className="text-[7px] font-bold uppercase tracking-[0.4px] mb-0.5" style={{ color: getPersonaColor(actor) }}>{actor}</div>
                      <div className="text-[10px] font-bold leading-[1.35]" style={{ color: c.fill === '#0A1E2F' ? '#0A1E2F' : c.fill }}>{oc.title}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`text-[7px] font-bold px-1 py-0.5 rounded ${hzStyle}`}>{oc.horizon.toUpperCase()}</span>
                  </div>
                  <div className="flex items-center gap-[3px] mt-1">
                    <span className="text-[6.5px] font-bold uppercase tracking-[0.4px]" style={{ color: c.fill }}>Strength</span>
                    <div className="flex gap-[1.5px]">{strDots}</div>
                  </div>
                </div>
              )
            })}

            {/* Surface cards */}
            {layout.visSf.map(sf => {
              const pos = layout.sfPositions[sf.id]
              if (!pos) return null
              const dim = isDimmed(sf)
              const sel = selectedSurface === sf.id
              const xp = isXP(sf)
              const isH2 = sf.horizon === 'h2'
              const isH3 = sf.horizon === 'h3'

              const ribbons = sf.linked_outcome_ids.map(oid => {
                const oi = outcomes.findIndex(o => o.id === oid)
                const c = getOcColor(oi >= 0 ? oi : 0)
                return <div key={oid} className="w-[5px] h-[5px] rounded-sm" style={{ background: c.fill }} />
              })

              const dots = sf.linked_outcome_ids.map(oid => {
                const oi = outcomes.findIndex(o => o.id === oid)
                const c = getOcColor(oi >= 0 ? oi : 0)
                return <div key={oid} className="w-[6px] h-[6px] rounded-full" style={{ background: c.fill }} />
              })

              const borderLeft = sf.linked_outcome_ids.length >= 3
                ? '5px solid #3FAF7A'
                : sf.linked_outcome_ids.length >= 2
                ? '4px solid rgba(63,175,122,0.35)'
                : '3px solid rgba(10,30,47,0.10)'

              return (
                <div
                  key={sf.id}
                  className={`absolute ${szClass(sf)} bg-white rounded-[11px] cursor-pointer z-[2] flex flex-col overflow-visible transition-all duration-300
                    ${dim ? 'opacity-[0.05] pointer-events-none' : ''}
                    ${sel ? 'z-[20] shadow-[0_0_0_2px_#3FAF7A,0_8px_32px_rgba(0,0,0,0.08)]' : 'shadow-[0_1px_4px_rgba(0,0,0,0.03)] hover:shadow-[0_6px_24px_rgba(0,0,0,0.06)]'}
                    ${xp && !isH2 && !isH3 ? 'shadow-[0_1px_4px_rgba(0,0,0,0.03),-3px_0_14px_rgba(63,175,122,0.06),3px_0_14px_rgba(4,65,89,0.04)]' : ''}
                    ${isH2 ? 'border-dashed border-[rgba(4,65,89,0.15)]' : 'border-[1.5px] border-[rgba(10,30,47,0.06)]'}
                    ${isH3 ? 'border-dashed border-[rgba(196,154,26,0.22)] bg-gradient-to-br from-[rgba(196,154,26,0.015)] to-white/85' : ''}
                  `}
                  style={{ left: pos.x, top: pos.y, borderLeft: !isH2 && !isH3 ? borderLeft : undefined }}
                  onClick={() => {
                    setSelectedSurface(selectedSurface === sf.id ? null : sf.id)
                    setSelectedOutcome(null)
                  }}
                >
                  {/* Browser bar */}
                  <div className={`h-[20px] flex items-center px-[7px] gap-[3px] border-b border-[rgba(0,0,0,0.03)] rounded-t-[11px] ${
                    isH3 ? 'bg-[rgba(196,154,26,0.03)]' : 'bg-[rgba(0,0,0,0.012)]'
                  }`}>
                    <div className="w-1 h-1 rounded-full bg-[rgba(220,80,80,0.20)]" />
                    <div className="w-1 h-1 rounded-full bg-[rgba(212,180,50,0.28)]" />
                    <div className="w-1 h-1 rounded-full bg-[rgba(63,175,122,0.25)]" />
                    <span className="flex-1 mx-1 text-[7px] font-medium text-[#A0AEC0] truncate">{sf.route}</span>
                    <div className="flex gap-[2px]">{ribbons}</div>
                  </div>

                  {/* Body */}
                  <div className="px-[10px] pt-[7px] pb-1">
                    <div className={`font-bold leading-[1.2] mb-0.5 ${
                      isH3 ? 'text-[#C49A1A] text-[12px]' : sf.linked_outcome_ids.length >= 3 ? 'text-[#0A1E2F] text-[14px]' : 'text-[#0A1E2F] text-[12px]'
                    }`}>
                      {sf.title}
                    </div>
                    <div className="text-[8.5px] text-[#7B7B7B] leading-[1.4] line-clamp-2">{sf.description}</div>
                  </div>

                  {/* Outcome dots */}
                  <div className="flex gap-[3px] px-[10px] py-0.5 flex-wrap">{dots}</div>

                  {/* Convergence indicator */}
                  {sf.convergence_insight && sf.linked_outcome_ids.length >= 2 && (
                    <div className="mx-2 mb-0.5 px-2 py-1 rounded-[6px] bg-gradient-to-br from-[rgba(63,175,122,0.025)] to-[rgba(4,65,89,0.015)] border border-[rgba(63,175,122,0.06)]">
                      <div className="flex items-center gap-1 text-[6.5px] font-bold uppercase tracking-[0.5px] text-[#3FAF7A]">
                        <span className="bg-[#3FAF7A] text-white px-[3px] rounded-sm text-[6.5px] font-extrabold">{sf.linked_outcome_ids.length}</span>
                        converge
                        {xp && <span className="bg-[#044159] text-white px-1 rounded-sm text-[6px] font-bold">cross-persona</span>}
                      </div>
                    </div>
                  )}

                  {/* Footer */}
                  <div className="px-[10px] py-1">
                    <span className="text-[7px] font-medium text-[#A0AEC0]">
                      {isH3 ? 'H3 · Vision' : isH2 ? `${sf.linked_outcome_ids.length} outcome${sf.linked_outcome_ids.length !== 1 ? 's' : ''} · H2` : `${sf.linked_outcome_ids.length} outcome${sf.linked_outcome_ids.length !== 1 ? 's' : ''}${xp ? ' · cross-persona' : ''}`}
                    </span>
                  </div>

                  {/* Stale indicator */}
                  {sf.is_stale && (
                    <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-[#C49A1A] border-2 border-white" title={sf.stale_reason || 'Upstream change detected'} />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Drawer */}
        <SurfaceDrawer
          projectId={projectId}
          surfaceId={selectedSurface}
          surfaces={surfaces}
          outcomes={outcomes}
          onClose={() => setSelectedSurface(null)}
        />
      </div>
    </div>
  )
}
