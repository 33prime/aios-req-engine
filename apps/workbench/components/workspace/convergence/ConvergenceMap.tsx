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
const OC_W = 200, OC_H = 130, AC_W = 210, AC_H = 130
function sfWidth(sf: SolutionSurface) { return sf.linked_outcome_ids.length >= 3 ? 300 : sf.linked_outcome_ids.length >= 2 ? 260 : 220 }
const SF_H = 160

interface Actor { name: string; initials: string; color: string; outcomeIds: string[] }

// ══════════════════════════════════════════════════════════
// Layout
// ══════════════════════════════════════════════════════════

function computeLayout(surfaces: SolutionSurface[], outcomes: Outcome[], actors: Actor[], timeMode: TimeMode, viewMode: ViewMode) {
  const visOc = timeMode === 'now' ? outcomes.filter(o => o.horizon === 'h1') : outcomes
  const visSf = timeMode === 'now' ? surfaces.filter(s => s.horizon === 'h1') : [...surfaces]
  const visActors = actors.slice(0, 3)

  const ocPositions: Record<string, { x: number; y: number }> = {}
  const acPositions: Record<string, { x: number; y: number }> = {}

  // Vertically center left-side nodes relative to surfaces
  const totalSfHeight = Math.max(visSf.filter(s => s.horizon === 'h1').length, 1) * 180

  if (viewMode === 'outcomes') {
    const totalOcHeight = visOc.length * (OC_H + 25)
    const ocStartY = Math.max(20, (totalSfHeight - totalOcHeight) / 2 + 20)
    visOc.forEach((o, i) => { ocPositions[o.id] = { x: 30, y: ocStartY + i * (OC_H + 25) } })
  } else {
    const totalAcHeight = visActors.length * (AC_H + 25)
    const acStartY = Math.max(20, (totalSfHeight - totalAcHeight) / 2 + 20)
    visActors.forEach((a, i) => { acPositions[a.name] = { x: 30, y: acStartY + i * (AC_H + 25) } })
  }

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

  return { ocPositions, acPositions, sfPositions, visOc, visSf, visActors }
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

  // Extract unique actors from outcomes
  const actors: Actor[] = useMemo(() => {
    const map = new Map<string, { outcomeIds: Set<string> }>()
    outcomes.forEach(oc => {
      oc.actors?.forEach(a => {
        if (!map.has(a.persona_name)) map.set(a.persona_name, { outcomeIds: new Set() })
        map.get(a.persona_name)!.outcomeIds.add(oc.id)
      })
    })
    return [...map.entries()]
      .sort((a, b) => b[1].outcomeIds.size - a[1].outcomeIds.size) // most outcomes first
      .slice(0, 3)
      .map(([name, data]) => ({
        name,
        initials: name.split(' ').map(w => w[0]).join('').slice(0, 2),
        color: getPersonaColor(name),
        outcomeIds: [...data.outcomeIds],
      }))
  }, [outcomes])

  const layout = useMemo(
    () => computeLayout(surfaces, outcomes, actors, timeMode, viewMode),
    [surfaces, outcomes, actors, timeMode, viewMode],
  )

  // Get effective position (drag override or layout default)
  const pos = useCallback((id: string): { x: number; y: number } => {
    if (positions[id]) return positions[id]
    return layout.ocPositions[id] || layout.acPositions[id] || layout.sfPositions[id] || { x: 0, y: 0 }
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
  // Screen → canvas coordinate conversion: canvasXY = (screenXY - wrapOffset - pan) / scale
  const screenToCanvas = useCallback((clientX: number, clientY: number) => {
    const rect = wrapRef.current?.getBoundingClientRect()
    if (!rect) return { x: 0, y: 0 }
    return {
      x: (clientX - rect.left - pan.x) / scale,
      y: (clientY - rect.top - pan.y) / scale,
    }
  }, [pan, scale])

  const onCardMouseDown = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    const p = pos(id)
    const canvas = screenToCanvas(e.clientX, e.clientY)
    dragState.current = {
      id,
      offsetX: canvas.x - p.x,
      offsetY: canvas.y - p.y,
    }
    didDrag.current = false
  }, [pos, screenToCanvas])

  // ── Pan / Zoom ──
  useEffect(() => {
    if (canvasRef.current) {
      canvasRef.current.style.transform = `translate(${pan.x}px,${pan.y}px) scale(${scale})`
    }
  }, [pan, scale])

  // Wheel handler — must be non-passive to preventDefault
  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const handler = (e: WheelEvent) => {
      e.preventDefault()
      const d = e.deltaY > 0 ? -0.05 : 0.05
      setScale(prev => {
        const next = Math.max(0.25, Math.min(2, prev + d))
        const rect = el.getBoundingClientRect()
        const mx = e.clientX - rect.left, my = e.clientY - rect.top
        setPan(p => ({ x: mx - (mx - p.x) * (next / prev), y: my - (my - p.y) * (next / prev) }))
        return next
      })
    }
    el.addEventListener('wheel', handler, { passive: false })
    return () => el.removeEventListener('wheel', handler)
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
        const canvas = screenToCanvas(e.clientX, e.clientY)
        const newX = canvas.x - dragState.current.offsetX
        const newY = canvas.y - dragState.current.offsetY
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
  }, [screenToCanvas])

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
      ...(viewMode === 'outcomes' ? layout.visOc.map(o => ({ ...pos(o.id), w: OC_W, h: OC_H })) : layout.visActors.map(a => ({ ...pos(a.name), w: AC_W, h: AC_H }))),
      ...layout.visSf.map(s => ({ ...pos(s.id), w: sfWidth(s), h: SF_H })),
    ]
    if (!nodes.length) return
    const pad = 50
    let mx = Infinity, my = Infinity, Mx = -Infinity, My = -Infinity
    nodes.forEach(n => { mx = Math.min(mx, n.x); my = Math.min(my, n.y); Mx = Math.max(Mx, n.x + n.w); My = Math.max(My, n.y + n.h) })
    const w = Mx - mx + pad * 2, h = My - my + pad * 2
    const cw = wrapRef.current.clientWidth - (selectedSurface ? 430 : 0), ch = wrapRef.current.clientHeight
    if (cw <= 0 || ch <= 0) return // wrapper not sized yet
    const s = Math.max(0.15, Math.min(cw / w, ch / h, 0.95))
    setPan({ x: (cw - (Mx - mx) * s) / 2 - mx * s, y: Math.max(15, (ch - (My - my) * s) / 2 - my * s) })
    setScale(s)
  }, [layout, selectedSurface, pos])

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    const t1 = setTimeout(fitView, 100)
    const t2 = setTimeout(fitView, 300)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [timeMode, viewMode, surfaces.length])

  // ── Generate ──
  const handleGenerate = useCallback(async () => {
    setIsGenerating(true)
    try { await generateSurfaces(projectId, true); mutateSurfaces() } finally { setIsGenerating(false) }
  }, [projectId, mutateSurfaces])

  // ── SVG Connections ──
  const connections = useMemo(() => {
    const paths: JSX.Element[] = []
    const hasSelection = !!(selectedOutcome || selectedSurface)

    if (viewMode === 'outcomes') {
      layout.visOc.forEach((oc, oi) => {
        const op = pos(oc.id)
        const color = getOcColor(oi)

        layout.visSf.forEach(sf => {
          if (!sf.linked_outcome_ids.includes(oc.id)) return
          const sp = pos(sf.id)

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

          const cpx = Math.max(50, Math.abs(px - ox) * 0.4)
          const d = `M${ox},${oy} C${ox + cpx},${oy} ${px - cpx},${py} ${px},${py}`
          paths.push(<path key={`c-${oc.id}-${sf.id}`} d={d} fill="none" stroke={color.fill} strokeWidth={sw} opacity={opacity} />)
        })
      })
    } else {
      // Actor → surface connections
      layout.visActors.forEach(actor => {
        const ap = pos(actor.name)
        layout.visSf.forEach(sf => {
          if (!sf.linked_outcome_ids.some(oid => actor.outcomeIds.includes(oid))) return
          const sp = pos(sf.id)

          const ax = ap.x + AC_W, ay = ap.y + AC_H / 2
          const px = sp.x, py = sp.y + SF_H / 2
          let opacity = 0.14, sw = 1.5

          if (selectedSurface) {
            if (selectedSurface === sf.id) { opacity = 0.45; sw = 2.5 }
            else { opacity = 0.02; sw = 0.5 }
          }

          const cpx = Math.max(50, Math.abs(px - ax) * 0.4)
          const d = `M${ax},${ay} C${ax + cpx},${ay} ${px - cpx},${py} ${px},${py}`
          paths.push(<path key={`a-${actor.name}-${sf.id}`} d={d} fill="none" stroke={actor.color} strokeWidth={sw} opacity={opacity} />)
        })
      })
    }

    // Outcome evolution lines ("deepens") on left rail
    if (timeMode === 'evolution' && viewMode === 'outcomes') {
      const ocWithEvo = outcomes.filter(o => (o as Outcome & { evolvesFrom?: string }).evolvesFrom)
      // Draw vertical dashed lines between H1 and H2 outcomes that share actors
      const h1Ocs = layout.visOc.filter(o => o.horizon === 'h1')
      const h2Ocs = layout.visOc.filter(o => o.horizon === 'h2')
      h2Ocs.forEach(h2oc => {
        // Find H1 outcome with shared actor
        const h2Actors = new Set(h2oc.actors?.map(a => a.persona_name) || [])
        const parent = h1Ocs.find(h1oc => h1oc.actors?.some(a => h2Actors.has(a.persona_name)))
        if (!parent) return
        const fp = pos(parent.id), tp = pos(h2oc.id)
        const fx = fp.x + OC_W / 2, fy = fp.y + OC_H
        const tx = tp.x + OC_W / 2, ty = tp.y
        const midY = (fy + ty) / 2
        const d = `M${fx},${fy} C${fx},${midY} ${tx},${midY} ${tx},${ty}`
        const inChain = chainOcIds?.has(h2oc.id) && chainOcIds?.has(parent.id)
        const o = inChain ? 0.5 : hasSelection ? 0.04 : 0.2
        paths.push(<path key={`oc-evo-${h2oc.id}`} d={d} fill="none" stroke="#044159" strokeWidth={inChain ? 2 : 1.5} strokeDasharray="4 3" opacity={o} />)
        // Label
        const lx = (fx + tx) / 2 - 15, ly = midY
        paths.push(<text key={`oc-evo-label-${h2oc.id}`} x={lx} y={ly} textAnchor="middle" fontSize={7} fontWeight={600} fill="#044159" opacity={inChain ? 0.5 : hasSelection ? 0.04 : 0.2}>deepens</text>)
      })
    }

    // Surface evolution lines
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
        // "evolves" label on the line
        const lx = (fx + tx) / 2, ly = (fy + ty) / 2 - 8
        paths.push(<text key={`el-${sf.id}`} x={lx} y={ly} textAnchor="middle" fontSize={7} fontWeight={600} fill="#044159" opacity={inChain ? 0.5 : hasSelection ? 0.04 : 0.18}>evolves →</text>)
      })
    }

    return paths
  }, [layout, viewMode, timeMode, selectedOutcome, selectedSurface, evoChain, chainOcIds, pos, outcomes])

  // ── Empty / loading states ──
  const isLoading = (surfacesLoading && !surfaces.length) || (!outcomesData && surfaces.length > 0)
  if (isLoading) {
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
          onMouseDown={handleCanvasMouseDown}>

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
            {/* Horizon lane backgrounds (evo mode) */}
            {timeMode === 'evolution' && (
              <>
                <div className="absolute top-0 h-full pointer-events-none" style={{ left: 280, width: 650, background: 'rgba(63,175,122,0.012)', borderRight: '1px dashed rgba(63,175,122,0.08)' }}>
                  <div className="absolute top-3 text-[9px] font-bold uppercase tracking-[0.6px] text-[rgba(63,175,122,0.3)]" style={{ left: '50%', transform: 'translateX(-50%)' }}>H1 · Now</div>
                </div>
                <div className="absolute top-0 h-full pointer-events-none" style={{ left: 930, width: 310, background: 'rgba(4,65,89,0.012)', borderRight: '1px dashed rgba(4,65,89,0.06)' }}>
                  <div className="absolute top-3 text-[9px] font-bold uppercase tracking-[0.6px] text-[rgba(4,65,89,0.25)]" style={{ left: '50%', transform: 'translateX(-50%)' }}>H2 · Next</div>
                </div>
                <div className="absolute top-0 h-full pointer-events-none" style={{ left: 1240, width: 400, background: 'rgba(196,154,26,0.008)' }}>
                  <div className="absolute top-3 text-[9px] font-bold uppercase tracking-[0.6px] text-[rgba(196,154,26,0.25)]" style={{ left: '50%', transform: 'translateX(-50%)' }}>H3 · Vision</div>
                </div>
              </>
            )}

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

            {/* Actor nodes (left side, actors mode) */}
            {viewMode === 'actors' && layout.visActors.map(actor => {
              const p = pos(actor.name)
              const ocCount = actor.outcomeIds.filter(oid => layout.visOc.some(o => o.id === oid) || outcomes.some(o => o.id === oid)).length
              const sfCount = layout.visSf.filter(sf => sf.linked_outcome_ids.some(oid => actor.outcomeIds.includes(oid))).length
              const dim = selectedSurface ? !layout.visSf.find(s => s.id === selectedSurface)?.linked_outcome_ids.some(oid => actor.outcomeIds.includes(oid)) : false

              // Outcome dots for this actor
              const ocDots = actor.outcomeIds.map(oid => {
                const oi = outcomes.findIndex(o => o.id === oid)
                return <div key={oid} className="w-[7px] h-[7px] rounded-full" style={{ background: getOcColor(Math.max(0, oi)).fill, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }} />
              })
              // Timeline dots (evo mode)
              const hasH1 = actor.outcomeIds.some(oid => outcomes.find(o => o.id === oid)?.horizon === 'h1')
              const hasH2 = actor.outcomeIds.some(oid => outcomes.find(o => o.id === oid)?.horizon === 'h2')

              return (
                <div key={actor.name}
                  className={`absolute rounded-[11px] p-[11px_13px] z-[3] border-[1.5px] border-[rgba(10,30,47,0.06)] bg-white transition-opacity duration-200 ${
                    dim ? 'opacity-[0.06] pointer-events-none' : 'cursor-grab active:cursor-grabbing hover:shadow-[0_6px_20px_rgba(0,0,0,0.07)]'
                  }`}
                  style={{ left: p.x, top: p.y, width: AC_W, boxShadow: '0 2px 8px rgba(0,0,0,0.04)' }}
                  onMouseDown={e => onCardMouseDown(e, actor.name)}
                >
                  <div className="flex items-center gap-2.5 mb-1.5">
                    <div className="w-8 h-8 rounded-[9px] flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0" style={{ background: actor.color, boxShadow: '0 2px 6px rgba(0,0,0,0.12)' }}>
                      {actor.initials}
                    </div>
                    <div>
                      <div className="text-[11px] font-bold text-[#0A1E2F]">{actor.name}</div>
                    </div>
                  </div>
                  {/* Outcome dots */}
                  <div className="flex gap-[3px] mb-1.5">{ocDots}</div>
                  {/* Stats */}
                  <div className="flex gap-2 text-[8px] pt-1.5 border-t border-[rgba(0,0,0,0.04)]">
                    <span className="text-[#25785A] font-semibold">{ocCount} outcomes</span>
                    <span className="text-[#A0AEC0]">·</span>
                    <span className="text-[#25785A] font-semibold">{sfCount} surfaces</span>
                  </div>
                  {/* Timeline dots (evo mode) */}
                  {timeMode === 'evolution' && (
                    <div className="flex items-center gap-1 mt-1.5 pt-1.5 border-t border-[rgba(0,0,0,0.04)]">
                      <div className={`w-2 h-2 rounded-full border-2 border-[#3FAF7A] ${hasH1 ? 'bg-[#3FAF7A]' : ''}`} />
                      <div className="w-4 h-[1.5px] bg-[rgba(0,0,0,0.06)]" />
                      <div className={`w-2 h-2 rounded-full border-2 border-[#044159] ${hasH2 ? 'bg-[#044159]' : ''}`} />
                      <span className="text-[7px] font-semibold ml-1" style={{ color: hasH2 ? '#044159' : '#A0AEC0' }}>
                        {hasH1 && hasH2 ? 'Deepens H1→H2' : hasH2 ? 'Enters H2' : 'H1'}
                      </span>
                    </div>
                  )}
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
                  onClick={() => { if (!didDrag.current) { setSelectedSurface(sel ? null : sf.id); setSelectedOutcome(null); setTimeout(fitView, 300) } }}
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

        <SurfaceDrawer projectId={projectId} surfaceId={selectedSurface} surfaces={surfaces} outcomes={outcomes} onClose={() => { setSelectedSurface(null); setTimeout(fitView, 300) }} />
      </div>
    </div>
  )
}
