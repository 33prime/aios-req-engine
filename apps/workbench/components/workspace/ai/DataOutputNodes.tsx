'use client'

/**
 * DataOutputNodes — Small amber (data source) and green (output) nodes
 * for the Intelligence Workbench canvas edges.
 */

interface DataNodeProps {
  label: string
  x: number
  y: number
  variant: 'source' | 'output'
}

const VARIANTS = {
  source: {
    bg: 'rgba(212, 160, 23, 0.08)',
    border: 'rgba(212, 160, 23, 0.35)',
    text: '#8B6914',
    dot: '#D4A017',
  },
  output: {
    bg: 'rgba(63, 175, 122, 0.08)',
    border: 'rgba(63, 175, 122, 0.35)',
    text: '#1B6B3A',
    dot: '#3FAF7A',
  },
}

export function DataOutputNode({ label, x, y, variant }: DataNodeProps) {
  const v = VARIANTS[variant]

  return (
    <div
      className="absolute flex items-center gap-2 rounded-lg px-3 py-2"
      style={{
        left: x,
        top: y,
        background: v.bg,
        border: `1px dashed ${v.border}`,
        maxWidth: 160,
      }}
    >
      <span
        className="flex-shrink-0 h-2 w-2 rounded-full"
        style={{ background: v.dot }}
      />
      <span
        className="text-[11px] font-medium leading-tight truncate"
        style={{ color: v.text }}
      >
        {label}
      </span>
    </div>
  )
}

/** Compute unique data sources from all agents' dataNeeds */
export function collectDataSources(
  agents: Array<{ dataNeeds: Array<{ source: string }> }>
): string[] {
  const seen = new Set<string>()
  for (const a of agents) {
    for (const d of a.dataNeeds) {
      if (d.source) seen.add(d.source)
    }
  }
  return Array.from(seen).sort()
}

/** Compute unique outputs from all agents' produces */
export function collectOutputs(
  agents: Array<{ produces: string[] }>
): string[] {
  const seen = new Set<string>()
  for (const a of agents) {
    for (const p of a.produces) {
      if (p) seen.add(p)
    }
  }
  return Array.from(seen).sort()
}
