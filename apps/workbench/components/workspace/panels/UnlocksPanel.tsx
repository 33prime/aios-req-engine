'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Zap,
  Globe,
  Search,
  RefreshCw,
  ChevronRight,
  ArrowUpRight,
  X as XIcon,
  Sparkles,
  ExternalLink,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import {
  listUnlocks,
  generateUnlocks,
  updateUnlock,
  promoteUnlock,
  dismissUnlock,
} from '@/lib/api'
import type {
  UnlockSummary,
  UnlockTier,
  UnlockStatus,
  ImpactType,
  ProvenanceLink,
} from '@/types/workspace'

// ============================================================================
// Config
// ============================================================================

const TIER_CONFIG: Record<UnlockTier, { label: string; subtitle: string; order: number }> = {
  implement_now: {
    label: 'Implement Now',
    subtitle: 'Quick wins that ride the core build',
    order: 1,
  },
  after_feedback: {
    label: 'After Feedback',
    subtitle: 'Layer on once the solution is validated',
    order: 2,
  },
  if_this_works: {
    label: 'If This Works',
    subtitle: 'Strategic bets on platform success',
    order: 3,
  },
}

const IMPACT_LABELS: Record<ImpactType, string> = {
  operational_scale: 'Operational Scale',
  talent_leverage: 'Talent Leverage',
  risk_elimination: 'Risk Elimination',
  revenue_expansion: 'Revenue Expansion',
  data_intelligence: 'Data Intelligence',
  compliance: 'Compliance',
  speed_to_change: 'Speed to Change',
}

const RELATIONSHIP_ICONS: Record<string, string> = {
  enables: '\u2192',
  solves: '\u2713',
  serves: '\u25B6',
  validated_by: '\u2690',
}

// ============================================================================
// Main Panel
// ============================================================================

type UnlockTab = 'unlocks' | 'similar_companies' | 'research'

interface UnlocksPanelProps {
  projectId: string
}

export function UnlocksPanel({ projectId }: UnlocksPanelProps) {
  const [activeTab, setActiveTab] = useState<UnlockTab>('unlocks')

  const TABS = [
    { id: 'unlocks' as const, icon: Zap, label: 'Unlocks' },
    { id: 'similar_companies' as const, icon: Globe, label: 'Similar Companies' },
    { id: 'research' as const, icon: Search, label: 'Research' },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center px-6 py-3 border-b border-[#E5E5E5] bg-white shrink-0">
        <div className="flex gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                  isActive
                    ? 'bg-[#E8F5E9] text-[#25785A]'
                    : 'text-[#999999] hover:text-[#333333] hover:bg-[#F4F4F4]'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === 'unlocks' && <UnlocksTab projectId={projectId} />}
        {activeTab === 'similar_companies' && <SimilarCompaniesTab projectId={projectId} />}
        {activeTab === 'research' && <ResearchTab />}
      </div>
    </div>
  )
}

// ============================================================================
// Unlocks Tab
// ============================================================================

function UnlocksTab({ projectId }: { projectId: string }) {
  const [unlocks, setUnlocks] = useState<UnlockSummary[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isGenerating, setIsGenerating] = useState(false)

  const loadUnlocks = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await listUnlocks(projectId)
      setUnlocks(data)
    } catch (err) {
      console.error('Failed to load unlocks:', err)
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadUnlocks()
  }, [loadUnlocks])

  const handleGenerate = useCallback(async () => {
    try {
      setIsGenerating(true)
      await generateUnlocks(projectId)
      // Poll for results after a delay (generation is async)
      setTimeout(() => {
        loadUnlocks().finally(() => setIsGenerating(false))
      }, 3000)
      // Poll again after more time
      setTimeout(() => loadUnlocks(), 8000)
      setTimeout(() => loadUnlocks(), 15000)
    } catch (err) {
      console.error('Failed to generate unlocks:', err)
      setIsGenerating(false)
    }
  }, [projectId, loadUnlocks])

  const handleCurate = useCallback(async (unlockId: string) => {
    try {
      await updateUnlock(projectId, unlockId, { status: 'curated' })
      setUnlocks(prev => prev.map(u => u.id === unlockId ? { ...u, status: 'curated' as UnlockStatus } : u))
    } catch (err) {
      console.error('Failed to curate unlock:', err)
    }
  }, [projectId])

  const handlePromote = useCallback(async (unlockId: string) => {
    try {
      const result = await promoteUnlock(projectId, unlockId)
      const featureId = (result.feature?.id as string) || null
      setUnlocks(prev => prev.map(u => u.id === unlockId ? {
        ...u,
        status: 'promoted' as UnlockStatus,
        promoted_feature_id: featureId,
      } : u))
    } catch (err) {
      console.error('Failed to promote unlock:', err)
    }
  }, [projectId])

  const handleDismiss = useCallback(async (unlockId: string) => {
    try {
      await dismissUnlock(projectId, unlockId)
      setUnlocks(prev => prev.map(u => u.id === unlockId ? { ...u, status: 'dismissed' as UnlockStatus } : u))
    } catch (err) {
      console.error('Failed to dismiss unlock:', err)
    }
  }, [projectId])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
      </div>
    )
  }

  const activeUnlocks = unlocks.filter(u => u.status !== 'dismissed')

  if (activeUnlocks.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-[#E8F5E9] flex items-center justify-center">
          <Zap className="w-7 h-7 text-[#3FAF7A]" />
        </div>
        <h3 className="text-[16px] font-semibold text-[#333333] mb-2">
          Discover Strategic Unlocks
        </h3>
        <p className="text-[13px] text-[#666666] max-w-md mx-auto mb-6">
          Analyze your project to discover what becomes strategically possible
          when the system is built — not features, but business outcomes.
        </p>
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="inline-flex items-center gap-2 px-5 py-2.5 text-[13px] font-medium text-white bg-[#3FAF7A] hover:bg-[#25785A] rounded-xl transition-colors disabled:opacity-50"
        >
          {isGenerating ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Unlocks
            </>
          )}
        </button>
      </div>
    )
  }

  // Group by tier
  const tiers = (['implement_now', 'after_feedback', 'if_this_works'] as UnlockTier[])
  const grouped = tiers.map(tier => ({
    tier,
    config: TIER_CONFIG[tier],
    unlocks: activeUnlocks.filter(u => u.tier === tier),
  }))

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <h3 className="text-[15px] font-semibold text-[#333333]">
            Strategic Unlocks
          </h3>
          <span className="px-2 py-0.5 text-[11px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
            {activeUnlocks.length}
          </span>
        </div>
        <button
          onClick={handleGenerate}
          disabled={isGenerating}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#3FAF7A] hover:bg-[#E8F5E9] rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? 'animate-spin' : ''}`} />
          {isGenerating ? 'Analyzing...' : 'Regenerate'}
        </button>
      </div>

      {/* Tier sections */}
      <div className="space-y-8">
        {grouped.map(({ tier, config, unlocks: tierUnlocks }) => (
          tierUnlocks.length > 0 && (
            <div key={tier}>
              {/* Tier header */}
              <div className="mb-3">
                <h4 className="text-[13px] font-semibold text-[#333333]">
                  {config.label}
                </h4>
                <p className="text-[11px] text-[#999999]">{config.subtitle}</p>
              </div>

              {/* Unlock cards */}
              <div className="space-y-3">
                {tierUnlocks.map((unlock) => (
                  <UnlockCard
                    key={unlock.id}
                    unlock={unlock}
                    onCurate={() => handleCurate(unlock.id)}
                    onPromote={() => handlePromote(unlock.id)}
                    onDismiss={() => handleDismiss(unlock.id)}
                  />
                ))}
              </div>
            </div>
          )
        ))}
      </div>
    </div>
  )
}

// ============================================================================
// Unlock Card
// ============================================================================

function UnlockCard({
  unlock,
  onCurate,
  onPromote,
  onDismiss,
}: {
  unlock: UnlockSummary
  onCurate: () => void
  onPromote: () => void
  onDismiss: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const statusStyles: Record<UnlockStatus, string> = {
    generated: 'border-[#E5E5E5]',
    curated: 'border-[#3FAF7A]/40',
    promoted: 'border-[#3FAF7A] bg-[#F8FFF8]',
    dismissed: 'border-[#E5E5E5] opacity-50',
  }

  return (
    <div className={`bg-white rounded-xl border ${statusStyles[unlock.status]} p-4 transition-all`}>
      {/* Top row: badges + title */}
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          {/* Badges */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
              {unlock.unlock_kind === 'new_capability' ? 'New Capability' : 'Feature Upgrade'}
            </span>
            <span className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
              {IMPACT_LABELS[unlock.impact_type] || unlock.impact_type}
            </span>
            {unlock.status === 'promoted' && (
              <span className="px-2 py-0.5 text-[10px] font-medium bg-[#3FAF7A] text-white rounded-full">
                Promoted
              </span>
            )}
            {unlock.status === 'curated' && (
              <span className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full border border-[#3FAF7A]/30">
                Curated
              </span>
            )}
          </div>

          {/* Title */}
          <h5 className="text-[13px] font-semibold text-[#333333] leading-snug">
            {unlock.title}
          </h5>

          {/* Narrative */}
          <p className="text-[12px] text-[#666666] mt-1 leading-relaxed line-clamp-2">
            {unlock.narrative}
          </p>

          {/* Magnitude highlight */}
          {unlock.magnitude && (
            <p className="text-[12px] text-[#25785A] font-medium mt-1.5">
              {unlock.magnitude}
            </p>
          )}

          {/* Provenance chips */}
          {unlock.provenance.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {unlock.provenance.map((prov, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] bg-[#F4F4F4] text-[#666666] rounded-lg"
                  title={`${prov.relationship}: ${prov.entity_name}`}
                >
                  <span className="text-[#999999]">{RELATIONSHIP_ICONS[prov.relationship] || '\u2022'}</span>
                  {prov.entity_name}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 rounded-lg text-[#999999] hover:text-[#333333] hover:bg-[#F4F4F4] transition-colors shrink-0"
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="mt-3 pt-3 border-t border-[#E5E5E5] space-y-2">
          {unlock.why_now && (
            <div>
              <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">Why Now</span>
              <p className="text-[12px] text-[#666666] mt-0.5">{unlock.why_now}</p>
            </div>
          )}
          {unlock.non_obvious && (
            <div>
              <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">Non-Obvious Insight</span>
              <p className="text-[12px] text-[#666666] mt-0.5 italic">{unlock.non_obvious}</p>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      {unlock.status !== 'promoted' && unlock.status !== 'dismissed' && (
        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-[#E5E5E5]">
          {unlock.status === 'generated' && (
            <button
              onClick={onCurate}
              className="px-3 py-1 text-[11px] font-medium text-[#25785A] bg-[#E8F5E9] hover:bg-[#d0efd8] rounded-lg transition-colors"
            >
              Curate
            </button>
          )}
          <button
            onClick={onPromote}
            className="inline-flex items-center gap-1 px-3 py-1 text-[11px] font-medium text-white bg-[#3FAF7A] hover:bg-[#25785A] rounded-lg transition-colors"
          >
            <ArrowUpRight className="w-3 h-3" />
            Promote to Feature
          </button>
          <button
            onClick={onDismiss}
            className="px-3 py-1 text-[11px] font-medium text-[#999999] hover:text-[#666666] hover:bg-[#F4F4F4] rounded-lg transition-colors ml-auto"
          >
            Dismiss
          </button>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Similar Companies Tab
// ============================================================================

interface CompetitorRef {
  id: string
  name: string
  url?: string | null
  strengths?: string[]
  weaknesses?: string[]
  research_notes?: string | null
  reference_type: string
  category?: string | null
  key_differentiator?: string | null
}

function SimilarCompaniesTab({ projectId }: { projectId: string }) {
  const [competitors, setCompetitors] = useState<CompetitorRef[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${baseUrl}/v1/projects/${projectId}/competitors`)
      .then(r => r.json())
      .then(d => d?.competitor_references || [])
      .then(setCompetitors)
      .catch(() => setCompetitors([]))
      .finally(() => setIsLoading(false))
  }, [projectId])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-16">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
      </div>
    )
  }

  const competitorItems = competitors.filter(c => c.reference_type === 'competitor')
  const designRefs = competitors.filter(c => c.reference_type === 'design_inspiration')
  const featureRefs = competitors.filter(c => c.reference_type === 'feature_inspiration')

  if (competitors.length === 0) {
    return (
      <div className="text-center py-16">
        <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-[#F4F4F4] flex items-center justify-center">
          <Globe className="w-7 h-7 text-[#999999]" />
        </div>
        <h3 className="text-[16px] font-semibold text-[#333333] mb-2">No Similar Companies Yet</h3>
        <p className="text-[13px] text-[#666666] max-w-md mx-auto">
          Upload competitive research documents or discovery transcripts to automatically
          extract similar companies and market references.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {competitorItems.length > 0 && (
        <CompetitorGroup title="Competitors" items={competitorItems} />
      )}
      {designRefs.length > 0 && (
        <CompetitorGroup title="Design Inspiration" items={designRefs} />
      )}
      {featureRefs.length > 0 && (
        <CompetitorGroup title="Feature Inspiration" items={featureRefs} />
      )}
    </div>
  )
}

function CompetitorGroup({ title, items }: { title: string; items: CompetitorRef[] }) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <h4 className="text-[13px] font-semibold text-[#333333]">{title}</h4>
        <span className="px-2 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
          {items.length}
        </span>
      </div>
      <div className="space-y-2">
        {items.map((comp) => (
          <CompetitorCard key={comp.id} competitor={comp} />
        ))}
      </div>
    </div>
  )
}

function CompetitorCard({ competitor: c }: { competitor: CompetitorRef }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-xl border border-[#E5E5E5] p-4">
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h5 className="text-[13px] font-semibold text-[#333333]">{c.name}</h5>
            {c.category && (
              <span className="px-2 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
                {c.category}
              </span>
            )}
          </div>
          {c.key_differentiator && (
            <p className="text-[12px] text-[#666666] mt-1">{c.key_differentiator}</p>
          )}
          {c.url && (
            <a
              href={c.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-[#3FAF7A] hover:text-[#25785A] mt-1"
            >
              <ExternalLink className="w-3 h-3" />
              {c.url}
            </a>
          )}
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 rounded-lg text-[#999999] hover:text-[#333333] hover:bg-[#F4F4F4] transition-colors shrink-0"
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 pt-3 border-t border-[#E5E5E5] space-y-2">
          {c.strengths && c.strengths.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">Strengths</span>
              <ul className="mt-1 space-y-0.5">
                {c.strengths.map((s, i) => (
                  <li key={i} className="text-[12px] text-[#666666] flex items-start gap-1.5">
                    <span className="text-[#3FAF7A] mt-0.5">+</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {c.weaknesses && c.weaknesses.length > 0 && (
            <div>
              <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">Weaknesses</span>
              <ul className="mt-1 space-y-0.5">
                {c.weaknesses.map((w, i) => (
                  <li key={i} className="text-[12px] text-[#666666] flex items-start gap-1.5">
                    <span className="text-red-400 mt-0.5">-</span>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {c.research_notes && (
            <div>
              <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">Research Notes</span>
              <p className="text-[12px] text-[#666666] mt-0.5">{c.research_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Research Tab (Placeholder)
// ============================================================================

function ResearchTab() {
  return (
    <div className="text-center py-16">
      <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-[#F4F4F4] flex items-center justify-center">
        <Search className="w-7 h-7 text-[#999999]" />
      </div>
      <h3 className="text-[16px] font-semibold text-[#333333] mb-2">Unlock Research</h3>
      <p className="text-[13px] text-[#666666] max-w-md mx-auto">
        Targeted research to discover and validate strategic unlocks is coming soon.
        For now, generate unlocks from your existing project data.
      </p>
    </div>
  )
}
