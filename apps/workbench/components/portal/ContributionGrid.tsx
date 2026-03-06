'use client'

import { Swords, Palette, ShieldAlert, FileText, Sparkles, BookOpen } from 'lucide-react'
import { ProgressRing } from '@/components/ui/ProgressRing'
import type { StationSlug, ProjectContextData, PortalDashboard } from '@/types/portal'

interface StationTile {
  slug: StationSlug
  label: string
  icon: React.ComponentType<{ className?: string }>
  getCount: (ctx: ProjectContextData | null, dash: PortalDashboard | null) => number
  getProgress: (ctx: ProjectContextData | null) => number
}

const STATIONS: StationTile[] = [
  {
    slug: 'competitors',
    label: 'Competitors',
    icon: Swords,
    getCount: (ctx) => ctx?.competitors?.length ?? 0,
    getProgress: (ctx) => ctx?.completion_scores?.competitors ?? 0,
  },
  {
    slug: 'design',
    label: 'Design',
    icon: Palette,
    getCount: (ctx) => ctx?.design_love?.length ?? 0,
    getProgress: (ctx) => ctx?.completion_scores?.design ?? 0,
  },
  {
    slug: 'constraints',
    label: 'Constraints',
    icon: ShieldAlert,
    getCount: (ctx) => (ctx?.tribal_knowledge ?? []).filter(t => t.startsWith('[constraint]')).length,
    getProgress: (ctx) => {
      const count = (ctx?.tribal_knowledge ?? []).filter(t => t.startsWith('[constraint]')).length
      return Math.min(count * 30, 100)
    },
  },
  {
    slug: 'documents',
    label: 'Documents',
    icon: FileText,
    getCount: (_ctx, dash) => {
      // Count from dashboard progress if available
      return 0 // File count will come from dashboard
    },
    getProgress: (ctx) => ctx?.completion_scores?.files ?? 0,
  },
  {
    slug: 'ai_wishlist',
    label: 'AI Wishlist',
    icon: Sparkles,
    getCount: (ctx) => (ctx?.tribal_knowledge ?? []).filter(t => t.startsWith('[ai_wishlist]')).length,
    getProgress: (ctx) => {
      const count = (ctx?.tribal_knowledge ?? []).filter(t => t.startsWith('[ai_wishlist]')).length
      return Math.min(count * 30, 100)
    },
  },
  {
    slug: 'tribal',
    label: 'Tribal Knowledge',
    icon: BookOpen,
    getCount: (ctx) => (ctx?.tribal_knowledge ?? []).filter(t => !t.startsWith('[constraint]') && !t.startsWith('[ai_wishlist]')).length,
    getProgress: (ctx) => ctx?.completion_scores?.tribal ?? 0,
  },
]

interface ContributionGridProps {
  projectContext: ProjectContextData | null
  dashboard: PortalDashboard | null
  onStationOpen: (slug: StationSlug) => void
}

export function ContributionGrid({ projectContext, dashboard, onStationOpen }: ContributionGridProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {STATIONS.map((station) => {
        const Icon = station.icon
        const count = station.getCount(projectContext, dashboard)
        const progress = station.getProgress(projectContext)

        return (
          <button
            key={station.slug}
            onClick={() => onStationOpen(station.slug)}
            className="bg-surface-card border border-border rounded-lg p-3 text-left hover:border-brand-primary hover:shadow-sm transition-all group"
          >
            <div className="flex items-start justify-between mb-2">
              <div className="w-8 h-8 rounded-lg bg-surface-subtle flex items-center justify-center group-hover:bg-brand-primary-light transition-colors">
                <Icon className="w-4 h-4 text-text-muted group-hover:text-brand-primary transition-colors" />
              </div>
              <ProgressRing value={progress} size={24} strokeWidth={2.5} />
            </div>
            <p className="text-xs font-medium text-text-primary">{station.label}</p>
            <p className="text-[10px] text-text-placeholder mt-0.5">
              {count > 0 ? `${count} item${count !== 1 ? 's' : ''}` : 'None yet'}
            </p>
          </button>
        )
      })}
    </div>
  )
}
