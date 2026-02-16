'use client'

import { ArrowLeft, Sparkles, Brain, Loader2 } from 'lucide-react'
import type { ClientDetail } from '@/types/workspace'
import type { ClientIntelligenceProfile } from '@/lib/api'
import { CompletenessRing } from '@/components/workspace/brd/components/CompletenessRing'

interface ClientHeaderProps {
  client: ClientDetail
  enriching: boolean
  analyzing: boolean
  intelligence: ClientIntelligenceProfile | null
  onBack: () => void
  onEnrich: () => void
  onAnalyze: () => void
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function completenessLabel(score: number): string {
  if (score >= 80) return 'Excellent'
  if (score >= 60) return 'Good'
  if (score >= 30) return 'Fair'
  return 'Poor'
}

export function ClientHeader({ client, enriching, analyzing, intelligence, onBack, onEnrich, onAnalyze }: ClientHeaderProps) {
  const initials = client.name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  const completeness = intelligence?.profile_completeness ?? client.profile_completeness ?? 0
  const hasIntelligence = !!intelligence?.last_analyzed_at

  return (
    <div className="mb-6">
      {/* Back button */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-[13px] text-[#999] hover:text-[#666] transition-colors mb-4"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Clients
      </button>

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          {client.logo_url ? (
            <img
              src={client.logo_url}
              alt={client.name}
              className="w-14 h-14 rounded-2xl object-cover"
            />
          ) : (
            <div className="w-14 h-14 rounded-2xl bg-[#F0F0F0] flex items-center justify-center">
              <span className="text-[18px] font-semibold text-[#666]">{initials}</span>
            </div>
          )}
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-[22px] font-bold text-[#333]">{client.name}</h1>
              {hasIntelligence && (
                <div className="flex items-center gap-1.5">
                  <CompletenessRing score={completeness} size="md" />
                  <span className="text-[11px] font-medium text-[#999]">{completenessLabel(completeness)}</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-2 mt-1">
              {client.industry && (
                <span className="px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                  {client.industry}
                </span>
              )}
              {client.stage && (
                <span className="px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                  {client.stage.charAt(0).toUpperCase() + client.stage.slice(1)}
                </span>
              )}
              {intelligence?.last_analyzed_at && (
                <span className="text-[11px] text-[#999]">
                  Analyzed {formatTimeAgo(intelligence.last_analyzed_at)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={onAnalyze}
            disabled={analyzing}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-[#3FAF7A] border border-[#3FAF7A] rounded-xl hover:bg-[#E8F5E9] transition-colors disabled:opacity-50"
          >
            {analyzing ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Brain className="w-3.5 h-3.5" />
            )}
            {analyzing ? 'Analyzing...' : 'Analyze'}
          </button>
          <button
            onClick={onEnrich}
            disabled={enriching}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
          >
            {enriching ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            {enriching ? 'Enriching...' : 'Enrich'}
          </button>
        </div>
      </div>

      {/* Stat pills */}
      <div className="flex items-center gap-3 mt-4">
        <div className="bg-[#F4F4F4] rounded-lg px-3 py-1.5 inline-flex items-center gap-1.5">
          <span className="text-[13px] font-semibold text-[#333]">{client.project_count}</span>
          <span className="text-[12px] text-[#999]">Projects</span>
        </div>
        <div className="bg-[#F4F4F4] rounded-lg px-3 py-1.5 inline-flex items-center gap-1.5">
          <span className="text-[13px] font-semibold text-[#333]">{client.stakeholder_count}</span>
          <span className="text-[12px] text-[#999]">People</span>
        </div>
        {hasIntelligence && (
          <div className="bg-[#F4F4F4] rounded-lg px-3 py-1.5 inline-flex items-center gap-1.5">
            <span className="text-[13px] font-semibold text-[#333]">{completeness}%</span>
            <span className="text-[12px] text-[#999]">Profile</span>
          </div>
        )}
      </div>
    </div>
  )
}
