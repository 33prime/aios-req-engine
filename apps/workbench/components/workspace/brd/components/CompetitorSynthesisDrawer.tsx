'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  X,
  Shield,
  Globe,
  Target,
  FileText,
  ChevronRight,
  Loader2,
  Sparkles,
  BarChart3,
} from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { synthesizeCompetitors } from '@/lib/api'
import type {
  CompetitorBRDSummary,
  CompetitorSynthesis,
  FeatureHeatmapRow,
  CompetitorThreat,
  FeatureBRDSummary,
  BusinessDriver,
  ROISummary,
} from '@/types/workspace'

type TabId = 'overview' | 'intelligence' | 'evidence'

interface CompetitorSynthesisDrawerProps {
  projectId: string
  competitors: CompetitorBRDSummary[]
  features?: FeatureBRDSummary[]
  painPoints?: BusinessDriver[]
  goals?: BusinessDriver[]
  roiSummary?: ROISummary[]
  onClose: () => void
  onOpenDetail: (competitor: CompetitorBRDSummary) => void
}

const TABS: { id: TabId; label: string; icon: typeof Shield }[] = [
  { id: 'overview', label: 'Overview', icon: BarChart3 },
  { id: 'intelligence', label: 'Intelligence', icon: Sparkles },
  { id: 'evidence', label: 'Evidence', icon: FileText },
]

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  strong: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  basic: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
  planned: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]' },
  missing: { bg: 'bg-white', text: 'text-[#999999]' },
}

const POSITION_LABELS: Record<string, string> = {
  market_leader: 'Market Leader',
  established_player: 'Established',
  emerging_challenger: 'Emerging',
  niche_player: 'Niche',
  declining: 'Declining',
}

const ANALYSIS_STATUS_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  completed: { label: 'Analyzed', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  analyzing: { label: 'Analyzing', bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
  failed: { label: 'Failed', bg: 'bg-[#F0F0F0]', text: 'text-[#999999]' },
  pending: { label: 'Pending', bg: 'bg-[#F0F0F0]', text: 'text-[#999999]' },
}

export function CompetitorSynthesisDrawer({
  projectId,
  competitors,
  features = [],
  painPoints = [],
  goals = [],
  roiSummary = [],
  onClose,
  onOpenDetail,
}: CompetitorSynthesisDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')

  const confirmedCount = useMemo(
    () =>
      competitors.filter(
        (c) =>
          c.confirmation_status === 'confirmed_consultant' ||
          c.confirmation_status === 'confirmed_client'
      ).length,
    [competitors]
  )

  const analyzedCount = useMemo(
    () => competitors.filter((c) => c.deep_analysis_status === 'completed').length,
    [competitors]
  )

  const hasAnalyzed = analyzedCount > 0

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[640px] max-w-[95vw] bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#E5E5E5] px-6 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              {/* Navy circle with Shield icon */}
              <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Shield className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">
                  Competitive Intelligence
                </p>
                <h2 className="text-[15px] font-semibold text-[#333333] leading-snug">
                  {competitors.length} competitor{competitors.length !== 1 ? 's' : ''} tracked
                </h2>
                <div className="flex items-center gap-2 mt-1.5">
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
                    {confirmedCount} confirmed
                  </span>
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                    {analyzedCount} analyzed
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-md text-[#999999] hover:text-[#666666] hover:bg-[#F0F0F0] transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-0 mt-4 -mb-4 border-b-0">
            {TABS.map((tab) => {
              const TabIcon = tab.icon
              const isActive = activeTab === tab.id
              const isDisabled = tab.id === 'intelligence' && !hasAnalyzed
              return (
                <button
                  key={tab.id}
                  onClick={() => !isDisabled && setActiveTab(tab.id)}
                  disabled={isDisabled}
                  className={`flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium border-b-2 transition-colors ${
                    isActive
                      ? 'border-[#3FAF7A] text-[#25785A]'
                      : isDisabled
                        ? 'border-transparent text-[#E5E5E5] cursor-not-allowed'
                        : 'border-transparent text-[#999999] hover:text-[#666666]'
                  }`}
                >
                  <TabIcon className="w-3.5 h-3.5" />
                  {tab.label}
                  {tab.id === 'overview' && (
                    <span className="ml-1 text-[10px] bg-[#F0F0F0] text-[#666666] px-1.5 py-0.5 rounded-full">
                      {competitors.length}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {activeTab === 'overview' && (
            <OverviewTab
              competitors={competitors}
              confirmedCount={confirmedCount}
              analyzedCount={analyzedCount}
              onOpenDetail={onOpenDetail}
            />
          )}
          {activeTab === 'intelligence' && (
            <IntelligenceTab
              projectId={projectId}
              features={features}
              painPoints={painPoints}
              goals={goals}
              roiSummary={roiSummary}
            />
          )}
          {activeTab === 'evidence' && (
            <EvidenceTab competitors={competitors} onOpenDetail={onOpenDetail} />
          )}
        </div>
      </div>
    </>
  )
}

// ============================================================================
// Overview Tab
// ============================================================================

function OverviewTab({
  competitors,
  confirmedCount,
  analyzedCount,
  onOpenDetail,
}: {
  competitors: CompetitorBRDSummary[]
  confirmedCount: number
  analyzedCount: number
  onOpenDetail: (competitor: CompetitorBRDSummary) => void
}) {
  // Pricing model distribution
  const pricingDistribution = useMemo(() => {
    const dist: Record<string, number> = {}
    competitors.forEach((c) => {
      if (c.pricing_model) {
        const model = c.pricing_model
        dist[model] = (dist[model] || 0) + 1
      }
    })
    return Object.entries(dist).sort((a, b) => b[1] - a[1])
  }, [competitors])

  return (
    <div className="space-y-6">
      {/* Summary stat grid */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard label="Total" value={competitors.length} icon={Globe} />
        <StatCard label="Confirmed" value={confirmedCount} icon={Shield} highlight />
        <StatCard label="Analyzed" value={analyzedCount} icon={Sparkles} />
      </div>

      {/* Competitor list */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Globe className="w-3.5 h-3.5" />
          Competitors
        </h4>
        <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
          {competitors.map((competitor, idx) => (
            <CompetitorRow
              key={competitor.id}
              competitor={competitor}
              isLast={idx === competitors.length - 1}
              onClick={() => onOpenDetail(competitor)}
            />
          ))}
          {competitors.length === 0 && (
            <div className="px-4 py-6 text-center">
              <p className="text-[13px] text-[#999999]">No competitors tracked yet.</p>
            </div>
          )}
        </div>
      </div>

      {/* Pricing model distribution */}
      {pricingDistribution.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5" />
            Pricing Models
          </h4>
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
            {pricingDistribution.map(([model, count]) => (
              <div
                key={model}
                className="flex items-center justify-between px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
              >
                <span className="text-[13px] text-[#333333]">{model}</span>
                <div className="flex items-center gap-2">
                  <div className="w-20 h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#3FAF7A] rounded-full transition-all"
                      style={{
                        width: `${(count / competitors.length) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="text-[11px] text-[#999999] w-6 text-right">{count}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({
  label,
  value,
  icon: Icon,
  highlight,
}: {
  label: string
  value: number
  icon: typeof Globe
  highlight?: boolean
}) {
  return (
    <div
      className={`border rounded-xl px-3 py-2.5 text-center ${
        highlight ? 'border-[#3FAF7A]/30 bg-[#E8F5E9]/30' : 'border-[#E5E5E5] bg-white'
      }`}
    >
      <Icon
        className={`w-4 h-4 mx-auto mb-1 ${highlight ? 'text-[#3FAF7A]' : 'text-[#999999]'}`}
      />
      <p
        className={`text-[18px] font-bold ${highlight ? 'text-[#25785A]' : 'text-[#333333]'}`}
      >
        {value}
      </p>
      <p className="text-[10px] text-[#999999] uppercase">{label}</p>
    </div>
  )
}

function CompetitorRow({
  competitor,
  isLast,
  onClick,
}: {
  competitor: CompetitorBRDSummary
  isLast: boolean
  onClick: () => void
}) {
  const posLabel = POSITION_LABELS[competitor.market_position || '']
  const analysisConfig =
    ANALYSIS_STATUS_CONFIG[competitor.deep_analysis_status || 'pending'] ||
    ANALYSIS_STATUS_CONFIG.pending

  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[#F4F4F4]/50 transition-colors group ${
        !isLast ? 'border-b border-[#F0F0F0]' : ''
      }`}
    >
      {/* Avatar */}
      <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center text-white text-[12px] font-medium flex-shrink-0">
        {competitor.name[0]?.toUpperCase() || '?'}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-medium text-[#333333] truncate">
            {competitor.name}
          </span>
          {competitor.category && (
            <span className="text-[10px] text-[#999999] bg-[#F0F0F0] px-1.5 py-0.5 rounded flex-shrink-0">
              {competitor.category}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          {posLabel && (
            <span className="text-[11px] text-[#666666]">{posLabel}</span>
          )}
          <span
            className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${analysisConfig.bg} ${analysisConfig.text}`}
          >
            {analysisConfig.label}
          </span>
        </div>
      </div>

      {/* Status + arrow */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <BRDStatusBadge status={competitor.confirmation_status} />
        <ChevronRight className="w-4 h-4 text-[#E5E5E5] group-hover:text-[#999999] transition-colors" />
      </div>
    </button>
  )
}

// ============================================================================
// Intelligence Tab
// ============================================================================

function IntelligenceTab({
  projectId,
  features,
  painPoints,
  goals,
  roiSummary,
}: {
  projectId: string
  features: FeatureBRDSummary[]
  painPoints: BusinessDriver[]
  goals: BusinessDriver[]
  roiSummary: ROISummary[]
}) {
  const [synthesis, setSynthesis] = useState<CompetitorSynthesis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    synthesizeCompetitors(projectId)
      .then((data) => {
        if (!cancelled) setSynthesis(data)
      })
      .catch((err) => {
        console.error('Failed to synthesize competitors:', err)
        if (!cancelled)
          setError(
            'Failed to generate synthesis. Make sure at least one competitor has been analyzed.'
          )
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [projectId])

  if (loading) {
    return (
      <div className="text-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-[#3FAF7A] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">Synthesizing competitor insights...</p>
        <p className="text-[11px] text-[#999999] mt-1">This may take a moment</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <Target className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666]">{error}</p>
      </div>
    )
  }

  if (!synthesis) {
    return (
      <div className="text-center py-12">
        <Sparkles className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666]">No synthesis data available.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Market Landscape Summary */}
      {synthesis.market_landscape && (
        <div className="bg-[#F4F4F4] border border-[#E5E5E5] rounded-xl px-4 py-3">
          <p className="text-[13px] text-[#333333] leading-relaxed">
            {synthesis.market_landscape}
          </p>
        </div>
      )}

      {/* Positioning Recommendation */}
      {synthesis.positioning_recommendation && (
        <div className="border border-[#3FAF7A]/30 rounded-xl overflow-hidden">
          <div className="px-4 py-3 bg-[#E8F5E9]/50 border-b border-[#3FAF7A]/20">
            <div className="flex items-center gap-1.5">
              <Target className="w-3.5 h-3.5 text-[#25785A]" />
              <span className="text-[11px] font-semibold text-[#25785A] uppercase tracking-wide">
                Positioning Recommendation
              </span>
            </div>
          </div>
          <div className="px-4 py-3">
            <p className="text-[13px] text-[#333333] leading-relaxed">
              {synthesis.positioning_recommendation}
            </p>
          </div>
        </div>
      )}

      {/* Common Themes */}
      {synthesis.common_themes.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            Common Themes
          </h4>
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
            {synthesis.common_themes.map((theme, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 px-4 py-2.5 border-b border-[#F0F0F0] last:border-0"
              >
                <span className="text-[#3FAF7A] mt-0.5 flex-shrink-0">•</span>
                <span className="text-[13px] text-[#333333] leading-relaxed">{theme}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Market Gaps */}
      {synthesis.market_gaps.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Target className="w-3.5 h-3.5" />
            Market Gaps
          </h4>
          <div className="space-y-2">
            {synthesis.market_gaps.map((gap, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 p-3 bg-[#E8F5E9]/50 rounded-xl border border-[#3FAF7A]/10"
              >
                <Target className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
                <p className="text-[12px] text-[#333333]">{gap}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Threat Summary */}
      {synthesis.threat_summary.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Shield className="w-3.5 h-3.5" />
            Threat Map
          </h4>
          <div className="space-y-2">
            {synthesis.threat_summary.map((threat, i) => (
              <ThreatCard key={i} threat={threat} />
            ))}
          </div>
        </div>
      )}

      {/* Feature Heatmap */}
      {synthesis.feature_heatmap.length > 0 && (
        <FeatureHeatmap rows={synthesis.feature_heatmap} />
      )}

      {/* Cross-Reference: Feature Gap Analysis */}
      {synthesis.feature_heatmap.length > 0 && features.length > 0 && (
        <FeatureGapAnalysis heatmap={synthesis.feature_heatmap} features={features} />
      )}

      {/* Cross-Reference: Pain Point Coverage */}
      {painPoints.length > 0 && (synthesis.market_gaps.length > 0 || synthesis.common_themes.length > 0) && (
        <PainPointCoverage
          painPoints={painPoints}
          marketGaps={synthesis.market_gaps}
          commonThemes={synthesis.common_themes}
        />
      )}

      {/* Cross-Reference: Goal Alignment */}
      {goals.length > 0 && (synthesis.market_gaps.length > 0 || synthesis.threat_summary.length > 0) && (
        <GoalAlignment
          goals={goals}
          marketGaps={synthesis.market_gaps}
          threats={synthesis.threat_summary}
        />
      )}

      {/* Cross-Reference: Financial Context */}
      {roiSummary.length > 0 && (
        <FinancialContext roiSummary={roiSummary} />
      )}
    </div>
  )
}

// ============================================================================
// Cross-Reference Sections
// ============================================================================

function FeatureGapAnalysis({
  heatmap,
  features,
}: {
  heatmap: FeatureHeatmapRow[]
  features: FeatureBRDSummary[]
}) {
  const analysis = useMemo(() => {
    const featureNames = new Set(features.map((f) => f.name.toLowerCase()))
    const heatmapAreas = new Set(heatmap.map((r) => r.feature_area.toLowerCase()))

    // Critical Gaps: competitor=strong in heatmap, but we have missing/planned
    const criticalGaps = heatmap.filter((row) => {
      const competitorStatuses = Object.values(row.competitors)
      const anyCompetitorStrong = competitorStatuses.some((s) => s === 'strong')
      return anyCompetitorStrong && (row.our_status === 'missing' || row.our_status === 'planned')
    })

    // Our Advantages: we are strong, competitors are basic/missing
    const ourAdvantages = heatmap.filter((row) => {
      if (row.our_status !== 'strong') return false
      const competitorStatuses = Object.values(row.competitors)
      return competitorStatuses.every((s) => s !== 'strong')
    })

    // Unique to Us: features we have that aren't in the heatmap at all
    const uniqueToUs = features.filter(
      (f) => !heatmapAreas.has(f.name.toLowerCase())
    ).slice(0, 5)

    return { criticalGaps, ourAdvantages, uniqueToUs }
  }, [heatmap, features])

  if (analysis.criticalGaps.length === 0 && analysis.ourAdvantages.length === 0 && analysis.uniqueToUs.length === 0) {
    return null
  }

  return (
    <div>
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <Target className="w-3.5 h-3.5" />
        Feature Gap Analysis
      </h4>
      <div className="space-y-3">
        {analysis.criticalGaps.length > 0 && (
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
            <div className="px-3 py-2 bg-[#F4F4F4] border-b border-[#E5E5E5]">
              <span className="text-[11px] font-medium text-[#333333]">
                Critical Gaps ({analysis.criticalGaps.length})
              </span>
              <span className="text-[10px] text-[#999999] ml-2">Competitors strong, we&apos;re not</span>
            </div>
            {analysis.criticalGaps.map((row, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-2 border-b border-[#F0F0F0] last:border-0">
                <span className="text-[12px] text-[#333333]">{row.feature_area}</span>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                  {row.our_status}
                </span>
              </div>
            ))}
          </div>
        )}

        {analysis.ourAdvantages.length > 0 && (
          <div className="border border-[#3FAF7A]/20 rounded-xl overflow-hidden">
            <div className="px-3 py-2 bg-[#E8F5E9]/30 border-b border-[#3FAF7A]/10">
              <span className="text-[11px] font-medium text-[#25785A]">
                Our Advantages ({analysis.ourAdvantages.length})
              </span>
            </div>
            {analysis.ourAdvantages.map((row, i) => (
              <div key={i} className="flex items-center justify-between px-3 py-2 border-b border-[#F0F0F0] last:border-0">
                <span className="text-[12px] text-[#333333]">{row.feature_area}</span>
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
                  strong
                </span>
              </div>
            ))}
          </div>
        )}

        {analysis.uniqueToUs.length > 0 && (
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
            <div className="px-3 py-2 bg-[#F4F4F4] border-b border-[#E5E5E5]">
              <span className="text-[11px] font-medium text-[#333333]">
                Unique to Us ({analysis.uniqueToUs.length})
              </span>
              <span className="text-[10px] text-[#999999] ml-2">Not in competitor heatmap</span>
            </div>
            {analysis.uniqueToUs.map((f) => (
              <div key={f.id} className="flex items-center justify-between px-3 py-2 border-b border-[#F0F0F0] last:border-0">
                <span className="text-[12px] text-[#333333]">{f.name}</span>
                {f.priority_group && (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                    {f.priority_group.replace(/_/g, ' ')}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function PainPointCoverage({
  painPoints,
  marketGaps,
  commonThemes,
}: {
  painPoints: BusinessDriver[]
  marketGaps: string[]
  commonThemes: string[]
}) {
  const coverage = useMemo(() => {
    // Simple keyword overlap between pain points and market gaps/themes
    const gapWords = marketGaps.join(' ').toLowerCase()
    const themeWords = commonThemes.join(' ').toLowerCase()

    return painPoints.slice(0, 8).map((pain) => {
      const words = pain.description.toLowerCase().split(/\s+/)
      const significantWords = words.filter((w) => w.length > 4)
      const gapOverlap = significantWords.some((w) => gapWords.includes(w))
      const themeOverlap = significantWords.some((w) => themeWords.includes(w))
      return {
        pain,
        alignsWithGap: gapOverlap,
        alignsWithTheme: themeOverlap,
      }
    })
  }, [painPoints, marketGaps, commonThemes])

  const gapAligned = coverage.filter((c) => c.alignsWithGap)
  if (gapAligned.length === 0) return null

  return (
    <div>
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <Shield className="w-3.5 h-3.5" />
        Pain Point Coverage
      </h4>
      <p className="text-[11px] text-[#666666] mb-2">
        Pain points that align with market gaps competitors miss — opportunity areas.
      </p>
      <div className="space-y-2">
        {gapAligned.map(({ pain }) => (
          <div key={pain.id} className="flex items-start gap-2.5 p-3 bg-[#E8F5E9]/30 rounded-xl border border-[#3FAF7A]/10">
            <Target className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="text-[12px] text-[#333333] line-clamp-2">{pain.description}</p>
              <div className="flex items-center gap-2 mt-1">
                {pain.severity && (
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                    {pain.severity}
                  </span>
                )}
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
                  market gap opportunity
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function GoalAlignment({
  goals,
  marketGaps,
  threats,
}: {
  goals: BusinessDriver[]
  marketGaps: string[]
  threats: CompetitorThreat[]
}) {
  const analysis = useMemo(() => {
    const gapText = marketGaps.join(' ').toLowerCase()
    const threatText = threats.map((t) => t.key_risk).join(' ').toLowerCase()

    return goals.slice(0, 6).map((goal) => {
      const words = goal.description.toLowerCase().split(/\s+/)
      const significantWords = words.filter((w) => w.length > 4)
      const supportedByGap = significantWords.some((w) => gapText.includes(w))
      const threatenedByCompetitor = significantWords.some((w) => threatText.includes(w))
      return { goal, supportedByGap, threatenedByCompetitor }
    }).filter((g) => g.supportedByGap || g.threatenedByCompetitor)
  }, [goals, marketGaps, threats])

  if (analysis.length === 0) return null

  return (
    <div>
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <Target className="w-3.5 h-3.5" />
        Goal Alignment
      </h4>
      <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
        {analysis.map(({ goal, supportedByGap, threatenedByCompetitor }) => (
          <div key={goal.id} className="flex items-center gap-3 px-3 py-2.5 border-b border-[#F0F0F0] last:border-0">
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
              supportedByGap ? 'bg-[#3FAF7A]' : 'bg-[#E5E5E5]'
            }`} />
            <span className="text-[12px] text-[#333333] flex-1 line-clamp-1">{goal.description}</span>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              {supportedByGap && (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
                  gap opportunity
                </span>
              )}
              {threatenedByCompetitor && (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                  competitive risk
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function FinancialContext({ roiSummary }: { roiSummary: ROISummary[] }) {
  const totalSaved = useMemo(() => {
    return roiSummary.reduce((sum, r) => sum + (r.cost_saved_per_year ?? 0), 0)
  }, [roiSummary])

  if (totalSaved <= 0) return null

  const formatted = totalSaved >= 1_000_000
    ? `$${(totalSaved / 1_000_000).toFixed(1)}M`
    : totalSaved >= 1_000
      ? `$${Math.round(totalSaved / 1_000)}K`
      : `$${totalSaved.toFixed(0)}`

  return (
    <div>
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <BarChart3 className="w-3.5 h-3.5" />
        Financial Context
      </h4>
      <div className="border border-[#E5E5E5] rounded-xl px-4 py-3 bg-[#F4F4F4]">
        <p className="text-[13px] text-[#333333]">
          Workflow optimizations identified: <span className="font-semibold text-[#25785A]">{formatted}/year</span> potential savings across {roiSummary.length} workflow{roiSummary.length !== 1 ? 's' : ''}
        </p>
      </div>
    </div>
  )
}

function ThreatCard({ threat }: { threat: CompetitorThreat }) {
  const threatLevelConfig: Record<string, { bg: string; text: string }> = {
    low: { bg: 'bg-[#F0F0F0]', text: 'text-[#999999]' },
    medium: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
    high: { bg: 'bg-[#F0F0F0]', text: 'text-[#333333]' },
    critical: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  }
  const config = threatLevelConfig[threat.threat_level] || threatLevelConfig.medium

  return (
    <div className="border border-[#E5E5E5] rounded-xl px-4 py-3">
      <div className="flex items-center gap-2 mb-1.5">
        <Shield className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
        <span className="text-[13px] font-medium text-[#333333]">
          {threat.competitor_name}
        </span>
        <span
          className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${config.bg} ${config.text}`}
        >
          {threat.threat_level}
        </span>
      </div>
      <p className="text-[12px] text-[#666666] ml-5">{threat.key_risk}</p>
    </div>
  )
}

function FeatureHeatmap({ rows }: { rows: FeatureHeatmapRow[] }) {
  const competitorNames = useMemo(() => {
    return Array.from(new Set(rows.flatMap((r) => Object.keys(r.competitors))))
  }, [rows])

  return (
    <div>
      <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <BarChart3 className="w-3.5 h-3.5" />
        Feature Heatmap
      </h4>
      <div className="border border-[#E5E5E5] rounded-xl overflow-hidden overflow-x-auto">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="bg-[#F4F4F4]">
              <th className="text-left px-3 py-2 font-medium text-[#666666] min-w-[120px]">
                Feature Area
              </th>
              <th className="text-center px-2 py-2 font-medium text-[#25785A] min-w-[60px]">
                Us
              </th>
              {competitorNames.map((name) => (
                <th
                  key={name}
                  className="text-center px-2 py-2 font-medium text-[#666666] min-w-[60px]"
                >
                  {name.length > 12 ? name.slice(0, 12) + '...' : name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} className="border-t border-[#E5E5E5]">
                <td className="px-3 py-2 font-medium text-[#333333]">
                  {row.feature_area}
                </td>
                <td className="px-2 py-2 text-center">
                  <HeatmapBadge status={row.our_status} />
                </td>
                {competitorNames.map((name) => (
                  <td key={name} className="px-2 py-2 text-center">
                    <HeatmapBadge status={row.competitors[name] || 'missing'} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function HeatmapBadge({ status }: { status: string }) {
  const colors = STATUS_COLORS[status] || STATUS_COLORS.missing
  return (
    <span
      className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${colors.bg} ${colors.text}`}
    >
      {status}
    </span>
  )
}

// ============================================================================
// Evidence Tab
// ============================================================================

function EvidenceTab({
  competitors,
  onOpenDetail,
}: {
  competitors: CompetitorBRDSummary[]
  onOpenDetail: (competitor: CompetitorBRDSummary) => void
}) {
  // Competitors with analysis data have evidence via their deep analysis
  const analyzedCompetitors = competitors.filter(
    (c) => c.deep_analysis_status === 'completed'
  )
  const unanalyzedCompetitors = competitors.filter(
    (c) => c.deep_analysis_status !== 'completed'
  )

  if (competitors.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No competitors tracked</p>
        <p className="text-[12px] text-[#999999]">
          Add competitors from signals or manually to begin tracking.
        </p>
      </div>
    )
  }

  if (analyzedCompetitors.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-8 h-8 text-[#E5E5E5] mx-auto mb-3" />
        <p className="text-[13px] text-[#666666] mb-1">No analysis evidence yet</p>
        <p className="text-[12px] text-[#999999]">
          Analyze competitors to gather evidence from their websites and public information.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Analyzed competitors grouped */}
      <div>
        <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
          <Sparkles className="w-3.5 h-3.5" />
          Analyzed ({analyzedCompetitors.length})
        </h4>
        <div className="space-y-2">
          {analyzedCompetitors.map((competitor) => (
            <button
              key={competitor.id}
              onClick={() => onOpenDetail(competitor)}
              className="w-full border border-[#E5E5E5] rounded-xl px-4 py-3 text-left hover:bg-[#F4F4F4]/50 transition-colors group"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-7 h-7 rounded-full bg-[#0A1E2F] flex items-center justify-center text-white text-[11px] font-medium flex-shrink-0">
                    {competitor.name[0]?.toUpperCase() || '?'}
                  </div>
                  <div className="min-w-0">
                    <span className="text-[13px] font-medium text-[#333333] truncate block">
                      {competitor.name}
                    </span>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      {(competitor.website || competitor.url) && (
                        <span className="text-[11px] text-[#999999] truncate">
                          {(competitor.website || competitor.url || '')
                            .replace(/^https?:\/\//, '')
                            .replace(/\/$/, '')}
                        </span>
                      )}
                      {competitor.deep_analysis_at && (
                        <span className="text-[10px] text-[#999999]">
                          · analyzed {formatRelativeTime(competitor.deep_analysis_at)}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#E8F5E9] text-[#25785A]">
                    View analysis
                  </span>
                  <ChevronRight className="w-4 h-4 text-[#E5E5E5] group-hover:text-[#999999] transition-colors" />
                </div>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Unanalyzed competitors */}
      {unanalyzedCompetitors.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1.5">
            <Globe className="w-3.5 h-3.5" />
            Not Yet Analyzed ({unanalyzedCompetitors.length})
          </h4>
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden bg-white">
            {unanalyzedCompetitors.map((competitor, idx) => (
              <button
                key={competitor.id}
                onClick={() => onOpenDetail(competitor)}
                className={`w-full flex items-center gap-2.5 px-4 py-2.5 text-left hover:bg-[#F4F4F4]/50 transition-colors group ${
                  idx < unanalyzedCompetitors.length - 1
                    ? 'border-b border-[#F0F0F0]'
                    : ''
                }`}
              >
                <div className="w-6 h-6 rounded-full bg-[#F0F0F0] flex items-center justify-center text-[#999999] text-[10px] font-medium flex-shrink-0">
                  {competitor.name[0]?.toUpperCase() || '?'}
                </div>
                <span className="text-[12px] text-[#666666] truncate flex-1">
                  {competitor.name}
                </span>
                <ChevronRight className="w-3.5 h-3.5 text-[#E5E5E5] group-hover:text-[#999999] transition-colors flex-shrink-0" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Helpers
// ============================================================================

function formatRelativeTime(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMin = Math.floor(diffMs / 60000)
    if (diffMin < 1) return 'just now'
    if (diffMin < 60) return `${diffMin}m ago`
    const diffHrs = Math.floor(diffMin / 60)
    if (diffHrs < 24) return `${diffHrs}h ago`
    const diffDays = Math.floor(diffHrs / 24)
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return ''
  }
}
