'use client'

import { useState } from 'react'
import { Globe, ChevronRight, Target, Shield, Sparkles } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import type { CompetitorBRDSummary, SectionScore } from '@/types/workspace'

interface CompetitorsSectionProps {
  competitors: CompetitorBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onOpenDetail: (competitor: CompetitorBRDSummary) => void
  onOpenSynthesis: () => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  sectionScore?: SectionScore | null
}

const POSITION_LABELS: Record<string, string> = {
  market_leader: 'Leader',
  established_player: 'Established',
  emerging_challenger: 'Emerging',
  niche_player: 'Niche',
  declining: 'Declining',
}

const ANALYSIS_STATUS_LABELS: Record<string, { label: string; color: string }> = {
  completed: { label: 'Analyzed', color: 'text-[#25785A] bg-[#E8F5E9]' },
  analyzing: { label: 'Analyzing...', color: 'text-[#666666] bg-[#F0F0F0]' },
  failed: { label: 'Failed', color: 'text-[#666666] bg-[#F0F0F0]' },
  pending: { label: 'Not analyzed', color: 'text-[#999999] bg-[#F0F0F0]' },
}

export function CompetitorsSection({
  competitors,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onOpenDetail,
  onOpenSynthesis,
  onStatusClick,
  sectionScore,
}: CompetitorsSectionProps) {
  const [showAll, setShowAll] = useState(false)
  const SHOW_MAX = 5

  if (competitors.length === 0) return null

  const confirmedCount = competitors.filter(
    (c) => c.confirmation_status === 'confirmed_consultant' || c.confirmation_status === 'confirmed_client'
  ).length

  const unconfirmedIds = competitors
    .filter((c) => c.confirmation_status !== 'confirmed_consultant' && c.confirmation_status !== 'confirmed_client')
    .map((c) => c.id)

  const analyzedCount = competitors.filter((c) => c.deep_analysis_status === 'completed').length

  const displayedCompetitors = showAll ? competitors : competitors.slice(0, SHOW_MAX)

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <SectionHeader
            title="Competitive Landscape"
            count={competitors.length}
            confirmedCount={confirmedCount}
            onConfirmAll={unconfirmedIds.length > 0 ? () => onConfirmAll('competitor_reference', unconfirmedIds) : undefined}
            sectionScore={sectionScore}
          />
        </div>
      </div>

      {/* Synthesis button if we have analyzed competitors */}
      {analyzedCount >= 2 && (
        <button
          onClick={onOpenSynthesis}
          className="mb-4 inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#25785A] bg-[#E8F5E9] rounded-lg hover:bg-[#d4edda] transition-colors"
        >
          <Globe className="w-3.5 h-3.5" />
          View Market Landscape ({analyzedCount} analyzed)
        </button>
      )}

      {/* Competitor cards */}
      <div className="space-y-2">
        {displayedCompetitors.map((comp) => {
          const posLabel = POSITION_LABELS[comp.market_position || ''] || comp.market_position || 'Unknown'
          const analysisInfo = ANALYSIS_STATUS_LABELS[comp.deep_analysis_status || 'pending']

          return (
            <button
              key={comp.id}
              onClick={() => onOpenDetail(comp)}
              className="w-full text-left p-3 border border-[#E5E5E5] rounded-xl hover:border-[#3FAF7A]/30 hover:shadow-sm transition-all bg-white group"
            >
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center text-white text-[11px] font-medium flex-shrink-0">
                  {comp.name[0]?.toUpperCase() || '?'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] font-medium text-[#333333] truncate">{comp.name}</span>
                    {comp.is_design_reference && (
                      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-medium bg-[#E8F5E9] text-[#25785A]">
                        design ref
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[11px] text-[#999999]">{posLabel}</span>
                    {comp.category && (
                      <>
                        <span className="text-[#E5E5E5]">·</span>
                        <span className="text-[11px] text-[#999999]">{comp.category}</span>
                      </>
                    )}
                    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${analysisInfo.color}`}>
                      {analysisInfo.label}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {comp.confirmation_status && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        onStatusClick?.('competitor_reference', comp.id, comp.name, comp.confirmation_status)
                      }}
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-[#F0F0F0] text-[#666666] hover:bg-[#E5E5E5] transition-colors"
                    >
                      {comp.confirmation_status.replace(/_/g, ' ')}
                    </button>
                  )}
                  <ChevronRight className="w-4 h-4 text-[#E5E5E5] group-hover:text-[#3FAF7A] transition-colors" />
                </div>
              </div>
              {comp.key_differentiator && (
                <p className="mt-1.5 ml-11 text-[11px] text-[#666666] line-clamp-1">
                  {comp.key_differentiator}
                </p>
              )}
            </button>
          )
        })}
      </div>

      {/* Show more/less */}
      {competitors.length > SHOW_MAX && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="mt-2 text-[12px] text-[#3FAF7A] hover:text-[#25785A] transition-colors"
        >
          {showAll ? 'Show less' : `Show ${competitors.length - SHOW_MAX} more`}
        </button>
      )}
    </div>
  )
}
