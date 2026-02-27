'use client'

import { Search, ExternalLink, Brain, Users, Workflow, HelpCircle, FileText } from 'lucide-react'
import type { GapClusterSummary } from '@/types/workspace'

interface GapClusterStripProps {
  clusters: GapClusterSummary[]
}

const KNOWLEDGE_ICONS: Record<string, typeof Brain> = {
  technical: Brain,
  stakeholder: Users,
  process: Workflow,
  requirement: FileText,
}

function FanOutDots({ score }: { score: number }) {
  const dots = Math.min(Math.round(score * 5), 5)
  return (
    <div className="flex items-center gap-0.5" title={`Fan-out: ${score.toFixed(2)}`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i < dots ? 'bg-[#F59E0B]' : 'bg-[#E5E5E5]'}`}
        />
      ))}
    </div>
  )
}

function GapClusterCard({ cluster }: { cluster: GapClusterSummary }) {
  const Icon = (cluster.knowledge_type && KNOWLEDGE_ICONS[cluster.knowledge_type]) || HelpCircle

  return (
    <div className="flex items-start gap-3 bg-white rounded-xl border border-border p-3.5 hover:shadow-sm transition-shadow">
      <div className="w-7 h-7 rounded-lg bg-[#FFF7ED] flex items-center justify-center shrink-0">
        <Icon className="w-3.5 h-3.5 text-[#F59E0B]" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[13px] font-medium text-text-body truncate">{cluster.theme}</p>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-[11px] text-[#666666]">
            {cluster.gap_count} gap{cluster.gap_count !== 1 ? 's' : ''}
          </span>
          <span className="text-[11px] text-text-placeholder capitalize">{cluster.knowledge_type}</span>
          {cluster.priority_score > 0 && <FanOutDots score={cluster.priority_score} />}
        </div>
      </div>
    </div>
  )
}

export function GapClusterStrip({ clusters }: GapClusterStripProps) {
  if (!clusters || clusters.length === 0) return null

  const top3 = clusters.slice(0, 3)

  return (
    <section className="mt-10">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-[#F59E0B]" />
          <h3 className="text-[13px] font-semibold text-text-body">Intelligence Gaps</h3>
          <span className="text-[11px] text-text-placeholder">
            {clusters.length} cluster{clusters.length !== 1 ? 's' : ''} detected
          </span>
        </div>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {top3.map((cluster) => (
          <GapClusterCard key={cluster.cluster_id} cluster={cluster} />
        ))}
      </div>
    </section>
  )
}
