'use client'

import { useState, useMemo } from 'react'
import { Building2, AlertTriangle, Target, Eye, BarChart3, Pencil, ChevronDown, ChevronRight, Users, Puzzle, Zap, FileText, Link2 } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import { EvidenceBlock } from '../components/EvidenceBlock'
import { BusinessDriverDetailDrawer } from '../components/BusinessDriverDetailDrawer'
import type { BRDWorkspaceData, BusinessDriver, VisionAlignment, SectionScore } from '@/types/workspace'

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
}

const SHOW_MAX_PAINS = 8
const SHOW_MAX_GOALS = 8
const SHOW_MAX_METRICS = 5

type SortKey = 'relevance' | 'linked' | 'confirmed' | 'newest'
type FilterKey = 'all' | 'linked' | 'orphaned'

// ============================================================================
// Vision Alignment Dot
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
// Link Summary Line (line 2 of collapsed card)
// ============================================================================

function LinkSummary({ driver }: { driver: BusinessDriver }) {
  const personaCount = driver.linked_persona_count ?? 0
  const featureCount = driver.linked_feature_count ?? 0
  const workflowCount = driver.linked_workflow_count ?? 0
  const totalLinks = personaCount + featureCount + workflowCount

  if (totalLinks === 0) {
    return (
      <span className="text-[11px] text-[#999999] bg-[#F0F0F0] px-2 py-0.5 rounded-full">
        Unlinked
      </span>
    )
  }

  return (
    <div className="flex items-center gap-3 text-[11px] text-[#666666]">
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
// Metric Line (line 3 of collapsed card — type-specific)
// ============================================================================

function MetricLine({ driver }: { driver: BusinessDriver }) {
  const evidenceCount = driver.evidence?.length ?? 0
  const parts: string[] = []

  if (driver.driver_type === 'pain') {
    if (driver.severity) parts.push(`Severity: ${driver.severity}`)
    if (driver.business_impact) parts.push(`Impact: ${driver.business_impact}`)
  } else if (driver.driver_type === 'goal') {
    if (driver.goal_timeframe) parts.push(`Timeframe: ${driver.goal_timeframe}`)
    if (driver.owner) parts.push(`Owner: ${driver.owner}`)
  } else if (driver.driver_type === 'kpi') {
    if (driver.baseline_value && driver.target_value) {
      parts.push(`${driver.baseline_value} → ${driver.target_value}`)
    } else if (driver.target_value) {
      parts.push(`Target: ${driver.target_value}`)
    }
  }

  if (parts.length === 0 && evidenceCount === 0) return null

  return (
    <div className="flex items-center gap-2 text-[11px] text-[#999999]">
      {parts.length > 0 && <span>{parts.join('  ·  ')}</span>}
      {evidenceCount > 0 && (
        <span className="flex items-center gap-0.5">
          <FileText className="w-3 h-3" />
          {evidenceCount} source{evidenceCount !== 1 ? 's' : ''}
        </span>
      )}
    </div>
  )
}

// ============================================================================
// Unified Driver Card (3-line collapsed, rich expanded)
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

  return (
    <div className={`bg-white rounded-2xl shadow-md border overflow-hidden ${
      driver.is_stale ? 'border-orange-200' : 'border-[#E5E5E5]'
    }`}>
      {/* Collapsed: 3-line display */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-3.5 text-left hover:bg-gray-50/50 transition-colors"
      >
        {/* Line 1: Title + status + vision dot */}
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

        {/* Line 2: Actor chips + link counts */}
        <div className="ml-[52px] mt-1.5">
          <LinkSummary driver={driver} />
        </div>

        {/* Line 3: Key metrics + evidence count */}
        <div className="ml-[52px] mt-1">
          <MetricLine driver={driver} />
        </div>
      </button>

      {/* Expanded view */}
      <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[3000px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className="px-5 pb-5 pt-1 border-t border-[#E5E5E5]">
          {/* Section 1: Type-specific fields */}
          <div className="space-y-2 text-[13px] text-[#666666] mb-4">
            {driver.driver_type === 'pain' && (
              <>
                {driver.severity && <div><span className="font-medium text-[#333333]">Severity:</span> {driver.severity}</div>}
                {driver.business_impact && <div><span className="font-medium text-[#333333]">Impact:</span> {driver.business_impact}</div>}
                {driver.affected_users && <div><span className="font-medium text-[#333333]">Affected Users:</span> {driver.affected_users}</div>}
                {driver.current_workaround && <div><span className="font-medium text-[#333333]">Workaround:</span> {driver.current_workaround}</div>}
              </>
            )}
            {driver.driver_type === 'goal' && (
              <>
                {driver.success_criteria && <div><span className="font-medium text-[#333333]">Success Criteria:</span> {driver.success_criteria}</div>}
                {driver.owner && <div><span className="font-medium text-[#333333]">Owner:</span> {driver.owner}</div>}
                {driver.goal_timeframe && <div><span className="font-medium text-[#333333]">Timeframe:</span> {driver.goal_timeframe}</div>}
              </>
            )}
            {driver.driver_type === 'kpi' && (
              <>
                {driver.baseline_value && <div><span className="font-medium text-[#333333]">Current:</span> {driver.baseline_value}</div>}
                {driver.target_value && <div><span className="font-medium text-[#333333]">Target:</span> {driver.target_value}</div>}
                {driver.measurement_method && <div><span className="font-medium text-[#333333]">Measurement:</span> {driver.measurement_method}</div>}
              </>
            )}
          </div>

          {/* Section 2: Connections (mini graph) */}
          {((driver.associated_persona_names?.length ?? 0) > 0 || (driver.linked_feature_count ?? 0) > 0 || (driver.linked_workflow_count ?? 0) > 0) && (
            <div className="mb-4">
              <h4 className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-2 flex items-center gap-1">
                <Link2 className="w-3 h-3" />
                Connections
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {driver.associated_persona_names?.map((name) => (
                  <span key={name} className="px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                    {name}
                  </span>
                ))}
                {(driver.linked_feature_count ?? 0) > 0 && (
                  <span className="px-2 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
                    {driver.linked_feature_count} feature{(driver.linked_feature_count ?? 0) !== 1 ? 's' : ''}
                  </span>
                )}
                {(driver.linked_workflow_count ?? 0) > 0 && (
                  <span className="px-2 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
                    {driver.linked_workflow_count} workflow{(driver.linked_workflow_count ?? 0) !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Section 3: Evidence trail (max 3 inline) */}
          <EvidenceBlock evidence={driver.evidence || []} maxItems={3} />

          {/* Actions row */}
          <div className="mt-3 pt-3 border-t border-[#E5E5E5] flex items-center justify-between">
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
    </div>
  )
}

// ============================================================================
// Sort / Filter Bar
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
    { key: 'linked', label: 'Linked' },
    { key: 'orphaned', label: 'Orphaned' },
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
// Sorting + Filtering Helpers
// ============================================================================

function sortDrivers(drivers: BusinessDriver[], key: SortKey): BusinessDriver[] {
  const sorted = [...drivers]
  switch (key) {
    case 'relevance':
      sorted.sort((a, b) => (b.relatability_score ?? 0) - (a.relatability_score ?? 0))
      break
    case 'linked':
      sorted.sort((a, b) => {
        const aLinks = (a.linked_feature_count ?? 0) + (a.linked_persona_count ?? 0) + (a.linked_workflow_count ?? 0)
        const bLinks = (b.linked_feature_count ?? 0) + (b.linked_persona_count ?? 0) + (b.linked_workflow_count ?? 0)
        return bLinks - aLinks
      })
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
      // Already sorted by newest if no explicit sort — keep as-is (backend default)
      break
  }
  return sorted
}

function filterDrivers(drivers: BusinessDriver[], key: FilterKey): BusinessDriver[] {
  if (key === 'all') return drivers
  if (key === 'linked') {
    return drivers.filter((d) =>
      (d.linked_feature_count ?? 0) + (d.linked_persona_count ?? 0) + (d.linked_workflow_count ?? 0) > 0
    )
  }
  if (key === 'orphaned') {
    return drivers.filter((d) =>
      (d.linked_feature_count ?? 0) + (d.linked_persona_count ?? 0) + (d.linked_workflow_count ?? 0) === 0
    )
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
}: BusinessContextSectionProps) {
  const [editingVision, setEditingVision] = useState(false)
  const [visionDraft, setVisionDraft] = useState(data.vision || '')
  const [editingBackground, setEditingBackground] = useState(false)
  const [backgroundDraft, setBackgroundDraft] = useState(data.background || '')
  const [showAllPains, setShowAllPains] = useState(false)
  const [showAllGoals, setShowAllGoals] = useState(false)
  const [showAllMetrics, setShowAllMetrics] = useState(false)
  const [selectedDriver, setSelectedDriver] = useState<{ id: string; type: 'pain' | 'goal' | 'kpi'; data: BusinessDriver } | null>(null)

  // Sort + filter state
  const [painSort, setPainSort] = useState<SortKey>('relevance')
  const [painFilter, setPainFilter] = useState<FilterKey>('all')
  const [goalSort, setGoalSort] = useState<SortKey>('relevance')
  const [goalFilter, setGoalFilter] = useState<FilterKey>('all')
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

  const processedPains = useMemo(
    () => sortDrivers(filterDrivers(data.pain_points, painFilter), painSort),
    [data.pain_points, painSort, painFilter]
  )
  const processedGoals = useMemo(
    () => sortDrivers(filterDrivers(data.goals, goalFilter), goalSort),
    [data.goals, goalSort, goalFilter]
  )
  const processedMetrics = useMemo(
    () => sortDrivers(filterDrivers(data.success_metrics, metricFilter), metricSort),
    [data.success_metrics, metricSort, metricFilter]
  )

  const visiblePains = showAllPains ? processedPains : processedPains.slice(0, SHOW_MAX_PAINS)
  const visibleGoals = showAllGoals ? processedGoals : processedGoals.slice(0, SHOW_MAX_GOALS)
  const visibleMetrics = showAllMetrics ? processedMetrics : processedMetrics.slice(0, SHOW_MAX_METRICS)

  return (
    <section className="space-y-8">
      {/* Background */}
      <div>
        <h2 className="text-lg font-semibold text-[#333333] mb-3 flex items-center gap-2">
          <Building2 className="w-5 h-5 text-[#999999]" />
          Background
        </h2>
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
          {editingBackground ? (
            <div className="space-y-3">
              <textarea
                value={backgroundDraft}
                onChange={(e) => setBackgroundDraft(e.target.value)}
                className="w-full p-3 text-[14px] text-[#333333] border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/30 focus:border-[#3FAF7A] resize-y min-h-[80px]"
                placeholder="Describe the company background..."
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

      {/* Pain Points */}
      <div>
        <SectionHeader
          title="Pain Points"
          count={data.pain_points.length}
          confirmedCount={confirmedPains}
          onConfirmAll={() => onConfirmAll('business_driver', data.pain_points.map((p) => p.id))}
          sectionScore={sectionScore}
        />
        {data.pain_points.length === 0 ? (
          <p className="text-[13px] text-[#999999] italic">No pain points identified yet</p>
        ) : (
          <div>
            {data.pain_points.length > 3 && (
              <SortFilterBar sortKey={painSort} filterKey={painFilter} onSortChange={setPainSort} onFilterChange={setPainFilter} />
            )}
            <div className="space-y-3">
              {visiblePains.map((pain) => (
                <DriverCard
                  key={pain.id}
                  driver={pain}
                  icon={AlertTriangle}
                  iconColor="text-[#999999]"
                  onConfirm={() => onConfirm('business_driver', pain.id)}
                  onNeedsReview={() => onNeedsReview('business_driver', pain.id)}
                  onStatusClick={onStatusClick ? () => onStatusClick('business_driver', pain.id, pain.description.slice(0, 60), pain.confirmation_status) : undefined}
                  onDetailClick={() => setSelectedDriver({ id: pain.id, type: 'pain', data: pain })}
                />
              ))}
              {processedPains.length > SHOW_MAX_PAINS && !showAllPains && (
                <button
                  onClick={() => setShowAllPains(true)}
                  className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-[#999999] hover:text-[#3FAF7A] transition-colors w-full justify-center"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                  Show all {processedPains.length} pain points
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Business Goals */}
      <div>
        <SectionHeader
          title="Business Goals"
          count={data.goals.length}
          confirmedCount={confirmedGoals}
          onConfirmAll={() => onConfirmAll('business_driver', data.goals.map((g) => g.id))}
        />
        {data.goals.length === 0 ? (
          <p className="text-[13px] text-[#999999] italic">No business goals identified yet</p>
        ) : (
          <div>
            {data.goals.length > 3 && (
              <SortFilterBar sortKey={goalSort} filterKey={goalFilter} onSortChange={setGoalSort} onFilterChange={setGoalFilter} />
            )}
            <div className="space-y-3">
              {visibleGoals.map((goal) => (
                <DriverCard
                  key={goal.id}
                  driver={goal}
                  icon={Target}
                  iconColor="text-[#3FAF7A]"
                  onConfirm={() => onConfirm('business_driver', goal.id)}
                  onNeedsReview={() => onNeedsReview('business_driver', goal.id)}
                  onStatusClick={onStatusClick ? () => onStatusClick('business_driver', goal.id, goal.description.slice(0, 60), goal.confirmation_status) : undefined}
                  onDetailClick={() => setSelectedDriver({ id: goal.id, type: 'goal', data: goal })}
                />
              ))}
              {processedGoals.length > SHOW_MAX_GOALS && !showAllGoals && (
                <button
                  onClick={() => setShowAllGoals(true)}
                  className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium text-[#999999] hover:text-[#3FAF7A] transition-colors w-full justify-center"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                  Show all {processedGoals.length} goals
                </button>
              )}
            </div>
          </div>
        )}
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
                {onOpenVisionDetail && (
                  <button
                    onClick={onOpenVisionDetail}
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

      {/* Success Metrics */}
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
          onClose={() => setSelectedDriver(null)}
          onConfirm={onConfirm}
          onNeedsReview={onNeedsReview}
        />
      )}
    </section>
  )
}
