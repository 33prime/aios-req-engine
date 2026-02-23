'use client'

import { useState, useMemo } from 'react'
import { Building2, AlertTriangle, Target, Eye, BarChart3, Pencil, ChevronDown, ChevronRight, Users, Puzzle, Zap, FileText, Sparkles, Loader2, Check, X } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import { BusinessDriverDetailDrawer } from '../components/BusinessDriverDetailDrawer'
import { DriverContainer } from '../components/DriverContainer'
import { DriverItemRow } from '../components/DriverItemRow'
import { enhanceVision } from '@/lib/api'
import type { BRDWorkspaceData, BusinessDriver, VisionAlignment, SectionScore, StakeholderBRDSummary } from '@/types/workspace'

interface BusinessContextSectionProps {
  data: BRDWorkspaceData['business_context']
  projectId: string
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onUpdateVision: (vision: string) => void
  onUpdateBackground: (background: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  sectionScore?: SectionScore | null
  onOpenVisionDetail?: () => void
  onOpenBackgroundDetail?: () => void
  stakeholders?: StakeholderBRDSummary[]
}

const SHOW_MAX_DRIVERS = 6
const SHOW_MAX_METRICS = 8

type SortKey = 'relevance' | 'linked' | 'confirmed' | 'newest'
type FilterKey = 'all' | 'linked' | 'orphaned'

// ============================================================================
// Vision Alignment Dot (used by KPI DriverCards)
// ============================================================================

function VisionDot({ alignment }: { alignment?: VisionAlignment | null }) {
  if (!alignment) return null
  const colors: Record<string, string> = {
    high: 'bg-[#3FAF7A]',
    medium: 'bg-[#4CC08C]',
    low: 'bg-[#E5E5E5]',
    unrelated: 'bg-[#E5E5E5]',
  }
  const labels: Record<string, string> = {
    high: 'High vision alignment',
    medium: 'Medium vision alignment',
    low: 'Low vision alignment',
    unrelated: 'Unrelated to vision',
  }
  return (
    <span
      className={`w-2 h-2 rounded-full shrink-0 ${colors[alignment] || 'bg-[#E5E5E5]'}`}
      title={labels[alignment] || ''}
    />
  )
}

// ============================================================================
// Link Summary Line (used by KPI DriverCards)
// ============================================================================

function LinkSummary({ driver }: { driver: BusinessDriver }) {
  const evidenceCount = driver.evidence?.length ?? 0
  const personaCount = driver.linked_persona_count ?? 0
  const featureCount = driver.linked_feature_count ?? 0
  const workflowCount = driver.linked_workflow_count ?? 0
  const totalLinks = personaCount + featureCount + workflowCount

  if (evidenceCount === 0 && totalLinks === 0) {
    return (
      <span className="text-[11px] text-[#999999] bg-[#F0F0F0] px-2 py-0.5 rounded-full">
        No evidence yet
      </span>
    )
  }

  return (
    <div className="flex items-center gap-3 text-[11px] text-[#666666]">
      {evidenceCount > 0 && (
        <span className="flex items-center gap-1 text-[#25785A]">
          <FileText className="w-3 h-3" />
          {evidenceCount} source{evidenceCount !== 1 ? 's' : ''}
        </span>
      )}
      {driver.associated_persona_names && driver.associated_persona_names.length > 0 && (
        <span className="flex items-center gap-1">
          <Users className="w-3 h-3 text-[#999999]" />
          {driver.associated_persona_names.slice(0, 2).join(', ')}
          {driver.associated_persona_names.length > 2 && ` +${driver.associated_persona_names.length - 2}`}
        </span>
      )}
      {featureCount > 0 && (
        <span className="flex items-center gap-1">
          <Puzzle className="w-3 h-3 text-[#999999]" />
          {featureCount} feature{featureCount !== 1 ? 's' : ''}
        </span>
      )}
      {workflowCount > 0 && (
        <span className="flex items-center gap-1">
          <Zap className="w-3 h-3 text-[#999999]" />
          {workflowCount} workflow{workflowCount !== 1 ? 's' : ''}
        </span>
      )}
    </div>
  )
}

// ============================================================================
// Metric Line (used by KPI DriverCards)
// ============================================================================

function MetricLine({ driver }: { driver: BusinessDriver }) {
  const parts: string[] = []

  if (driver.driver_type === 'kpi') {
    if (driver.baseline_value && driver.target_value) {
      parts.push(`${driver.baseline_value} → ${driver.target_value}`)
    } else if (driver.target_value) {
      parts.push(`Target: ${driver.target_value}`)
    }
    if (driver.monetary_value_high) {
      const val = driver.monetary_value_high
      const formatted = val >= 1_000_000 ? `$${(val / 1_000_000).toFixed(1)}M` : val >= 1_000 ? `$${Math.round(val / 1_000)}K` : `$${val}`
      parts.push(`~${formatted}/yr impact`)
    }
  }

  const firstEvidence = driver.evidence?.[0]

  if (parts.length === 0 && !firstEvidence) return null

  return (
    <div className="space-y-1">
      {parts.length > 0 && (
        <div className="text-[11px] text-[#999999]">{parts.join('  ·  ')}</div>
      )}
      {firstEvidence && (
        <div className="text-[11px] text-[#666666] italic line-clamp-1">
          &ldquo;{firstEvidence.excerpt}&rdquo;
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Unified Driver Card (still used by KPIs / Success Metrics)
// ============================================================================

function DriverCard({
  driver,
  icon: Icon,
  iconColor,
  onConfirm,
  onNeedsReview,
  onStatusClick,
  onDetailClick,
}: {
  driver: BusinessDriver
  icon: typeof AlertTriangle
  iconColor: string
  onConfirm: () => void
  onNeedsReview: () => void
  onStatusClick?: () => void
  onDetailClick: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [hasBeenExpanded, setHasBeenExpanded] = useState(false)

  return (
    <div className={`bg-white rounded-2xl shadow-md border overflow-hidden ${
      driver.is_stale ? 'border-orange-200' : 'border-[#E5E5E5]'
    }`}>
      <button
        onClick={() => { const next = !expanded; setExpanded(next); if (next && !hasBeenExpanded) setHasBeenExpanded(true) }}
        className="w-full px-5 py-3.5 text-left hover:bg-gray-50/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <ChevronRight
            className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
          />
          <Icon className={`w-4 h-4 shrink-0 ${iconColor}`} />
          <span className="text-[14px] font-semibold text-[#333333] truncate flex-1">{driver.description}</span>
          <VisionDot alignment={driver.vision_alignment} />
          <span onClick={(e) => e.stopPropagation()}>
            <BRDStatusBadge status={driver.confirmation_status} onClick={onStatusClick} />
          </span>
        </div>
        <div className="ml-[52px] mt-1.5">
          <LinkSummary driver={driver} />
        </div>
        <div className="ml-[52px] mt-1">
          <MetricLine driver={driver} />
        </div>
      </button>

      {hasBeenExpanded && (
        <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[800px] opacity-100' : 'max-h-0 opacity-0'}`}>
          <div className="px-5 pb-4 pt-2 border-t border-[#E5E5E5] space-y-3">
            {driver.evidence && driver.evidence.length > 0 && (
              <div className="space-y-2">
                <span className="text-[11px] font-semibold text-[#999999] uppercase tracking-wider">Evidence</span>
                {driver.evidence.slice(0, 3).map((ev, i) => (
                  <div key={i} className="flex items-start gap-2 pl-2 border-l-2 border-[#3FAF7A]/30">
                    <div className="flex-1 min-w-0">
                      <p className="text-[12px] text-[#333333] italic leading-relaxed">&ldquo;{ev.excerpt}&rdquo;</p>
                      <p className="text-[10px] text-[#999999] mt-0.5">{ev.rationale}</p>
                    </div>
                    <span className="text-[10px] text-[#999999] bg-[#F0F0F0] px-1.5 py-0.5 rounded shrink-0">
                      {ev.source_type}
                    </span>
                  </div>
                ))}
                {driver.evidence.length > 3 && (
                  <button onClick={onDetailClick} className="text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors pl-2">
                    +{driver.evidence.length - 3} more source{driver.evidence.length - 3 !== 1 ? 's' : ''} →
                  </button>
                )}
              </div>
            )}
            <div className="flex items-center justify-between pt-1">
              <ConfirmActions status={driver.confirmation_status} onConfirm={onConfirm} onNeedsReview={onNeedsReview} />
              <button
                onClick={onDetailClick}
                className="text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
              >
                View details →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// Sort / Filter Bar (still used by KPIs)
// ============================================================================

function SortFilterBar({
  sortKey,
  filterKey,
  onSortChange,
  onFilterChange,
}: {
  sortKey: SortKey
  filterKey: FilterKey
  onSortChange: (key: SortKey) => void
  onFilterChange: (key: FilterKey) => void
}) {
  const sortOptions: { key: SortKey; label: string }[] = [
    { key: 'relevance', label: 'Relevance' },
    { key: 'linked', label: 'Most Linked' },
    { key: 'confirmed', label: 'Confirmed' },
    { key: 'newest', label: 'Newest' },
  ]

  const filterOptions: { key: FilterKey; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'linked', label: 'With Evidence' },
    { key: 'orphaned', label: 'No Evidence' },
  ]

  return (
    <div className="flex items-center gap-4 mb-3">
      <div className="flex items-center gap-1.5">
        <span className="text-[11px] text-[#999999]">Sort:</span>
        {sortOptions.map((opt) => (
          <button
            key={opt.key}
            onClick={() => onSortChange(opt.key)}
            className={`px-2 py-0.5 text-[11px] rounded-md transition-colors ${
              sortKey === opt.key
                ? 'bg-[#E8F5E9] text-[#25785A] font-medium'
                : 'text-[#999999] hover:text-[#666666] hover:bg-[#F0F0F0]'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-1.5">
        <span className="text-[11px] text-[#999999]">Filter:</span>
        {filterOptions.map((opt) => (
          <button
            key={opt.key}
            onClick={() => onFilterChange(opt.key)}
            className={`px-2 py-0.5 text-[11px] rounded-md transition-colors ${
              filterKey === opt.key
                ? 'bg-[#E8F5E9] text-[#25785A] font-medium'
                : 'text-[#999999] hover:text-[#666666] hover:bg-[#F0F0F0]'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>
    </div>
  )
}

// ============================================================================
// Sorting + Filtering Helpers (still used by KPIs)
// ============================================================================

function getDriverLinkScore(d: BusinessDriver): number {
  return (d.evidence?.length ?? 0) + (d.linked_feature_count ?? 0) + (d.linked_persona_count ?? 0) + (d.linked_workflow_count ?? 0)
}

function sortDrivers(drivers: BusinessDriver[], key: SortKey): BusinessDriver[] {
  const sorted = [...drivers]
  switch (key) {
    case 'relevance':
      sorted.sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0))
      break
    case 'linked':
      sorted.sort((a, b) => getDriverLinkScore(b) - getDriverLinkScore(a))
      break
    case 'confirmed': {
      const confirmedSet = new Set(['confirmed_consultant', 'confirmed_client'])
      sorted.sort((a, b) => {
        const aConf = confirmedSet.has(a.confirmation_status ?? '') ? 1 : 0
        const bConf = confirmedSet.has(b.confirmation_status ?? '') ? 1 : 0
        return bConf - aConf
      })
      break
    }
    case 'newest':
      break
  }
  return sorted
}

function filterDrivers(drivers: BusinessDriver[], key: FilterKey): BusinessDriver[] {
  if (key === 'all') return drivers
  if (key === 'linked') {
    return drivers.filter((d) => getDriverLinkScore(d) > 0)
  }
  if (key === 'orphaned') {
    return drivers.filter((d) => getDriverLinkScore(d) === 0)
  }
  return drivers
}

// ============================================================================
// Main Section
// ============================================================================

export function BusinessContextSection({
  data,
  projectId,
  onConfirm,
  onNeedsReview,
  onConfirmAll,
  onUpdateVision,
  onUpdateBackground,
  onStatusClick,
  sectionScore,
  onOpenVisionDetail,
  onOpenBackgroundDetail,
  stakeholders = [],
}: BusinessContextSectionProps) {
  const [editingVision, setEditingVision] = useState(false)
  const [visionDraft, setVisionDraft] = useState(data.vision || '')
  const [editingBackground, setEditingBackground] = useState(false)
  const [backgroundDraft, setBackgroundDraft] = useState(data.background || '')
  const [showAllGoals, setShowAllGoals] = useState(false)
  const [showAllPains, setShowAllPains] = useState(false)
  const [showAllMetrics, setShowAllMetrics] = useState(false)
  const [selectedDriver, setSelectedDriver] = useState<{ id: string; type: 'pain' | 'goal' | 'kpi'; data: BusinessDriver } | null>(null)

  // Which driver row is expanded inline (only one at a time)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // Vision AI Enhance state
  const [showEnhanceMenu, setShowEnhanceMenu] = useState(false)
  const [aiSuggestion, setAiSuggestion] = useState<string | null>(null)
  const [isEnhancing, setIsEnhancing] = useState(false)
  const [enhancementError, setEnhancementError] = useState<string | null>(null)

  const handleEnhanceVision = async (type: string) => {
    setShowEnhanceMenu(false)
    setIsEnhancing(true)
    setEnhancementError(null)
    setAiSuggestion(null)
    try {
      const result = await enhanceVision(projectId, type)
      setAiSuggestion(result.suggestion)
    } catch (err) {
      setEnhancementError(err instanceof Error ? err.message : 'Enhancement failed')
    } finally {
      setIsEnhancing(false)
    }
  }

  const handleAcceptSuggestion = () => {
    if (aiSuggestion) {
      onUpdateVision(aiSuggestion)
      setAiSuggestion(null)
    }
  }

  const handleEditSuggestion = () => {
    if (aiSuggestion) {
      setVisionDraft(aiSuggestion)
      setEditingVision(true)
      setAiSuggestion(null)
    }
  }

  // Sort + filter state (KPIs only)
  const [metricSort, setMetricSort] = useState<SortKey>('relevance')
  const [metricFilter, setMetricFilter] = useState<FilterKey>('all')

  const handleSaveVision = () => {
    onUpdateVision(visionDraft)
    setEditingVision(false)
  }

  const handleSaveBackground = () => {
    onUpdateBackground(backgroundDraft)
    setEditingBackground(false)
  }

  const confirmedPains = data.pain_points.filter(
    (p) => p.confirmation_status === 'confirmed_consultant' || p.confirmation_status === 'confirmed_client'
  ).length
  const confirmedGoals = data.goals.filter(
    (g) => g.confirmation_status === 'confirmed_consultant' || g.confirmation_status === 'confirmed_client'
  ).length
  const confirmedMetrics = data.success_metrics.filter(
    (m) => m.confirmation_status === 'confirmed_consultant' || m.confirmation_status === 'confirmed_client'
  ).length

  // Sort goals + pains by relatability_score descending (built into container)
  const sortedPains = useMemo(
    () => [...data.pain_points].sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0)),
    [data.pain_points]
  )
  const sortedGoals = useMemo(
    () => [...data.goals].sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0)),
    [data.goals]
  )

  const processedMetrics = useMemo(
    () => sortDrivers(filterDrivers(data.success_metrics, metricFilter), metricSort),
    [data.success_metrics, metricSort, metricFilter]
  )

  const visibleGoals = showAllGoals ? sortedGoals : sortedGoals.slice(0, SHOW_MAX_DRIVERS)
  const visiblePains = showAllPains ? sortedPains : sortedPains.slice(0, SHOW_MAX_DRIVERS)
  const visibleMetrics = showAllMetrics ? processedMetrics : processedMetrics.slice(0, SHOW_MAX_METRICS)

  return (
    <section id="brd-section-business-context" className="space-y-8">
      {/* Background */}
      <div>
        <h2 className="text-lg font-semibold text-[#333333] mb-3 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-[#999999]" />
          What drove the need for this solution
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
          {editingBackground ? (
            <div className="space-y-3">
              <textarea
                value={backgroundDraft}
                onChange={(e) => setBackgroundDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-[#333333] border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/30 focus:border-[#3FAF7A] resize-y min-h-[80px]"
                placeholder="What drove the need for this solution..."
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveBackground}
                  className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setEditingBackground(false); setBackgroundDraft(data.background || '') }}
                  className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              {data.company_name && (
                <p className="text-[14px] font-medium text-[#333333] mb-1">
                  {data.company_name}
                  {data.industry && (
                    <span className="text-[#666666] font-normal"> &mdash; {data.industry}</span>
                  )}
                </p>
              )}
              {data.background ? (
                <p className="text-[14px] text-[#666666] leading-relaxed">{data.background}</p>
              ) : (
                <p className="text-[13px] text-[#999999] italic">No background description yet. Click to add one.</p>
              )}
              <div className="mt-2 flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => { setBackgroundDraft(data.background || ''); setEditingBackground(true) }}
                  className="inline-flex items-center gap-1 text-[12px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
                >
                  <Pencil className="w-3 h-3" />
                  Edit
                </button>
                {onOpenBackgroundDetail && (
                  <button
                    onClick={onOpenBackgroundDetail}
                    className="text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
                  >
                    View Details →
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Vision */}
      <div>
        <h2 className="text-lg font-semibold text-[#333333] mb-3 flex items-center gap-2">
          <Eye className="w-5 h-5 text-[#999999]" />
          Vision
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
          {editingVision ? (
            <div className="space-y-3">
              <textarea
                value={visionDraft}
                onChange={(e) => setVisionDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-[#333333] border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/30 focus:border-[#3FAF7A] resize-y min-h-[80px]"
                placeholder="Describe the product vision..."
                autoFocus
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSaveVision}
                  className="px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
                >
                  Save
                </button>
                <button
                  onClick={() => { setEditingVision(false); setVisionDraft(data.vision || '') }}
                  className="px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="group">
              {data.vision ? (
                <p className="text-[14px] text-[#666666] leading-relaxed">{data.vision}</p>
              ) : (
                <p className="text-[13px] text-[#999999] italic">No vision statement yet. Click to add one.</p>
              )}
              <div className="mt-2 flex items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity">
                <button
                  onClick={() => { setVisionDraft(data.vision || ''); setEditingVision(true) }}
                  className="inline-flex items-center gap-1 text-[12px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
                >
                  <Pencil className="w-3 h-3" />
                  Edit
                </button>
                {data.vision && (
                  <div className="relative">
                    <button
                      onClick={() => setShowEnhanceMenu(!showEnhanceMenu)}
                      className="inline-flex items-center gap-1 text-[12px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
                    >
                      <Sparkles className="w-3 h-3" />
                      AI Enhance
                    </button>
                    {showEnhanceMenu && (
                      <div className="absolute left-0 top-full mt-1 w-48 bg-white border border-[#E5E5E5] rounded-xl shadow-lg z-10 py-1">
                        {[
                          { key: 'enhance', label: 'Enhance' },
                          { key: 'simplify', label: 'Simplify' },
                          { key: 'metrics', label: 'Add Metrics' },
                          { key: 'professional', label: 'Make Professional' },
                        ].map((opt) => (
                          <button
                            key={opt.key}
                            onClick={() => handleEnhanceVision(opt.key)}
                            className="w-full text-left px-3 py-2 text-[12px] text-[#333333] hover:bg-[#E8F5E9] transition-colors"
                          >
                            {opt.label}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {onOpenVisionDetail && (
                  <button
                    onClick={onOpenVisionDetail}
                    className="text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors"
                  >
                    View Details →
                  </button>
                )}
              </div>

              {/* AI Enhancement loading/result */}
              {isEnhancing && (
                <div className="mt-3 p-3 border border-[#E5E5E5] rounded-xl bg-[#F4F4F4]">
                  <div className="flex items-center gap-2 text-[12px] text-[#666666]">
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-[#3FAF7A]" />
                    Generating suggestion...
                  </div>
                </div>
              )}
              {enhancementError && (
                <div className="mt-3 p-3 border border-red-200 rounded-xl bg-red-50">
                  <p className="text-[12px] text-red-600">{enhancementError}</p>
                </div>
              )}
              {aiSuggestion && (
                <div className="mt-3 p-4 border border-[#3FAF7A]/30 rounded-xl bg-[#E8F5E9]/30">
                  <p className="text-[11px] font-medium text-[#25785A] uppercase tracking-wide mb-2">AI Suggestion</p>
                  <p className="text-[14px] text-[#333333] leading-relaxed">{aiSuggestion}</p>
                  <div className="mt-3 flex items-center gap-2">
                    <button
                      onClick={handleAcceptSuggestion}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
                    >
                      <Check className="w-3 h-3" />
                      Accept
                    </button>
                    <button
                      onClick={handleEditSuggestion}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
                    >
                      <Pencil className="w-3 h-3" />
                      Edit
                    </button>
                    <button
                      onClick={() => setAiSuggestion(null)}
                      className="inline-flex items-center gap-1 px-3 py-1.5 text-[12px] font-medium text-[#999999] hover:text-[#666666] transition-colors"
                    >
                      <X className="w-3 h-3" />
                      Dismiss
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Business Goals — Action Queue pattern */}
      <DriverContainer
        icon={Target}
        title="BUSINESS GOALS"
        count={data.goals.length}
        confirmedCount={confirmedGoals}
        onConfirmAll={() => onConfirmAll('business_driver', data.goals.map(g => g.id))}
      >
        {data.goals.length === 0 ? (
          <p className="px-5 py-4 text-[13px] text-[#999999] italic">No business goals identified yet</p>
        ) : (
          <>
            {visibleGoals.map((goal) => (
              <DriverItemRow
                key={goal.id}
                driver={goal}
                driverType="goal"
                isExpanded={expandedId === goal.id}
                onToggle={() => setExpandedId(expandedId === goal.id ? null : goal.id)}
                onDrawerOpen={() => setSelectedDriver({ id: goal.id, type: 'goal', data: goal })}
                onConfirm={() => onConfirm('business_driver', goal.id)}
                onNeedsReview={() => onNeedsReview('business_driver', goal.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', goal.id, goal.description.slice(0, 60), goal.confirmation_status) : undefined}
              />
            ))}
            {sortedGoals.length > SHOW_MAX_DRIVERS && (
              <button
                onClick={() => setShowAllGoals(!showAllGoals)}
                className="w-full px-4 py-2.5 text-[12px] font-medium text-[#3FAF7A] hover:bg-[#FAFAFA] transition-colors border-t border-[#F0F0F0]"
              >
                {showAllGoals ? 'Show less' : `Show all ${sortedGoals.length} goals`}
              </button>
            )}
          </>
        )}
      </DriverContainer>

      {/* Business Pain Points — Action Queue pattern */}
      <DriverContainer
        icon={AlertTriangle}
        title="BUSINESS PAIN POINTS"
        count={data.pain_points.length}
        confirmedCount={confirmedPains}
        onConfirmAll={() => onConfirmAll('business_driver', data.pain_points.map(p => p.id))}
      >
        {data.pain_points.length === 0 ? (
          <p className="px-5 py-4 text-[13px] text-[#999999] italic">No pain points identified yet</p>
        ) : (
          <>
            {visiblePains.map((pain) => (
              <DriverItemRow
                key={pain.id}
                driver={pain}
                driverType="pain"
                isExpanded={expandedId === pain.id}
                onToggle={() => setExpandedId(expandedId === pain.id ? null : pain.id)}
                onDrawerOpen={() => setSelectedDriver({ id: pain.id, type: 'pain', data: pain })}
                onConfirm={() => onConfirm('business_driver', pain.id)}
                onNeedsReview={() => onNeedsReview('business_driver', pain.id)}
                onStatusClick={onStatusClick ? () => onStatusClick('business_driver', pain.id, pain.description.slice(0, 60), pain.confirmation_status) : undefined}
              />
            ))}
            {sortedPains.length > SHOW_MAX_DRIVERS && (
              <button
                onClick={() => setShowAllPains(!showAllPains)}
                className="w-full px-4 py-2.5 text-[12px] font-medium text-[#3FAF7A] hover:bg-[#FAFAFA] transition-colors border-t border-[#F0F0F0]"
              >
                {showAllPains ? 'Show less' : `Show all ${sortedPains.length} pain points`}
              </button>
            )}
          </>
        )}
      </DriverContainer>

      {/* Success Metrics (unchanged — keeps DriverCard pattern) */}
      <div>
        <SectionHeader
          title="Success Metrics"
          count={data.success_metrics.length}
          confirmedCount={confirmedMetrics}
          onConfirmAll={() => onConfirmAll('business_driver', data.success_metrics.map((m) => m.id))}
        />
        {data.success_metrics.length === 0 ? (
          <p className="text-[13px] text-[#999999] italic">No success metrics defined yet</p>
        ) : (
          <div>
            {data.success_metrics.length > 3 && (
              <SortFilterBar sortKey={metricSort} filterKey={metricFilter} onSortChange={setMetricSort} onFilterChange={setMetricFilter} />
            )}
            <div className="space-y-3">
              {visibleMetrics.map((metric) => (
                <DriverCard
                  key={metric.id}
                  driver={metric}
                  icon={BarChart3}
                  iconColor="text-[#3FAF7A]"
                  onConfirm={() => onConfirm('business_driver', metric.id)}
                  onNeedsReview={() => onNeedsReview('business_driver', metric.id)}
                  onStatusClick={onStatusClick ? () => onStatusClick('business_driver', metric.id, metric.description.slice(0, 60), metric.confirmation_status) : undefined}
                  onDetailClick={() => setSelectedDriver({ id: metric.id, type: 'kpi', data: metric })}
                />
              ))}
              {processedMetrics.length > SHOW_MAX_METRICS && !showAllMetrics && (
                <button
                  onClick={() => setShowAllMetrics(true)}
                  className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-[#999999] hover:text-[#3FAF7A] transition-colors w-full justify-center"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                  Show all {processedMetrics.length} metrics
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Detail Drawer */}
      {selectedDriver && (
        <BusinessDriverDetailDrawer
          driverId={selectedDriver.id}
          driverType={selectedDriver.type}
          projectId={projectId}
          initialData={selectedDriver.data}
          stakeholders={stakeholders}
          onClose={() => setSelectedDriver(null)}
          onConfirm={onConfirm}
          onNeedsReview={onNeedsReview}
        />
      )}
    </section>
  )
}
