'use client'

import { useState, useCallback, useRef, useEffect, useMemo } from 'react'
import { Target, Users, GitBranch, Sparkles, Loader2 } from 'lucide-react'
import { useSurfaces, useOutcomesTab } from '@/lib/hooks/use-api'
import { generateSurfaces } from '@/lib/api'
import { SurfaceDrawer } from './SurfaceDrawer'
import type { SolutionSurface } from '@/types/workspace'

// ══════════════════════════════════════════════════════════
// Colors
// ══════════════════════════════════════════════════════════

const OC_COLORS = [
  { fill: '#3FAF7A', bg: 'rgba(63,175,122,0.045)', bd: 'rgba(63,175,122,0.18)' },
  { fill: '#044159', bg: 'rgba(4,65,89,0.04)', bd: 'rgba(4,65,89,0.16)' },
  { fill: '#C49A1A', bg: 'rgba(196,154,26,0.035)', bd: 'rgba(196,154,26,0.18)' },
  { fill: '#0A1E2F', bg: 'rgba(10,30,47,0.025)', bd: 'rgba(10,30,47,0.13)' },
  { fill: '#2D6B4A', bg: 'rgba(45,107,74,0.04)', bd: 'rgba(45,107,74,0.16)' },
  { fill: '#6B4A2D', bg: 'rgba(107,74,45,0.04)', bd: 'rgba(107,74,45,0.16)' },
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
  id: string; title: string; horizon: string; strength_score: number
  actors: Array<{ persona_name: string }>
}
interface ConvergenceMapProps { projectId: string }
type ViewMode = 'outcomes' | 'actors'
type TimeMode = 'now' | 'evolution'

// Card dimensions
const OC_W = 200, OC_H = 130
const SF_WIDTHS: Record<string, number> = {} // computed per surface
function sfWidth(sf: SolutionSurface) { return sf.linked_outcome_ids.length >= 3 ? 300 : sf.linked_outcome_ids.length >= 2 ? 260 : 220 }
const SF_H = 160

// ══════════════════════════════════════════════════════════
// Layout
// ══════════════════════════════════════════════════════════

function computeLayout(surfaces: SolutionSurface[], outcomes: Outcome[], timeMode: TimeMode) {
  const visOc = timeMode === 'now' ? outcomes.filter(o => o.horizon === 'h1') : outcomes
  const visSf = timeMode === 'now' ? surfaces.filter(s => s.horizon === 'h1') : [...surfaces]

  const ocPositions: Record<string, { x: number; y: number }> = {}
  // Vertically center outcomes relative to surfaces
  const totalSfHeight = Math.max(visSf.filter(s => s.horizon === 'h1').length, 1) * 180
  const totalOcHeight = visOc.length * (OC_H + 25)
  const ocStartY = Math.max(20, (totalSfHeight - totalOcHeight) / 2 + 20)
  visOc.forEach((o, i) => { ocPositions[o.id] = { x: 30, y: ocStartY + i * (OC_H + 25) } })

  const sfPositions: Record<string, { x: number; y: number }> = {}
  const h1 = visSf.filter(s => s.horizon === 'h1')
  const h2 = visSf.filter(s => s.horizon === 'h2')
  const h3 = visSf.filter(s => s.horizon === 'h3')

  // H1: two columns, centered vertically
  const h1Col1 = h1.slice(0, Math.ceil(h1.length / 2))
  const h1Col2 = h1.slice(Math.ceil(h1.length / 2))
  h1Col1.forEach((s, i) => { sfPositions[s.id] = { x: 320, y: 20 + i * 180 } })
  h1Col2.forEach((s, i) => { sfPositions[s.id] = { x: 620, y: 20 + i * 180 } })
  h2.forEach((s, i) => { sfPositions[s.id] = { x: 940, y: 20 + i * 175 } })
  h3.forEach((s, i) => { sfPositions[s.id] = { x: 1240, y: 40 + i * 175 } })

  // Use DB positions if available
  visSf.forEach(s => {
    if (s.position_x > 0 || s.position_y > 0) {
      sfPositions[s.id] = { x: s.position_x, y: s.position_y }
    }
  })

  return { ocPositions, sfPositions, visOc, visSf }
}

// ══════════════════════════════════════════════════════════
// Evolution chain helper
// ══════════════════════════════════════════════════════════

function getEvoChain(surfaces: SolutionSurface[], surfaceId: string): Set<string> {
  const chain = new Set<string>([surfaceId])
  // backward
  let cur = surfaces.find(s => s.id === surfaceId)
  while (cur?.evolves_from_id) {
    const parentId = cur.evolves_from_id
    if (chain.has(parentId)) break // cycle guard
    chain.add(parentId)
    cur = surfaces.find(s => s.id === parentId)
  }
  // forward
  const fwd = (id: string) => {
    surfaces.filter(s => s.evolves_from_id === id).forEach(s => {
      if (!chain.has(s.id)) { chain.add(s.id); fwd(s.id) }
    })
  }
  fwd(surfaceId)
  return chain
}

// ══════════════════════════════════════════════════════════
// Component
// ══════════════════════════════════════════════════════════

export function ConvergenceMap({ projectId }: ConvergenceMapProps) {
  const { data: surfacesData, isLoading: surfacesLoading, mutate: mutateSurfaces } = useSurfaces(projectId)
  const { data: outcomesData } = useOutcomesTab(projectId)

  const [viewMode, setViewMode] = useState<ViewMode>('outcomes')
  const [timeMode, setTimeMode] = useState<TimeMode>('now')
  const [selectedSurface, setSelectedSurface] = useState<string | null>(null)
  const [selectedOutcome, setSelectedOutcome] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)

  // Drag state: absolute positions that override layout
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({})
  const dragState = useRef<{ id: string; offsetX: number; offsetY: number } | null>(null)
  const didDrag = useRef(false)

  // Pan & zoom
  const [scale, setScale] = useState(0.78)
  const [pan, setPan] = useState({ x: 20, y: 20 })
  const isPanning = useRef(false)
  const panStart = useRef({ x: 0, y: 0 })
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLDivElement>(null)

  const surfaces = surfacesData?.surfaces ?? []
  const outcomes: Outcome[] = useMemo(() => {
    const raw = (outcomesData as Record<string, unknown> | undefined)?.outcomes
    return (Array.isArray(raw) ? raw : []).slice(0, 6) as Outcome[]
  }, [outcomesData])

  const layout = useMemo(
    () => computeLayout(surfaces, outcomes, timeMode),
    [surfaces, outcomes, timeMode],
  )

  // Get effective position (drag override or layout default)
  const pos = useCallback((id: string): { x: number; y: number } => {
    if (positions[id]) return positions[id]
    return layout.ocPositions[id] || layout.sfPositions[id] || { x: 0, y: 0 }
  }, [positions, layout])

  const getOcColor = (idx: number) => OC_COLORS[idx % OC_COLORS.length]

  // ── Selection logic ──
  const evoChain = useMemo(() => {
    if (!selectedSurface || timeMode !== 'evolution') return null
    return getEvoChain(surfaces, selectedSurface)
  }, [selectedSurface, timeMode, surfaces])

  const chainOcIds = useMemo(() => {
    if (!evoChain) return null
    const ids = new Set<string>()
    evoChain.forEach(sid => {
      const s = surfaces.find(x => x.id === sid)
      s?.linked_outcome_ids.forEach(oid => ids.add(oid))
    })
    return ids
  }, [evoChain, surfaces])

  const isSfDimmed = useCallback((sf: SolutionSurface) => {
    if (!selectedOutcome && !selectedSurface) return false
    if (selectedOutcome) return !sf.linked_outcome_ids.includes(selectedOutcome)
    if (selectedSurface === sf.id) return false
    if (evoChain) return !evoChain.has(sf.id)
    return true
  }, [selectedOutcome, selectedSurface, evoChain])

  const isOcDimmed = useCallback((oc: Outcome) => {
    if (!selectedOutcome && !selectedSurface) return false
    if (selectedOutcome) return selectedOutcome !== oc.id
    if (selectedSurface) {
      if (evoChain && chainOcIds) return !chainOcIds.has(oc.id)
      const sf = surfaces.find(s => s.id === selectedSurface)
      return sf ? !sf.linked_outcome_ids.includes(oc.id) : true
    }
    return false
  }, [selectedOutcome, selectedSurface, surfaces, evoChain, chainOcIds])

  const isXP = (sf: SolutionSurface) => {
    const actors = new Set<string>()
    sf.linked_outcome_ids.forEach(oid => {
      outcomes.find(o => o.id === oid)?.actors?.forEach(a => actors.add(a.persona_name))
    })
    return actors.size >= 2
  }

  // ── Drag handling ──
  const onCardMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    const p = pos(id)
    dragState.current = {
      id,
      offsetX: e.clientX / scale - p.x + pan.x / scale,
      offsetY: e.clientY / scale - p.y + pan.y / scale,
    }
    didDrag.current = false
  }, [pos, scale, pan])

  // ── Pan / Zoom ──
  useEffect(() => {
    if (canvasRef.current) {
      canvasRef.current.style.transform = `translate(${pan.x}px,${pan.y}px) scale(${scale})`
    }
  }, [pan, scale])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const d = e.deltaY > 0 ? -0.05 : 0.05
    setScale(prev => {
      const next = Math.max(0.25, Math.min(2, prev + d))
      const rect = wrapRef.current?.getBoundingClientRect()
      if (rect) {
        const mx = e.clientX - rect.left, my = e.clientY - rect.top
        setPan(p => ({ x: mx - (mx - p.x) * (next / prev), y: my - (my - p.y) * (next / prev) }))
      }
      return next
    })
  }, [])

  const handleCanvasMouseDown = useCallback((e: React.MouseEvent) => {
    const tag = (e.target as HTMLElement).tagName
    if (e.target === wrapRef.current || e.target === canvasRef.current || tag === 'svg' || tag === 'path') {
      isPanning.current = true
      panStart.current = { x: e.clientX - pan.x, y: e.clientY - pan.y }
    }
  }, [pan])

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (dragState.current) {
        didDrag.current = true
        const newX = e.clientX / scale - dragState.current.offsetX + pan.x / scale
        const newY = e.clientY / scale - dragState.current.offsetY + pan.y / scale
        setPositions(prev => ({ ...prev, [dragState.current!.id]: { x: newX, y: newY } }))
        return
      }
      if (isPanning.current) {
        setPan({ x: e.clientX - panStart.current.x, y: e.clientY - panStart.current.y })
      }
    }
    const onUp = () => { isPanning.current = false; dragState.current = null }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [scale, pan])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setSelectedSurface(null); setSelectedOutcome(null) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  // ── Fit view ──
  const fitView = useCallback(() => {
    if (!wrapRef.current) return
    const nodes = [
      ...layout.visOc.map(o => ({ ...pos(o.id), w: OC_W, h: OC_H })),
      ...layout.visSf.map(s => ({ ...pos(s.id), w: sfWidth(s), h: SF_H })),
    ]
    if (!nodes.length) return
    const pad = 50
    let mx = Infinity, my = Infinity, Mx = -Infinity, My = -Infinity
    nodes.forEach(n => { mx = Math.min(mx, n.x); my = Math.min(my, n.y); Mx = Math.max(Mx, n.x + n.w); My = Math.max(My, n.y + n.h) })
    const w = Mx - mx + pad * 2, h = My - my + pad * 2
    const cw = wrapRef.current.clientWidth - (selectedSurface ? 430 : 0), ch = wrapRef.current.clientHeight
    const s = Math.min(cw / w, ch / h, 0.95)
    setPan({ x: (cw - (Mx - mx) * s) / 2 - mx * s, y: Math.max(15, (ch - (My - my) * s) / 2 - my * s) })
    setScale(s)
  }, [layout, selectedSurface, pos])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { setTimeout(fitView, 50) }, [timeMode, surfaces.length])

  // ── Generate ──
  const handleGenerate = useCallback(async () => {
    setIsGenerating(true)
    try { await generateSurfaces(projectId, true); mutateSurfaces() } finally { setIsGenerating(false) }
  }, [projectId, mutateSurfaces])

  // ── SVG Connections ──
  const connections = useMemo(() => {
    const paths: JSX.Element[] = []
    if (viewMode !== 'outcomes') return paths

    const hasSelection = !!(selectedOutcome || selectedSurface)

    layout.visOc.forEach((oc, oi) => {
      const op = pos(oc.id)
      const color = getOcColor(oi)

      layout.visSf.forEach(sf => {
        if (!sf.linked_outcome_ids.includes(oc.id)) return
        const sp = pos(sf.id)

        // Connection: right-center of outcome → left-center of surface
        const ox = op.x + OC_W, oy = op.y + OC_H / 2
        const px = sp.x, py = sp.y + SF_H / 2
        let opacity = 0.14, sw = 1.5

        if (hasSelection) {
          const ocActive = selectedOutcome === oc.id
          const sfActive = selectedSurface === sf.id
          const inEvo = evoChain?.has(sf.id) && chainOcIds?.has(oc.id)

          if (ocActive || sfActive || inEvo) { opacity = 0.5; sw = 2.5 }
          else { opacity = 0.02; sw = 0.5 }
        }

        const dx = px - ox
        const cpx = Math.max(50, Math.abs(dx) * 0.4)
        const d = `M${ox},${oy} C${ox + cpx},${oy} ${px - cpx},${py} ${px},${py}`

        paths.push(<path key={`c-${oc.id}-${sf.id}`} d={d} fill="none" stroke={color.fill} strokeWidth={sw} opacity={opacity} />)
      })
    })

    // Evolution lines
    if (timeMode === 'evolution') {
      layout.visSf.forEach(sf => {
        if (!sf.evolves_from_id) return
        const from = layout.visSf.find(s => s.id === sf.evolves_from_id)
        if (!from) return
        const fp = pos(from.id), tp = pos(sf.id)

        const fx = fp.x + sfWidth(from), fy = fp.y + SF_H / 2
        const tx = tp.x, ty = tp.y + SF_H / 2
        const cpx = Math.max(40, (tx - fx) * 0.35)
        const d = `M${fx},${fy} C${fx + cpx},${fy} ${tx - cpx},${ty} ${tx},${ty}`

        const inChain = evoChain?.has(sf.id) && evoChain?.has(from.id)
        const hasSelection = !!(selectedOutcome || selectedSurface)
        const o = inChain ? 0.55 : hasSelection ? 0.04 : 0.22
        const w = inChain ? 2.5 : 1.5

        paths.push(<path key={`e-${sf.id}`} d={d} fill="none" stroke="#044159" strokeWidth={w} strokeDasharray="6 4" opacity={o} />)
      })
    }

    return paths
  }, [layout, viewMode, timeMode, selectedOutcome, selectedSurface, evoChain, chainOcIds, pos, outcomes])

  // ── Empty / loading states ──
  if (surfacesLoading && !surfaces.length) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex items-center gap-2 text-[13px] text-text-placeholder">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading convergence map...
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
            Generate surfaces from your outcomes, features, and workflows to see how everything converges.
          </p>
        </div>
        <button onClick={handleGenerate} disabled={isGenerating}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50">
          {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          {isGenerating ? 'Generating...' : 'Generate Solution Surfaces'}
        </button>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* ── Header ── */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-[#E5E5E5] bg-white flex-shrink-0">
        <div className="flex rounded-md overflow-hidden border border-[#E5E5E5]">
          {(['outcomes', 'actors'] as const).map(m => (
            <button key={m} onClick={() => { setViewMode(m); setSelectedOutcome(null); setSelectedSurface(null) }}
              className={`flex items-center gap-1.5 px-3 py-1 text-[11px] font-semibold transition-colors ${
                viewMode === m ? (m === 'outcomes' ? 'bg-[#E8F5E9] text-[#25785A]' : 'bg-[rgba(4,65,89,0.06)] text-[#044159]') : 'text-[#A0AEC0] hover:text-[#666]'
              }`}>
              {m === 'outcomes' ? <Target className="w-3 h-3" /> : <Users className="w-3 h-3" />}
              {m === 'outcomes' ? 'Outcomes' : 'Actors'}
            </button>
          ))}
        </div>
        <div className="w-px h-4 bg-[#E5E5E5]" />
        <div className="flex gap-3 text-[10px]">
          <span><b className="text-[#3FAF7A]">{layout.visOc.length}</b> <span className="text-[#A0AEC0] uppercase tracking-wide font-semibold">Outcomes</span></span>
          <span><b className="text-[#3FAF7A]">{layout.visSf.filter(s => s.horizon !== 'h3').length}</b> <span className="text-[#A0AEC0] uppercase tracking-wide font-semibold">Surfaces</span></span>
          <span><b className="text-[#3FAF7A]">{layout.visSf.filter(isXP).length}</b> <span className="text-[#A0AEC0] uppercase tracking-wide font-semibold">Cross-Persona</span></span>
        </div>
        <div className="flex-1" />
        <div className="flex rounded-md overflow-hidden border border-[#E5E5E5]">
          {(['now', 'evolution'] as const).map(m => (
            <button key={m} onClick={() => { setTimeMode(m); setSelectedOutcome(null); setSelectedSurface(null) }}
              className={`px-3 py-1 text-[11px] font-semibold transition-colors ${
                timeMode === m ? 'bg-[#E8F5E9] text-[#25785A]' : 'text-[#A0AEC0] hover:text-[#666]'
              }`}>
              {m === 'now' ? 'Now' : 'Evolution'}
            </button>
          ))}
        </div>
        <button onClick={fitView} className="px-2.5 py-1 text-[10px] font-semibold text-[#A0AEC0] border border-[#E5E5E5] rounded-md hover:text-[#666] transition-colors">Fit</button>
        <span className="text-[9px] text-[#A0AEC0] font-mono w-8 text-right">{Math.round(scale * 100)}%</span>
      </div>

      {/* ── Canvas + Drawer ── */}
      <div className="flex-1 flex overflow-hidden">
        <div ref={wrapRef} className="flex-1 overflow-hidden relative cursor-grab active:cursor-grabbing bg-[#FAFBFC]"
          onWheel={handleWheel} onMouseDown={handleCanvasMouseDown}>

          {/* Timeline (evo mode) */}
          {timeMode === 'evolution' && (
            <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-0 pointer-events-none">
              {[
                { color: '#3FAF7A', label: 'Now' },
                { color: '#044159', label: 'Next' },
                { color: '#C49A1A', label: 'Vision' },
              ].map((n, i, arr) => (
                <div key={n.label} className="flex items-center">
                  <div className="flex flex-col items-center gap-0.5">
                    <div className="w-2 h-2 rounded-full border-2" style={{ borderColor: n.color, background: n.color + '18' }} />
                    <span className="text-[7px] font-bold uppercase tracking-wider" style={{ color: n.color }}>{n.label}</span>
                  </div>
                  {i < arr.length - 1 && <div className="w-16 h-[1.5px] -mb-3" style={{ background: `linear-gradient(90deg,${n.color},${arr[i + 1].color})` }} />}
                </div>
              ))}
            </div>
          )}

          <div ref={canvasRef} className="absolute top-0 left-0 origin-top-left w-[4000px] h-[3000px]">
            {/* SVG */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-[1]">{connections}</svg>

            {/* Outcome nodes */}
            {viewMode === 'outcomes' && layout.visOc.map((oc, oi) => {
              const p = pos(oc.id)
              const c = getOcColor(oi)
              const dim = isOcDimmed(oc)
              const sel = selectedOutcome === oc.id
              const actor = oc.actors?.[0]?.persona_name || ''
              const hzCls = oc.horizon === 'h1' ? 'bg-[rgba(63,175,122,0.08)] text-[#2D6B4A]' : 'bg-[rgba(4,65,89,0.06)] text-[#044159]'
              const strDots = [20, 40, 60, 80, 100].map(t => (
                <div key={t} className="w-[3.5px] h-[3.5px] rounded-full" style={{ background: oc.strength_score >= t ? c.fill : 'rgba(0,0,0,.05)' }} />
              ))

              return (
                <div key={oc.id}
                  className={`absolute rounded-[9px] p-[9px_11px] z-[3] border-[1.5px] transition-opacity duration-200 ${
                    dim ? 'opacity-[0.06] pointer-events-none' : 'cursor-grab active:cursor-grabbing'
                  } ${sel ? 'shadow-[0_0_0_2px_#3FAF7A,0_4px_16px_rgba(63,175,122,0.10)]' : 'hover:shadow-[0_4px_16px_rgba(0,0,0,0.05)]'}`}
                  style={{ left: p.x, top: p.y, width: OC_W, background: c.bg, borderColor: dim ? 'transparent' : c.bd }}
                  onMouseDown={e => onCardMouseDown(e, oc.id)}
                  onClick={() => { if (!didDrag.current) setSelectedOutcome(sel ? null : oc.id) }}
                >
                  <div className="flex items-start gap-1.5 mb-1">
                    <div className="min-w-[20px] h-[20px] rounded-[5px] flex items-center justify-center text-[8px] font-extrabold text-white flex-shrink-0" style={{ background: c.fill }}>{oi + 1}</div>
                    <div>
                      <div className="text-[7px] font-bold uppercase tracking-[0.4px] mb-0.5" style={{ color: getPersonaColor(actor) }}>{actor}</div>
                      <div className="text-[10px] font-bold leading-[1.35]" style={{ color: c.fill }}>{oc.title}</div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className={`text-[7px] font-bold px-1 py-0.5 rounded ${hzCls}`}>{oc.horizon.toUpperCase()}</span>
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
              const p = pos(sf.id)
              const dim = isSfDimmed(sf)
              const sel = selectedSurface === sf.id
              const xp = isXP(sf)
              const isH2 = sf.horizon === 'h2', isH3 = sf.horizon === 'h3'
              const w = sfWidth(sf)

              const ribbons = sf.linked_outcome_ids.map(oid => {
                const oi = outcomes.findIndex(o => o.id === oid)
                return <div key={oid} className="w-[5px] h-[5px] rounded-sm" style={{ background: getOcColor(Math.max(0, oi)).fill }} />
              })
              const dots = sf.linked_outcome_ids.map(oid => {
                const oi = outcomes.findIndex(o => o.id === oid)
                return <div key={oid} className="w-[6px] h-[6px] rounded-full" style={{ background: getOcColor(Math.max(0, oi)).fill }} />
              })

              const borderLeft = !isH2 && !isH3
                ? (sf.linked_outcome_ids.length >= 3 ? '5px solid #3FAF7A' : sf.linked_outcome_ids.length >= 2 ? '4px solid rgba(63,175,122,0.35)' : '3px solid rgba(10,30,47,0.10)')
                : undefined

              return (
                <div key={sf.id}
                  className={`absolute bg-white rounded-[11px] z-[2] flex flex-col overflow-visible transition-opacity duration-200
                    ${dim ? 'opacity-[0.05] pointer-events-none' : 'cursor-grab active:cursor-grabbing'}
                    ${sel ? 'z-[20] shadow-[0_0_0_2px_#3FAF7A,0_8px_32px_rgba(0,0,0,0.08)] border-[#3FAF7A]' : 'shadow-[0_1px_4px_rgba(0,0,0,0.03)] hover:shadow-[0_6px_24px_rgba(0,0,0,0.06)]'}
                    ${isH2 ? 'border border-dashed border-[rgba(4,65,89,0.15)]' : isH3 ? 'border border-dashed border-[rgba(196,154,26,0.22)] bg-gradient-to-br from-[rgba(196,154,26,0.015)] to-white/85' : 'border-[1.5px] border-[rgba(10,30,47,0.06)]'}
                  `}
                  style={{ left: p.x, top: p.y, width: w, borderLeft }}
                  onMouseDown={e => onCardMouseDown(e, sf.id)}
                  onClick={() => { if (!didDrag.current) { setSelectedSurface(sel ? null : sf.id); setSelectedOutcome(null) } }}
                >
                  <div className={`h-[20px] flex items-center px-[7px] gap-[3px] border-b border-[rgba(0,0,0,0.03)] rounded-t-[11px] ${isH3 ? 'bg-[rgba(196,154,26,0.03)]' : 'bg-[rgba(0,0,0,0.012)]'}`}>
                    <div className="w-1 h-1 rounded-full bg-[rgba(220,80,80,0.20)]" />
                    <div className="w-1 h-1 rounded-full bg-[rgba(212,180,50,0.28)]" />
                    <div className="w-1 h-1 rounded-full bg-[rgba(63,175,122,0.25)]" />
                    <span className="flex-1 mx-1 text-[7px] font-medium text-[#A0AEC0] truncate">{sf.route}</span>
                    <div className="flex gap-[2px]">{ribbons}</div>
                  </div>
                  <div className="px-[10px] pt-[7px] pb-1">
                    <div className={`font-bold leading-[1.2] mb-0.5 ${isH3 ? 'text-[#C49A1A] text-[12px]' : w >= 300 ? 'text-[#0A1E2F] text-[14px]' : 'text-[#0A1E2F] text-[12px]'}`}>{sf.title}</div>
                    <div className="text-[8.5px] text-[#7B7B7B] leading-[1.4] line-clamp-2">{sf.description}</div>
                  </div>
                  <div className="flex gap-[3px] px-[10px] py-0.5 flex-wrap">{dots}</div>
                  {sf.convergence_insight && sf.linked_outcome_ids.length >= 2 && (
                    <div className="mx-2 mb-0.5 px-2 py-1 rounded-[6px] bg-gradient-to-br from-[rgba(63,175,122,0.025)] to-[rgba(4,65,89,0.015)] border border-[rgba(63,175,122,0.06)]">
                      <div className="flex items-center gap-1 text-[6.5px] font-bold uppercase tracking-[0.5px] text-[#3FAF7A]">
                        <span className="bg-[#3FAF7A] text-white px-[3px] rounded-sm text-[6.5px] font-extrabold">{sf.linked_outcome_ids.length}</span>
                        converge {xp && <span className="bg-[#044159] text-white px-1 rounded-sm text-[6px] font-bold">cross-persona</span>}
                      </div>
                    </div>
                  )}
                  <div className="px-[10px] py-1">
                    <span className="text-[7px] font-medium text-[#A0AEC0]">
                      {isH3 ? 'H3 · Vision' : isH2 ? `${sf.linked_outcome_ids.length} outcome${sf.linked_outcome_ids.length !== 1 ? 's' : ''} · H2` : `${sf.linked_outcome_ids.length} outcome${sf.linked_outcome_ids.length !== 1 ? 's' : ''}${xp ? ' · cross-persona' : ''}`}
                    </span>
                  </div>
                  {sf.is_stale && <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-[#C49A1A] border-2 border-white" title={sf.stale_reason || 'Upstream change detected'} />}
                </div>
              )
            })}
          </div>
        </div>

        <SurfaceDrawer projectId={projectId} surfaceId={selectedSurface} surfaces={surfaces} outcomes={outcomes} onClose={() => setSelectedSurface(null)} />
      </div>
    </div>
  )
}
