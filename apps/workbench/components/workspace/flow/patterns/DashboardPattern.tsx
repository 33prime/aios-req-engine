'use client'

import type { PatternRendererProps } from './types'
import { KpiCards, ChartBars, AlertBox } from './shared'

export function DashboardPattern({ fields }: PatternRendererProps) {
  return (
    <>
      <KpiCards fields={fields} />
      <ChartBars />
      <AlertBox title="AI Insight" desc="System detected a pattern in your data" />
    </>
  )
}
