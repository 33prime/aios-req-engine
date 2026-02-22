'use client'

import { useState, useEffect } from 'react'
import { Globe, Target, Shield, Sparkles, ExternalLink, FileText, Swords, Loader2, ToggleLeft, ToggleRight } from 'lucide-react'
import { getCompetitorAnalysis, analyzeCompetitor, toggleDesignReference } from '@/lib/api'
import { DrawerShell, type DrawerTab } from '@/components/ui/DrawerShell'
import { ConfirmActions } from './ConfirmActions'
import { EvidenceBlock } from './EvidenceBlock'
import type { CompetitorBRDSummary, CompetitorDeepAnalysis } from '@/types/workspace'

interface CompetitorDetailDrawerProps {
  competitor: CompetitorBRDSummary
  projectId: string
  onClose: () => void
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onUpdate?: () => void
}

type TabId = 'overview' | 'analysis' | 'strategic' | 'evidence'

const POSITION_LABELS: Record<string, { label: string; bg: string; text: string }> = {
  market_leader: { label: 'Market Leader', bg: 'bg-[#F0F0F0]', text: 'text-[#333333]' },
  established_player: { label: 'Established', bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
  emerging_challenger: { label: 'Emerging', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  niche_player: { label: 'Niche', bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
  declining: { label: 'Declining', bg: 'bg-[#F0F0F0]', text: 'text-[#999999]' },
}

const THREAT_COLORS: Record<string, { bg: string; text: string }> = {
  low: { bg: 'bg-[#F0F0F0]', text: 'text-[#666666]' },
  medium: { bg: 'bg-[#F0F0F0]', text: 'text-[#333333]' },
  high: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  critical: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
}

const TABS: DrawerTab[] = [
  { id: 'overview', label: 'Overview', icon: Globe },
  { id: 'analysis', label: 'Analysis', icon: Target },
  { id: 'strategic', label: 'Strategic', icon: Swords },
  { id: 'evidence', label: 'Evidence', icon: FileText },
]

export function CompetitorDetailDrawer({
  competitor,
  projectId,
  onClose,
  onConfirm,
  onNeedsReview,
  onUpdate,
}: CompetitorDetailDrawerProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview')
  const [analysis, setAnalysis] = useState<CompetitorDeepAnalysis | null>(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisStatus, setAnalysisStatus] = useState(competitor.deep_analysis_status || 'pending')
  const [scrapedPages, setScrapedPages] = useState<{ url: string; title: string; scraped_at: string }[]>([])
  const [isDesignRef, setIsDesignRef] = useState(competitor.is_design_reference)
  const [analyzing, setAnalyzing] = useState(false)

  // Load analysis if completed
  useEffect(() => {
    if (competitor.deep_analysis_status === 'completed') {
      setAnalysisLoading(true)
      getCompetitorAnalysis(projectId, competitor.id)
        .then((data) => {
          if (data.deep_analysis) {
            setAnalysis(data.deep_analysis)
            setScrapedPages(data.scraped_pages || [])
          }
          setAnalysisStatus(data.status)
        })
        .catch((err) => console.error('Failed to load analysis:', err))
        .finally(() => setAnalysisLoading(false))
    }
  }, [projectId, competitor.id, competitor.deep_analysis_status])

  const handleAnalyze = async () => {
    setAnalyzing(true)
    setAnalysisStatus('analyzing')
    try {
      await analyzeCompetitor(projectId, competitor.id)
      // Poll for completion
      const poll = setInterval(async () => {
        try {
          const result = await getCompetitorAnalysis(projectId, competitor.id)
          if (result.status === 'completed' && result.deep_analysis) {
            setAnalysis(result.deep_analysis)
            setScrapedPages(result.scraped_pages || [])
            setAnalysisStatus('completed')
            setAnalyzing(false)
            clearInterval(poll)
            onUpdate?.()
          } else if (result.status === 'failed') {
            setAnalysisStatus('failed')
            setAnalyzing(false)
            clearInterval(poll)
          }
        } catch {
          // Still analyzing, keep polling
        }
      }, 3000)
      // Stop polling after 2 minutes
      setTimeout(() => { clearInterval(poll); setAnalyzing(false) }, 120000)
    } catch (err) {
      console.error('Failed to trigger analysis:', err)
      setAnalyzing(false)
      setAnalysisStatus('failed')
    }
  }

  const handleToggleDesignRef = async () => {
    const newVal = !isDesignRef
    setIsDesignRef(newVal)
    try {
      await toggleDesignReference(projectId, competitor.id, newVal)
      onUpdate?.()
    } catch (err) {
      console.error('Failed to toggle design reference:', err)
      setIsDesignRef(!newVal)
    }
  }

  const posConfig = POSITION_LABELS[competitor.market_position || ''] || POSITION_LABELS.niche_player

  return (
    <DrawerShell
      onClose={onClose}
      icon={Globe}
      entityLabel="Competitor"
      title={competitor.name}
      headerExtra={
        <>
          {(competitor.website || competitor.url) && (
            <a
              href={competitor.website || competitor.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[12px] text-[#3FAF7A] hover:underline flex items-center gap-1"
            >
              {(competitor.website || competitor.url || '').replace(/^https?:\/\//, '')}
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium ${posConfig.bg} ${posConfig.text}`}>
              {posConfig.label}
            </span>
            {competitor.confirmation_status && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#F0F0F0] text-[#666666]">
                {competitor.confirmation_status.replace(/_/g, ' ')}
              </span>
            )}
          </div>
        </>
      }
      headerActions={
        <ConfirmActions
          status={competitor.confirmation_status}
          onConfirm={() => onConfirm('competitor_reference', competitor.id)}
          onNeedsReview={() => onNeedsReview('competitor_reference', competitor.id)}
          size="md"
        />
      }
      tabs={TABS}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as TabId)}
    >
      {/* Design reference toggle + Analyze button */}
      <div className="flex items-center justify-between px-6 py-3 -mx-6 -mt-5 mb-5 border-b border-[#E5E5E5] bg-[#F4F4F4]">
        <button
          onClick={handleToggleDesignRef}
          className="flex items-center gap-2 text-[12px] text-[#666666] hover:text-[#333333] transition-colors"
        >
          {isDesignRef ? (
            <ToggleRight className="w-5 h-5 text-[#3FAF7A]" />
          ) : (
            <ToggleLeft className="w-5 h-5 text-[#999999]" />
          )}
          Design reference
        </button>

        {analysisStatus !== 'completed' && (
          competitor.confirmation_status === 'confirmed_consultant' || competitor.confirmation_status === 'confirmed_client' ? (
            <button
              onClick={handleAnalyze}
              disabled={analyzing}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-lg hover:bg-[#25785A] transition-colors disabled:opacity-50"
            >
              {analyzing ? (
                <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Analyzing...</>
              ) : (
                <><Sparkles className="w-3.5 h-3.5" /> Analyze</>
              )}
            </button>
          ) : (
            <span className="text-[11px] text-[#999999] italic">Confirm this competitor before running analysis</span>
          )
        )}
      </div>

      {activeTab === 'overview' && (
        <OverviewTab competitor={competitor} />
      )}

      {activeTab === 'analysis' && (
        <AnalysisTab
          analysis={analysis}
          loading={analysisLoading || analyzing}
          status={analysisStatus}
        />
      )}

      {activeTab === 'strategic' && (
        <StrategicTab
          analysis={analysis}
          loading={analysisLoading || analyzing}
          status={analysisStatus}
        />
      )}

      {activeTab === 'evidence' && (
        <CompetitorEvidenceTab scrapedPages={scrapedPages} evidence={competitor.evidence || []} />
      )}
    </DrawerShell>
  )
}

// ============================================================================
// Tab Components
// ============================================================================

function buildOverviewNarrative(c: CompetitorBRDSummary): string | null {
  const parts: string[] = []
  const pos = c.market_position?.replace(/_/g, ' ')

  // Sentence 1: who they are
  if (pos && c.category) {
    parts.push(`${c.name} is a${pos === 'established' || pos === 'emerging' ? 'n' : ''} ${pos} in the ${c.category} space.`)
  } else if (c.category) {
    parts.push(`${c.name} operates in the ${c.category} space.`)
  } else if (pos) {
    parts.push(`${c.name} is positioned as a${pos === 'established' || pos === 'emerging' ? 'n' : ''} ${pos} in the market.`)
  }

  // Sentence 2: differentiator
  if (c.key_differentiator) {
    parts.push(`Their key differentiator is ${c.key_differentiator.charAt(0).toLowerCase()}${c.key_differentiator.slice(1)}${c.key_differentiator.endsWith('.') ? '' : '.'}`)
  }

  // Sentence 3: target audience + pricing
  if (c.target_audience && c.pricing_model) {
    parts.push(`They target ${c.target_audience.toLowerCase()} with a ${c.pricing_model.toLowerCase()} pricing model.`)
  } else if (c.target_audience) {
    parts.push(`Their target audience is ${c.target_audience.toLowerCase()}.`)
  } else if (c.pricing_model) {
    parts.push(`They use a ${c.pricing_model.toLowerCase()} pricing model.`)
  }

  return parts.length > 0 ? parts.join(' ') : null
}

function OverviewTab({ competitor }: { competitor: CompetitorBRDSummary }) {
  const narrative = buildOverviewNarrative(competitor)

  const fields = [
    { label: 'Category', value: competitor.category },
    { label: 'Market Position', value: competitor.market_position?.replace(/_/g, ' ') },
    { label: 'Key Differentiator', value: competitor.key_differentiator },
    { label: 'Pricing Model', value: competitor.pricing_model },
    { label: 'Target Audience', value: competitor.target_audience },
  ].filter((f) => f.value)

  return (
    <div className="space-y-5">
      {narrative && (
        <p className="text-[13px] text-[#333333] leading-relaxed">
          {narrative}
        </p>
      )}
      {fields.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {fields.map((field) => (
            <div key={field.label} className="p-3 bg-[#F4F4F4] rounded-xl">
              <dt className="text-[11px] font-medium text-[#999999] uppercase tracking-wider">{field.label}</dt>
              <dd className="mt-1 text-[13px] text-[#333333]">{field.value}</dd>
            </div>
          ))}
        </div>
      )}
      {!narrative && fields.length === 0 && (
        <p className="text-[13px] text-[#999999] text-center py-8">
          No details available yet. Analyze this competitor to generate insights.
        </p>
      )}
    </div>
  )
}

function AnalysisTab({ analysis, loading, status }: {
  analysis: CompetitorDeepAnalysis | null
  loading: boolean
  status: string
}) {
  if (loading) {
    return (
      <div className="text-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-[#3FAF7A] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">
          {status === 'analyzing' ? 'Analyzing competitor...' : 'Loading analysis...'}
        </p>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="text-center py-12">
        <Target className="w-8 h-8 text-[#E5E5E5] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">
          {status === 'failed' ? 'Analysis failed. Try again.' : 'No analysis available yet. Click Analyze to start.'}
        </p>
      </div>
    )
  }

  const threatColor = THREAT_COLORS[analysis.threat_level] || THREAT_COLORS.medium

  return (
    <div className="space-y-6">
      {/* Positioning */}
      <div>
        <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Market Positioning</h4>
        <p className="text-[13px] text-[#666666] leading-relaxed">{analysis.positioning_summary}</p>
        <div className="mt-2 flex items-center gap-2">
          <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium ${threatColor.bg} ${threatColor.text}`}>
            <Shield className="w-3 h-3 mr-1" />
            Threat: {analysis.threat_level}
          </span>
        </div>
        <p className="mt-1.5 text-[12px] text-[#999999]">{analysis.threat_reasoning}</p>
      </div>

      {/* Feature Overlap */}
      {analysis.feature_overlap.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Feature Overlap</h4>
          <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
            <table className="w-full text-[12px]">
              <thead>
                <tr className="bg-[#F4F4F4]">
                  <th className="text-left px-3 py-2 font-medium text-[#666666]">Feature</th>
                  <th className="text-left px-3 py-2 font-medium text-[#666666]">Us</th>
                  <th className="text-left px-3 py-2 font-medium text-[#666666]">Them</th>
                  <th className="text-center px-3 py-2 font-medium text-[#666666]">Edge</th>
                </tr>
              </thead>
              <tbody>
                {analysis.feature_overlap.map((f, i) => (
                  <tr key={i} className="border-t border-[#E5E5E5]">
                    <td className="px-3 py-2 font-medium text-[#333333]">{f.feature_name}</td>
                    <td className="px-3 py-2 text-[#666666]">{f.our_approach || '—'}</td>
                    <td className="px-3 py-2 text-[#666666]">{f.their_approach || '—'}</td>
                    <td className="px-3 py-2 text-center">
                      <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        f.advantage === 'us' ? 'bg-[#E8F5E9] text-[#25785A]' :
                        f.advantage === 'them' ? 'bg-[#F0F0F0] text-[#666666]' :
                        'bg-[#F0F0F0] text-[#999999]'
                      }`}>
                        {f.advantage}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Unique to Them */}
      {analysis.unique_to_them.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Unique to Them</h4>
          <div className="space-y-2">
            {analysis.unique_to_them.map((f, i) => (
              <div key={i} className="flex items-start gap-2 p-2.5 bg-[#F4F4F4] rounded-lg">
                <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 mt-0.5 ${
                  f.strategic_relevance === 'high' ? 'bg-[#E8F5E9] text-[#25785A]' : 'bg-[#F0F0F0] text-[#999999]'
                }`}>
                  {f.strategic_relevance}
                </span>
                <div>
                  <p className="text-[12px] font-medium text-[#333333]">{f.feature_name}</p>
                  <p className="text-[11px] text-[#666666]">{f.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unique to Us */}
      {analysis.unique_to_us.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Unique to Us</h4>
          <div className="space-y-2">
            {analysis.unique_to_us.map((f, i) => (
              <div key={i} className="flex items-start gap-2 p-2.5 bg-[#E8F5E9]/50 rounded-lg">
                <span className={`inline-flex px-1.5 py-0.5 rounded text-[10px] font-medium flex-shrink-0 mt-0.5 ${
                  f.strategic_relevance === 'high' ? 'bg-[#E8F5E9] text-[#25785A]' : 'bg-[#F0F0F0] text-[#999999]'
                }`}>
                  {f.strategic_relevance}
                </span>
                <div>
                  <p className="text-[12px] font-medium text-[#333333]">{f.feature_name}</p>
                  <p className="text-[11px] text-[#666666]">{f.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Inferred Pains */}
      {analysis.inferred_pains.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Pains They Solve</h4>
          <ul className="space-y-1">
            {analysis.inferred_pains.map((p, i) => (
              <li key={i} className="text-[12px] text-[#666666] flex items-start gap-2">
                <span className="text-[#3FAF7A] mt-1">•</span>
                {p}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Benefits */}
      {analysis.inferred_benefits.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Benefits They Claim</h4>
          <ul className="space-y-1">
            {analysis.inferred_benefits.map((b, i) => (
              <li key={i} className="text-[12px] text-[#666666] flex items-start gap-2">
                <span className="text-[#3FAF7A] mt-1">•</span>
                {b}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

function StrategicTab({ analysis, loading, status }: {
  analysis: CompetitorDeepAnalysis | null
  loading: boolean
  status: string
}) {
  if (loading) {
    return (
      <div className="text-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-[#3FAF7A] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">Loading strategic insights...</p>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="text-center py-12">
        <Swords className="w-8 h-8 text-[#E5E5E5] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">Run analysis first to see strategic insights.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {analysis.differentiation_opportunities.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Differentiation Opportunities</h4>
          <div className="space-y-2">
            {analysis.differentiation_opportunities.map((d, i) => (
              <div key={i} className="flex items-start gap-2 p-3 bg-[#E8F5E9]/50 rounded-lg border border-[#3FAF7A]/10">
                <Sparkles className="w-3.5 h-3.5 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
                <p className="text-[12px] text-[#333333]">{d}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.gaps_to_address.length > 0 && (
        <div>
          <h4 className="text-[13px] font-semibold text-[#333333] mb-2">Gaps to Address</h4>
          <div className="space-y-2">
            {analysis.gaps_to_address.map((g, i) => (
              <div key={i} className="flex items-start gap-2 p-3 bg-[#F4F4F4] rounded-lg">
                <Target className="w-3.5 h-3.5 text-[#999999] flex-shrink-0 mt-0.5" />
                <p className="text-[12px] text-[#333333]">{g}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function CompetitorEvidenceTab({
  scrapedPages,
  evidence,
}: {
  scrapedPages: { url: string; title: string; scraped_at: string }[]
  evidence: import('@/types/workspace').BRDEvidence[]
}) {
  if (scrapedPages.length === 0 && evidence.length === 0) {
    return (
      <div className="text-center py-12">
        <FileText className="w-8 h-8 text-[#E5E5E5] mx-auto mb-2" />
        <p className="text-[13px] text-[#999999]">No evidence yet. Run analysis to gather evidence.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {evidence.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wider mb-2">
            Signal Evidence
          </h4>
          <EvidenceBlock evidence={evidence} maxItems={100} />
        </div>
      )}

      {scrapedPages.length > 0 && (
        <div>
          <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wider mb-2">
            Scraped Pages
          </h4>
          <div className="space-y-2">
            {scrapedPages.map((page, i) => (
              <div key={i} className="p-3 border border-[#E5E5E5] rounded-lg">
                <a
                  href={page.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[12px] font-medium text-[#3FAF7A] hover:underline flex items-center gap-1"
                >
                  {page.title}
                  <ExternalLink className="w-3 h-3" />
                </a>
                <p className="text-[11px] text-[#999999] mt-1">
                  Scraped {new Date(page.scraped_at).toLocaleDateString()}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
