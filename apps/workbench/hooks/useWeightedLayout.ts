import { useMemo } from 'react'
import type { FlowLayoutPosition, FlowCardSize } from '@/types/workspace'

export interface LayoutItem {
  id: string
  weight: number
  column: number
  row: number
}

interface LayoutConfig {
  colGap?: number
  rowGap?: number
  paddingLeft?: number
  riverY?: number
}

const DEFAULTS: Required<LayoutConfig> = {
  colGap: 90,
  rowGap: 24,
  paddingLeft: 60,
  riverY: 220,
}

function cardDimensions(weight: number, isHero: boolean): { w: number; h: number } {
  if (isHero) return { w: 290, h: 210 }
  if (weight >= 60) return { w: 250, h: 190 }
  if (weight >= 45) return { w: 225, h: 175 }
  return { w: 200, h: 160 }
}

export function getSizeClass(weight: number, isHero: boolean): FlowCardSize {
  if (isHero) return 'size-hero'
  if (weight >= 60) return 'size-lg'
  if (weight >= 45) return 'size-md'
  return 'size-sm'
}

export function useWeightedLayout(items: LayoutItem[], config?: LayoutConfig) {
  return useMemo(() => {
    if (!items.length) {
      return { positions: new Map<string, FlowLayoutPosition>(), totalWidth: 0, totalHeight: 0, heroId: null }
    }

    const { colGap, rowGap, paddingLeft, riverY } = { ...DEFAULTS, ...config }

    // Find hero (highest weight)
    let heroIdx = 0
    let maxWeight = -1
    items.forEach((item, i) => {
      if (item.weight > maxWeight) {
        maxWeight = item.weight
        heroIdx = i
      }
    })
    const heroId = items[heroIdx].id

    // Compute card sizes
    const sizes = items.map((item, i) => cardDimensions(item.weight, i === heroIdx))

    // Group items by column
    const cols: Record<number, number[]> = {}
    items.forEach((item, i) => {
      if (!cols[item.column]) cols[item.column] = []
      cols[item.column].push(i)
    })

    const colKeys = Object.keys(cols).map(Number).sort((a, b) => a - b)

    // Compute column widths (widest card in each column)
    const colWidths: Record<number, number> = {}
    colKeys.forEach(c => {
      colWidths[c] = Math.max(...cols[c].map(i => sizes[i].w))
    })

    // Compute x offsets
    const colX: Record<number, number> = {}
    let x = paddingLeft
    colKeys.forEach(c => {
      colX[c] = x
      x += colWidths[c] + colGap
    })

    // Position cards within each column
    const positions = new Map<string, FlowLayoutPosition>()

    const TOP_PAD = 16

    colKeys.forEach(c => {
      const cardIndices = cols[c].sort((a, b) => items[a].row - items[b].row)

      if (cardIndices.length === 1) {
        const i = cardIndices[0]
        positions.set(items[i].id, {
          x: colX[c] + (colWidths[c] - sizes[i].w) / 2,
          y: Math.max(TOP_PAD, riverY - sizes[i].h / 2),
          w: sizes[i].w,
          h: sizes[i].h,
        })
      } else {
        const totalH = cardIndices.reduce((s, i) => s + sizes[i].h, 0) + rowGap * (cardIndices.length - 1)
        let y = Math.max(TOP_PAD, riverY - totalH / 2)
        cardIndices.forEach(i => {
          positions.set(items[i].id, {
            x: colX[c] + (colWidths[c] - sizes[i].w) / 2,
            y,
            w: sizes[i].w,
            h: sizes[i].h,
          })
          y += sizes[i].h + rowGap
        })
      }
    })

    // Compute total height needed (max bottom edge of any card + padding)
    let maxBottom = 0
    positions.forEach(pos => {
      maxBottom = Math.max(maxBottom, pos.y + pos.h)
    })
    const totalHeight = maxBottom + TOP_PAD

    return { positions, totalWidth: x + 40, totalHeight, heroId }
  }, [items, config])
}
