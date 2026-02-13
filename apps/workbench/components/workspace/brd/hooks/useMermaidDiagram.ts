'use client'

import { useRef, useEffect, useState } from 'react'
import type { WorkflowPair, WorkflowStepSummary } from '@/types/workspace'

/**
 * Generate a mermaid flowchart definition from a WorkflowPair.
 * Produces two subgraphs: Current State and Future State.
 */
function generateMermaidDef(pair: WorkflowPair): string {
  const lines: string[] = ['flowchart LR']

  const formatStep = (step: WorkflowStepSummary, prefix: string, idx: number): string => {
    const timeLabel = step.time_minutes != null ? ` (${step.time_minutes}m)` : ''
    const label = `${step.label}${timeLabel}`
    // Escape quotes in labels
    return `  ${prefix}${idx}["${label.replace(/"/g, '#quot;')}"]`
  }

  const addStepStyles = (steps: WorkflowStepSummary[], prefix: string, lines: string[]) => {
    steps.forEach((step, idx) => {
      if (step.automation_level === 'fully_automated') {
        lines.push(`  style ${prefix}${idx} fill:#E8F5E9,stroke:#3FAF7A,color:#25785A`)
      } else if (step.automation_level === 'semi_automated') {
        lines.push(`  style ${prefix}${idx} fill:#FFF8E1,stroke:#F59E0B,color:#92400E`)
      } else {
        lines.push(`  style ${prefix}${idx} fill:#F0F0F0,stroke:#E5E5E5,color:#666666`)
      }
    })
  }

  // Current State subgraph
  if (pair.current_steps.length > 0) {
    lines.push('  subgraph current["Current State"]')
    pair.current_steps.forEach((step, idx) => {
      lines.push(formatStep(step, 'C', idx))
    })
    // Connect steps sequentially
    for (let i = 0; i < pair.current_steps.length - 1; i++) {
      lines.push(`    C${i} --> C${i + 1}`)
    }
    lines.push('  end')
  }

  // Future State subgraph
  if (pair.future_steps.length > 0) {
    lines.push('  subgraph future["Future State"]')
    pair.future_steps.forEach((step, idx) => {
      lines.push(formatStep(step, 'F', idx))
    })
    for (let i = 0; i < pair.future_steps.length - 1; i++) {
      lines.push(`    F${i} --> F${i + 1}`)
    }
    lines.push('  end')
  }

  // Apply styles
  addStepStyles(pair.current_steps, 'C', lines)
  addStepStyles(pair.future_steps, 'F', lines)

  // Subgraph styles
  lines.push('  style current fill:transparent,stroke:#E5E5E5,stroke-width:1px')
  lines.push('  style future fill:transparent,stroke:#3FAF7A,stroke-width:1px')

  return lines.join('\n')
}

/**
 * Hook that lazy-loads mermaid, generates a flowchart from a WorkflowPair,
 * and renders SVG into a ref.
 */
export function useMermaidDiagram(pair: WorkflowPair | null, containerId: string) {
  const ref = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!ref.current || !pair) return
    if (pair.current_steps.length === 0 && pair.future_steps.length === 0) return

    let cancelled = false
    const def = generateMermaidDef(pair)

    import('mermaid').then(({ default: mermaid }) => {
      if (cancelled) return
      mermaid.initialize({
        startOnLoad: false,
        theme: 'base',
        themeVariables: {
          primaryColor: '#E8F5E9',
          primaryBorderColor: '#3FAF7A',
          primaryTextColor: '#333333',
          lineColor: '#E5E5E5',
          fontFamily: 'Inter, sans-serif',
          fontSize: '12px',
        },
      })

      mermaid
        .render(containerId, def)
        .then(({ svg }) => {
          if (!cancelled && ref.current) {
            ref.current.innerHTML = svg
          }
        })
        .catch((err) => {
          if (!cancelled) {
            console.error('Mermaid render error:', err)
            setError('Failed to render diagram')
          }
        })
    }).catch((err) => {
      if (!cancelled) {
        console.error('Failed to load mermaid:', err)
        setError('Failed to load diagram library')
      }
    })

    return () => {
      cancelled = true
    }
  }, [pair, containerId])

  return { ref, error }
}
