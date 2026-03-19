import type { ComponentType } from 'react'
import type { PatternRendererProps } from './types'

import { DashboardPattern } from './DashboardPattern'
import { TablePattern } from './TablePattern'
import { WizardPattern } from './WizardPattern'
import { CardPattern } from './CardPattern'
import { FormPattern } from './FormPattern'
import { TimelinePattern } from './TimelinePattern'
import { KanbanPattern } from './KanbanPattern'
import { MapPattern } from './MapPattern'
import { ComparisonPattern } from './ComparisonPattern'
import { ReportPattern } from './ReportPattern'
import { ChatPattern } from './ChatPattern'
import { CalendarPattern } from './CalendarPattern'
import { GalleryPattern } from './GalleryPattern'
import { TreePattern } from './TreePattern'
import { MetricsPattern } from './MetricsPattern'
import { InboxPattern } from './InboxPattern'
import { SplitviewPattern } from './SplitviewPattern'
import { FallbackPattern } from './shared'

const PATTERN_REGISTRY: Record<string, ComponentType<PatternRendererProps>> = {
  dashboard: DashboardPattern,
  table: TablePattern,
  wizard: WizardPattern,
  card: CardPattern,
  form: FormPattern,
  timeline: TimelinePattern,
  kanban: KanbanPattern,
  map: MapPattern,
  comparison: ComparisonPattern,
  report: ReportPattern,
  chat: ChatPattern,
  calendar: CalendarPattern,
  gallery: GalleryPattern,
  tree: TreePattern,
  metrics: MetricsPattern,
  inbox: InboxPattern,
  splitview: SplitviewPattern,
}

/** Look up a pattern renderer by name. Returns FallbackPattern for unknown patterns. */
export function getPatternRenderer(pattern: string): ComponentType<PatternRendererProps> {
  return PATTERN_REGISTRY[pattern] || (FallbackPattern as unknown as ComponentType<PatternRendererProps>)
}

export type { PatternRendererProps } from './types'
