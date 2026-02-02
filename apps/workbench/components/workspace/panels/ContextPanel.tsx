/**
 * ContextPanel - Strategic Intelligence view
 *
 * 4 tabs: Foundation (merged with Company), Business Drivers, Market, Stakeholders
 * Fetches foundation, status, company-info, business-drivers, and competitors.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  Target,
  TrendingUp,
  Globe,
  Users,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Sparkles,
  CheckCircle,
  AlertCircle,
  Clock,
  BarChart3,
  Loader2,
  AlertTriangle,
} from 'lucide-react'
import { getProjectFoundation, getProjectStatus, markEntityNeedsReview } from '@/lib/api'
import type { ProjectFoundation, ProjectStatusResponse } from '@/lib/api'
import { Markdown } from '@/components/ui/Markdown'
import { API_BASE } from '@/lib/config'

// --- Local interfaces ---

interface CompanyInfo {
  id?: string
  name: string
  industry: string | null
  stage: string | null
  size: string | null
  website: string | null
  description: string | null
  key_differentiators: string[]
  location: string | null
  unique_selling_point: string | null
  customers: string | null
  products_services: string | null
  industry_overview: string | null
  industry_trends: string | null
  fast_facts: string | null
  enrichment_source: string | null
  enriched_at: string | null
}

interface Evidence {
  chunk_id?: string
  excerpt?: string
  text?: string
  rationale?: string
}

interface BusinessDriver {
  id: string
  driver_type: 'kpi' | 'pain' | 'goal'
  description: string
  measurement?: string | null
  priority?: number
  confirmation_status?: string
  evidence?: Evidence[]
  enrichment_status?: string
  enriched_at?: string
  owner?: string
  // KPI
  baseline_value?: string
  target_value?: string
  measurement_method?: string
  tracking_frequency?: string
  data_source?: string
  responsible_team?: string
  // Pain
  severity?: string
  frequency?: string
  affected_users?: string
  business_impact?: string
  current_workaround?: string
  // Goal
  goal_timeframe?: string
  success_criteria?: string
  dependencies?: string
}

interface CompetitorRef {
  id: string
  name: string
  url?: string | null
  strengths?: string[]
  weaknesses?: string[]
  notes?: string | null
  research_notes?: string | null
  reference_type: string
  category?: string | null
  features_to_study?: string[]
}

// --- Component ---

interface ContextPanelProps {
  projectId: string
}

type ContextTab = 'foundation' | 'drivers' | 'market' | 'stakeholders'

const TABS: { id: ContextTab; label: string; icon: typeof Target }[] = [
  { id: 'foundation', label: 'Foundation', icon: Target },
  { id: 'drivers', label: 'Drivers', icon: TrendingUp },
  { id: 'market', label: 'Market', icon: Globe },
  { id: 'stakeholders', label: 'Stakeholders', icon: Users },
]

export function ContextPanel({ projectId }: ContextPanelProps) {
  const [foundation, setFoundation] = useState<ProjectFoundation | null>(null)
  const [status, setStatus] = useState<ProjectStatusResponse | null>(null)
  const [companyInfo, setCompanyInfo] = useState<CompanyInfo | null>(null)
  const [drivers, setDrivers] = useState<BusinessDriver[]>([])
  const [competitors, setCompetitors] = useState<CompetitorRef[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<ContextTab>('foundation')

  const fetchAll = useCallback(() => {
    setIsLoading(true)
    const baseUrl = API_BASE

    Promise.all([
      getProjectFoundation(projectId).catch(() => null),
      getProjectStatus(projectId).catch(() => null),
      fetch(`${baseUrl}/v1/state/company-info?project_id=${projectId}`)
        .then(r => r.ok ? r.json() : null)
        .then(d => d?.company_info || null)
        .catch(() => null),
      fetch(`${baseUrl}/v1/projects/${projectId}/business-drivers`)
        .then(r => r.ok ? r.json() : null)
        .then(d => d?.business_drivers || [])
        .catch(() => []),
      fetch(`${baseUrl}/v1/projects/${projectId}/competitors`)
        .then(r => r.ok ? r.json() : null)
        .then(d => d?.competitor_references || [])
        .catch(() => []),
    ])
      .then(([f, s, ci, bd, cr]) => {
        setFoundation(f)
        setStatus(s)
        setCompanyInfo(ci)
        setDrivers(bd)
        setCompetitors(cr)
      })
      .finally(() => setIsLoading(false))
  }, [projectId])

  useEffect(() => { fetchAll() }, [fetchAll])

  const handleDriverUpdate = useCallback((id: string, updates: Partial<BusinessDriver>) => {
    setDrivers(prev => prev.map(d => d.id === id ? { ...d, ...updates } : d))
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-teal" />
      </div>
    )
  }

  if (!foundation && !status && !companyInfo && drivers.length === 0) {
    return (
      <p className="text-sm text-ui-supportText text-center py-8">
        No strategic data available yet. Run the DI Agent to extract insights.
      </p>
    )
  }

  return (
    <div>
      {/* Tab Navigation */}
      <div className="flex gap-1 mb-5 -mt-1">
        {TABS.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-brand-teal/10 text-brand-teal'
                  : 'text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {activeTab === 'foundation' && (
        <FoundationTab foundation={foundation} companyInfo={companyInfo} />
      )}
      {activeTab === 'drivers' && (
        <DriversTab
          projectId={projectId}
          drivers={drivers}
          status={status}
          onDriverUpdate={handleDriverUpdate}
        />
      )}
      {activeTab === 'market' && (
        <MarketTab companyInfo={companyInfo} competitors={competitors} status={status} />
      )}
      {activeTab === 'stakeholders' && (
        <StakeholdersTab status={status} />
      )}
    </div>
  )
}

// =============================================================================
// Tab 1: Foundation (merged with Company)
// =============================================================================

function FoundationTab({
  foundation,
  companyInfo,
}: {
  foundation: ProjectFoundation | null
  companyInfo: CompanyInfo | null
}) {
  const hasCompany = companyInfo && (companyInfo.name || companyInfo.industry)
  const hasFoundation = foundation && (foundation.core_pain || foundation.wow_moment || foundation.business_case)

  if (!hasCompany && !hasFoundation) {
    return <EmptyState message="Foundation data not extracted yet." />
  }

  return (
    <div className="space-y-6">
      {/* Company Overview */}
      {hasCompany && (
        <div>
          <SectionHeader title="Company Overview" />
          <div className="grid grid-cols-3 gap-3 mb-4">
            {companyInfo!.name && <InfoCell label="Name" value={companyInfo!.name} />}
            {companyInfo!.industry && <InfoCell label="Industry" value={companyInfo!.industry} />}
            {companyInfo!.stage && <InfoCell label="Stage" value={companyInfo!.stage} />}
            {companyInfo!.size && <InfoCell label="Size" value={companyInfo!.size} />}
            {companyInfo!.website && (
              <div className="bg-ui-background rounded-lg px-3 py-2">
                <span className="text-[11px] text-ui-supportText">Website</span>
                <a
                  href={companyInfo!.website.startsWith('http') ? companyInfo!.website : `https://${companyInfo!.website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-sm text-brand-teal hover:underline"
                >
                  {companyInfo!.website}
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            )}
            {companyInfo!.location && <InfoCell label="Location" value={companyInfo!.location} />}
          </div>

          {/* USP */}
          {companyInfo!.unique_selling_point && (
            <div className="bg-brand-teal/5 border border-brand-teal/20 rounded-lg p-4 mb-4">
              <h5 className="text-xs font-semibold text-brand-teal uppercase tracking-wide mb-1.5">
                Unique Selling Point
              </h5>
              <Markdown
                content={companyInfo!.unique_selling_point}
                className="text-sm text-ui-bodyText prose prose-sm max-w-none"
              />
            </div>
          )}

          {/* Key Differentiators */}
          {companyInfo!.key_differentiators && companyInfo!.key_differentiators.length > 0 && (
            <div className="mb-4">
              <span className="text-[11px] text-ui-supportText font-medium uppercase tracking-wide">Key Differentiators</span>
              <div className="flex flex-wrap gap-1.5 mt-1.5">
                {companyInfo!.key_differentiators.map((d, i) => (
                  <span key={i} className="px-2 py-0.5 text-[11px] rounded-full bg-emerald-50 text-emerald-700">
                    {d}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Target Customers */}
      {companyInfo?.customers && (
        <div>
          <SectionHeader title="Target Customers" />
          <div className="border-l-3 border-emerald-400 pl-4 py-1">
            <RichContent content={companyInfo.customers} />
          </div>
        </div>
      )}

      {/* Products & Services */}
      {companyInfo?.products_services && (
        <div>
          <SectionHeader title="Products & Services" />
          <div className="border-l-3 border-teal-400 pl-4 py-1">
            <RichContent content={companyInfo.products_services} />
          </div>
        </div>
      )}

      {/* Core Foundation Cards */}
      {hasFoundation && (
        <div>
          <SectionHeader title="Strategic Foundation" />
          <div className="grid grid-cols-2 gap-4">
            <DataCard title="Core Pain">
              {foundation!.core_pain ? (
                <>
                  <p className="text-sm text-ui-bodyText">{foundation!.core_pain.statement}</p>
                  <ConfidenceBar value={foundation!.core_pain.confidence} />
                </>
              ) : (
                <NotExtracted />
              )}
            </DataCard>

            <DataCard title="Wow Moment">
              {foundation!.wow_moment ? (
                <>
                  <p className="text-sm text-ui-bodyText">{foundation!.wow_moment.description}</p>
                  <ConfidenceBar value={foundation!.wow_moment.confidence} />
                </>
              ) : (
                <NotExtracted />
              )}
            </DataCard>

            <DataCard title="Business Case">
              {foundation!.business_case ? (
                <>
                  <p className="text-sm text-ui-bodyText">{foundation!.business_case.value_to_business}</p>
                  <p className="text-[11px] text-ui-supportText mt-1">{foundation!.business_case.roi_framing}</p>
                </>
              ) : (
                <NotExtracted />
              )}
            </DataCard>

            <DataCard title="Budget & Constraints">
              {foundation!.budget_constraints ? (
                <>
                  <p className="text-sm text-ui-bodyText">
                    {foundation!.budget_constraints.budget_range}
                  </p>
                  {foundation!.budget_constraints.technical_constraints.length > 0 && (
                    <div className="mt-2">
                      <span className="text-[11px] text-ui-supportText">Technical:</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {foundation!.budget_constraints.technical_constraints.map((c, i) => (
                          <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-100 text-emerald-800">{c}</span>
                        ))}
                      </div>
                    </div>
                  )}
                  {foundation!.budget_constraints.organizational_constraints.length > 0 && (
                    <div className="mt-1.5">
                      <span className="text-[11px] text-ui-supportText">Organizational:</span>
                      <div className="flex flex-wrap gap-1 mt-0.5">
                        {foundation!.budget_constraints.organizational_constraints.map((c, i) => (
                          <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-teal-50 text-teal-700">{c}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <NotExtracted />
              )}
            </DataCard>
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Tab 2: Business Drivers (expanded, with confirm/needs review)
// =============================================================================

function DriversTab({
  projectId,
  drivers,
  status,
  onDriverUpdate,
}: {
  projectId: string
  drivers: BusinessDriver[]
  status: ProjectStatusResponse | null
  onDriverUpdate: (id: string, updates: Partial<BusinessDriver>) => void
}) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const kpis = drivers.filter(d => d.driver_type === 'kpi')
  const pains = drivers.filter(d => d.driver_type === 'pain')
  const goals = drivers.filter(d => d.driver_type === 'goal')
  const hasDrivers = drivers.length > 0

  const confirmedCount = status?.strategic?.confirmed_drivers ?? 0
  const totalCount = status?.strategic?.total_drivers ?? drivers.length

  if (!hasDrivers && !status?.strategic) {
    return <EmptyState message="No business drivers extracted yet." />
  }

  if (!hasDrivers && status?.strategic) {
    return <DriversTabFallback status={status} />
  }

  return (
    <div className="space-y-5">
      {/* Progress bar */}
      {totalCount > 0 && (
        <div className="flex items-center gap-3">
          <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-teal rounded-full transition-all"
              style={{ width: `${(confirmedCount / totalCount) * 100}%` }}
            />
          </div>
          <span className="text-[11px] text-ui-supportText whitespace-nowrap">
            {confirmedCount}/{totalCount} confirmed
          </span>
        </div>
      )}

      {kpis.length > 0 && (
        <DriverSection
          title="KPIs"
          headerClass="bg-emerald-50 text-emerald-700"
          drivers={kpis}
          expandedIds={expandedIds}
          onToggle={toggleExpand}
          projectId={projectId}
          onDriverUpdate={onDriverUpdate}
        />
      )}

      {pains.length > 0 && (
        <DriverSection
          title="Business Pains"
          headerClass="bg-teal-50 text-teal-700"
          drivers={pains}
          expandedIds={expandedIds}
          onToggle={toggleExpand}
          projectId={projectId}
          onDriverUpdate={onDriverUpdate}
        />
      )}

      {goals.length > 0 && (
        <DriverSection
          title="Business Goals"
          headerClass="bg-emerald-100 text-emerald-800"
          drivers={goals}
          expandedIds={expandedIds}
          onToggle={toggleExpand}
          projectId={projectId}
          onDriverUpdate={onDriverUpdate}
        />
      )}
    </div>
  )
}

function DriverSection({
  title,
  headerClass,
  drivers,
  expandedIds,
  onToggle,
  projectId,
  onDriverUpdate,
}: {
  title: string
  headerClass: string
  drivers: BusinessDriver[]
  expandedIds: Set<string>
  onToggle: (id: string) => void
  projectId: string
  onDriverUpdate: (id: string, updates: Partial<BusinessDriver>) => void
}) {
  return (
    <div>
      <div className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide mb-2 ${headerClass}`}>
        {title}
        <span className="ml-1.5 opacity-70">({drivers.length})</span>
      </div>
      <div className="space-y-2">
        {drivers.map((driver) => (
          <DriverCard
            key={driver.id}
            driver={driver}
            isExpanded={expandedIds.has(driver.id)}
            onToggle={() => onToggle(driver.id)}
            projectId={projectId}
            onDriverUpdate={onDriverUpdate}
          />
        ))}
      </div>
    </div>
  )
}

function DriverCard({
  driver,
  isExpanded,
  onToggle,
  projectId,
  onDriverUpdate,
}: {
  driver: BusinessDriver
  isExpanded: boolean
  onToggle: () => void
  projectId: string
  onDriverUpdate: (id: string, updates: Partial<BusinessDriver>) => void
}) {
  const [updating, setUpdating] = useState(false)
  const isEnriched = driver.enrichment_status === 'enriched'
  const Chevron = isExpanded ? ChevronUp : ChevronDown

  const handleConfirm = async () => {
    try {
      setUpdating(true)
      const baseUrl = API_BASE
      const res = await fetch(`${baseUrl}/v1/projects/${projectId}/business-drivers/${driver.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_status: 'confirmed_consultant' }),
      })
      if (res.ok) {
        onDriverUpdate(driver.id, { confirmation_status: 'confirmed_consultant' })
      }
    } catch (error) {
      console.error('Failed to confirm:', error)
    } finally {
      setUpdating(false)
    }
  }

  const handleNeedsReview = async () => {
    try {
      setUpdating(true)
      const entityType = driver.driver_type === 'pain' ? 'pain_point' : driver.driver_type
      await markEntityNeedsReview(projectId, entityType, driver.id)
      onDriverUpdate(driver.id, { confirmation_status: 'needs_client' })
    } catch (error) {
      console.error('Failed to mark for review:', error)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="bg-ui-background rounded-lg overflow-hidden">
      {/* Collapsed row — always clickable */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left cursor-pointer hover:bg-gray-100/50 transition-colors"
      >
        {/* Confirmation status dot */}
        <ConfirmationDot status={driver.confirmation_status} />

        {/* Description */}
        <span className="flex-1 text-[12px] text-ui-bodyText leading-snug">{driver.description}</span>

        {/* Badges */}
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <ConfirmationBadge status={driver.confirmation_status} />
          {isEnriched && (
            <span className="flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] rounded bg-teal-50 text-teal-700">
              <Sparkles className="w-2.5 h-2.5" />
              Enriched
            </span>
          )}
          {driver.severity && <SeverityBadge severity={driver.severity} />}
          <EvidenceIndicator count={driver.evidence?.length || 0} />
          <Chevron className="w-3.5 h-3.5 text-ui-supportText" />
        </div>
      </button>

      {/* Expanded details */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 border-t border-gray-100 space-y-3">
          {/* Type-specific enrichment sections */}
          {driver.driver_type === 'kpi' && <KpiDetails driver={driver} />}
          {driver.driver_type === 'pain' && <PainDetails driver={driver} />}
          {driver.driver_type === 'goal' && <GoalDetails driver={driver} />}

          {/* Evidence */}
          {driver.evidence && driver.evidence.length > 0 && (
            <div>
              <h4 className="text-[10px] font-medium text-ui-supportText uppercase tracking-wide mb-1.5">
                Evidence ({driver.evidence.length})
              </h4>
              <div className="space-y-1.5">
                {driver.evidence.slice(0, 3).map((ev, i) => (
                  <div key={i} className="bg-emerald-50 rounded-lg p-2.5 border border-emerald-100">
                    <blockquote className="text-[11px] text-emerald-800 italic">
                      &ldquo;{ev.excerpt || ev.text}&rdquo;
                    </blockquote>
                    {ev.rationale && (
                      <span className="block text-[10px] text-emerald-600 mt-1">{ev.rationale}</span>
                    )}
                  </div>
                ))}
                {driver.evidence.length > 3 && (
                  <p className="text-[10px] text-ui-supportText italic">
                    +{driver.evidence.length - 3} more evidence items
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Enrichment date */}
          {driver.enriched_at && (
            <p className="text-[10px] text-ui-supportText">
              Enriched {new Date(driver.enriched_at).toLocaleDateString()}
            </p>
          )}

          {/* Confirm / Needs Review buttons */}
          <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
            <button
              onClick={handleConfirm}
              disabled={updating || driver.confirmation_status === 'confirmed_consultant'}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                driver.confirmation_status === 'confirmed_consultant'
                  ? 'bg-[#009b87] text-white'
                  : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
              } disabled:opacity-50`}
            >
              {updating ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <CheckCircle className="h-3.5 w-3.5" />
              )}
              Confirm
            </button>
            <button
              onClick={handleNeedsReview}
              disabled={updating || driver.confirmation_status === 'needs_client'}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                driver.confirmation_status === 'needs_client'
                  ? 'bg-teal-600 text-white'
                  : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
              } disabled:opacity-50`}
            >
              <AlertCircle className="h-3.5 w-3.5" />
              Needs Review
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// --- KPI expanded details ---
function KpiDetails({ driver }: { driver: BusinessDriver }) {
  const hasBaseline = !!driver.baseline_value
  const hasTarget = !!driver.target_value

  const hasAny = hasBaseline || hasTarget || driver.measurement_method ||
    driver.tracking_frequency || driver.data_source || driver.responsible_team

  if (!hasAny) return null

  return (
    <div>
      <h4 className="text-[10px] font-medium text-ui-supportText uppercase tracking-wide mb-2 flex items-center gap-1">
        <BarChart3 className="h-3 w-3" />
        Measurement Details
      </h4>
      <div className="space-y-2.5">
        {/* Baseline → Target */}
        {(hasBaseline || hasTarget) && (
          <div className="bg-emerald-50 rounded-lg p-2.5 border border-emerald-100">
            <div className="grid grid-cols-2 gap-3">
              {hasBaseline && (
                <div>
                  <div className="text-[10px] text-ui-supportText mb-0.5">Current (Baseline)</div>
                  <div className="text-sm font-semibold text-gray-700">{driver.baseline_value}</div>
                </div>
              )}
              {hasTarget && (
                <div>
                  <div className="text-[10px] text-ui-supportText mb-0.5">Target</div>
                  <div className="text-sm font-semibold text-emerald-700">{driver.target_value}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Measurement Method */}
        {driver.measurement_method && (
          <div>
            <div className="text-[10px] font-medium text-ui-supportText mb-0.5">Measurement Method</div>
            <div className="text-xs text-gray-700 bg-gray-50 rounded p-2 border border-gray-100">
              {driver.measurement_method}
            </div>
          </div>
        )}

        {/* Tracking details grid */}
        <div className="grid grid-cols-2 gap-2.5">
          {driver.tracking_frequency && (
            <div>
              <div className="text-[10px] font-medium text-ui-supportText mb-0.5">Tracking Frequency</div>
              <div className="text-xs text-gray-700 capitalize flex items-center gap-1">
                <Clock className="h-3 w-3 text-gray-400" />
                {driver.tracking_frequency}
              </div>
            </div>
          )}
          {driver.data_source && (
            <div>
              <div className="text-[10px] font-medium text-ui-supportText mb-0.5">Data Source</div>
              <div className="text-xs text-gray-700">{driver.data_source}</div>
            </div>
          )}
        </div>

        {/* Responsible team */}
        {driver.responsible_team && (
          <div>
            <div className="text-[10px] font-medium text-ui-supportText mb-0.5">Responsible Team</div>
            <div className="flex items-center gap-1.5 text-xs text-gray-700">
              <Users className="h-3 w-3 text-emerald-600" />
              {driver.responsible_team}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// --- Pain expanded details ---
function PainDetails({ driver }: { driver: BusinessDriver }) {
  const hasAny = driver.severity || driver.frequency || driver.affected_users ||
    driver.business_impact || driver.current_workaround

  if (!hasAny) return null

  return (
    <div>
      <h4 className="text-[10px] font-medium text-ui-supportText uppercase tracking-wide mb-2 flex items-center gap-1">
        <AlertCircle className="h-3 w-3" />
        Impact Analysis
      </h4>
      <div className="space-y-2.5">
        {/* Severity + Frequency row */}
        {(driver.severity || driver.frequency) && (
          <div className="grid grid-cols-2 gap-2.5">
            {driver.severity && (
              <div>
                <div className="text-[10px] font-medium text-ui-supportText mb-1">Severity</div>
                <SeverityBadgeLarge severity={driver.severity} />
              </div>
            )}
            {driver.frequency && (
              <div>
                <div className="text-[10px] font-medium text-ui-supportText mb-1">Frequency</div>
                <div className="flex items-center gap-1.5 text-xs text-gray-700">
                  <Clock className="h-3.5 w-3.5 text-gray-400" />
                  <span className="capitalize">{driver.frequency}</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Affected Users */}
        {driver.affected_users && (
          <div className="bg-emerald-50 rounded-lg p-2.5 border border-emerald-100">
            <div className="text-[10px] font-medium text-emerald-700 mb-0.5 flex items-center gap-1">
              <Users className="h-2.5 w-2.5" />
              Who Experiences This Pain
            </div>
            <div className="text-xs text-emerald-900">{driver.affected_users}</div>
          </div>
        )}

        {/* Business Impact */}
        {driver.business_impact && (
          <div className="bg-emerald-50 rounded-lg p-2.5 border border-emerald-200">
            <div className="text-[10px] font-medium text-emerald-700 mb-0.5 flex items-center gap-1">
              <TrendingUp className="h-2.5 w-2.5" />
              Quantified Business Impact
            </div>
            <div className="text-xs font-semibold text-emerald-900">{driver.business_impact}</div>
          </div>
        )}

        {/* Current Workaround */}
        {driver.current_workaround && (
          <div>
            <div className="text-[10px] font-medium text-ui-supportText mb-0.5">Current Workaround</div>
            <div className="text-xs text-gray-700 bg-gray-50 rounded p-2.5 border border-gray-200 italic">
              &ldquo;{driver.current_workaround}&rdquo;
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// --- Goal expanded details ---
function GoalDetails({ driver }: { driver: BusinessDriver }) {
  const criteriaList = driver.success_criteria
    ? driver.success_criteria.split(/[;\n]+/).map(s => s.trim()).filter(Boolean)
    : []
  const depsList = driver.dependencies
    ? driver.dependencies.split(/[;\n]+/).map(s => s.trim()).filter(Boolean)
    : []

  const hasAny = driver.goal_timeframe || criteriaList.length > 0 || depsList.length > 0 || driver.owner

  if (!hasAny) return null

  return (
    <div>
      <h4 className="text-[10px] font-medium text-ui-supportText uppercase tracking-wide mb-2 flex items-center gap-1">
        <Target className="h-3 w-3" />
        Achievement Criteria
      </h4>
      <div className="space-y-2.5">
        {/* Timeframe */}
        {driver.goal_timeframe && (
          <div className="bg-emerald-50 rounded-lg p-2.5 border border-emerald-200">
            <div className="text-[10px] font-medium text-emerald-700 mb-0.5 flex items-center gap-1">
              <Clock className="h-2.5 w-2.5" />
              Target Timeframe
            </div>
            <div className="text-xs font-semibold text-emerald-900">{driver.goal_timeframe}</div>
          </div>
        )}

        {/* Success Criteria */}
        {criteriaList.length > 0 && (
          <div>
            <div className="text-[10px] font-medium text-gray-700 mb-1.5 flex items-center gap-1">
              <CheckCircle className="h-2.5 w-2.5 text-emerald-600" />
              Success Criteria ({criteriaList.length})
            </div>
            <div className="space-y-1">
              {criteriaList.map((c, i) => (
                <div key={i} className="flex items-start gap-1.5 bg-emerald-50 rounded p-2 border border-emerald-100">
                  <CheckCircle className="h-3 w-3 text-emerald-600 mt-0.5 flex-shrink-0" />
                  <span className="text-xs text-gray-700">{c}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dependencies */}
        {depsList.length > 0 && (
          <div>
            <div className="text-[10px] font-medium text-gray-700 mb-1.5 flex items-center gap-1">
              <AlertTriangle className="h-2.5 w-2.5 text-teal-600" />
              Dependencies ({depsList.length})
            </div>
            <div className="space-y-1">
              {depsList.map((d, i) => (
                <div key={i} className="flex items-start gap-1.5 bg-teal-50 rounded p-2 border border-teal-100">
                  <div className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-1.5 flex-shrink-0" />
                  <span className="text-xs text-gray-700">{d}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Owner */}
        {driver.owner && (
          <div>
            <div className="text-[10px] font-medium text-ui-supportText mb-0.5">Goal Owner</div>
            <div className="flex items-center gap-1.5 text-xs text-gray-700 bg-gray-50 rounded p-2 border border-gray-200">
              <Users className="h-3 w-3 text-emerald-600" />
              <span className="font-medium">{driver.owner}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// --- Driver helper components ---

function ConfirmationDot({ status }: { status?: string }) {
  const isConfirmed = status?.startsWith('confirmed')
  const needsReview = status === 'needs_client'
  if (isConfirmed) return <CheckCircle className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" />
  if (needsReview) return <Clock className="w-3.5 h-3.5 text-teal-500 flex-shrink-0" />
  return <AlertCircle className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
}

function ConfirmationBadge({ status }: { status?: string }) {
  const s = status || 'ai_generated'
  if (s === 'confirmed_client') {
    return (
      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
        <CheckCircle className="h-2.5 w-2.5" />
        Client
      </span>
    )
  }
  if (s === 'confirmed_consultant') {
    return (
      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
        <CheckCircle className="h-2.5 w-2.5" />
        Confirmed
      </span>
    )
  }
  if (s === 'needs_client') {
    return (
      <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-teal-100 text-teal-800 border border-teal-200">
        <Clock className="h-2.5 w-2.5" />
        Needs Review
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200">
      AI Draft
    </span>
  )
}

function EvidenceIndicator({ count }: { count: number }) {
  const filled = count >= 3 ? 3 : count >= 2 ? 2 : count >= 1 ? 1 : 0
  if (filled === 0) return null
  return (
    <div className="flex items-center gap-0.5" title={`${count} evidence source${count !== 1 ? 's' : ''}`}>
      {[1, 2, 3].map(i => (
        <div
          key={i}
          className={`w-1 h-1 rounded-full ${i <= filled ? 'bg-[#009b87]' : 'bg-gray-200'}`}
        />
      ))}
    </div>
  )
}

function SeverityBadge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    critical: 'bg-emerald-200 text-emerald-900',
    high: 'bg-emerald-100 text-emerald-800',
    medium: 'bg-teal-50 text-teal-700',
    low: 'bg-gray-100 text-gray-600',
  }
  return (
    <span className={`px-1.5 py-0.5 text-[10px] rounded font-medium capitalize ${styles[severity] || styles.low}`}>
      {severity}
    </span>
  )
}

function SeverityBadgeLarge({ severity }: { severity: string }) {
  const styles: Record<string, string> = {
    critical: 'bg-emerald-200 text-emerald-900',
    high: 'bg-emerald-100 text-emerald-800',
    medium: 'bg-teal-50 text-teal-700',
    low: 'bg-gray-100 text-gray-600',
  }
  return (
    <div className={`inline-flex items-center gap-1 px-2.5 py-1 rounded font-medium text-xs ${styles[severity] || styles.low}`}>
      <AlertCircle className="h-3.5 w-3.5" />
      <span className="capitalize">{severity}</span>
    </div>
  )
}

/** Fallback: status summary when full driver objects unavailable */
function DriversTabFallback({ status }: { status: ProjectStatusResponse }) {
  const { pains, goals, kpis, confirmed_drivers, total_drivers } = status.strategic!

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-brand-teal rounded-full"
            style={{ width: `${total_drivers > 0 ? (confirmed_drivers / total_drivers) * 100 : 0}%` }}
          />
        </div>
        <span className="text-[11px] text-ui-supportText whitespace-nowrap">
          {confirmed_drivers}/{total_drivers} confirmed
        </span>
      </div>

      {kpis.length > 0 && (
        <div>
          <div className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide mb-2 bg-emerald-50 text-emerald-700">
            KPIs <span className="ml-1.5 opacity-70">({kpis.length})</span>
          </div>
          <div className="space-y-2">
            {kpis.map((kpi, i) => (
              <div key={i} className="bg-ui-background rounded-lg px-3 py-2.5">
                <p className="text-[12px] text-ui-bodyText">{kpi.description}</p>
                {kpi.measurement && (
                  <p className="text-[11px] text-ui-supportText mt-0.5">{kpi.measurement}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {pains.length > 0 && (
        <div>
          <div className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide mb-2 bg-teal-50 text-teal-700">
            Business Pains <span className="ml-1.5 opacity-70">({pains.length})</span>
          </div>
          <div className="space-y-1.5">
            {pains.map((pain, i) => (
              <div key={i} className="flex items-start gap-2 bg-ui-background rounded-lg px-3 py-2.5">
                <StatusDot status={pain.status} />
                <p className="text-[12px] text-ui-bodyText">{pain.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {goals.length > 0 && (
        <div>
          <div className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wide mb-2 bg-emerald-100 text-emerald-800">
            Business Goals <span className="ml-1.5 opacity-70">({goals.length})</span>
          </div>
          <div className="space-y-1.5">
            {goals.map((goal, i) => (
              <div key={i} className="flex items-start gap-2 bg-ui-background rounded-lg px-3 py-2.5">
                <StatusDot status={goal.status} />
                <p className="text-[12px] text-ui-bodyText">{goal.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {pains.length === 0 && goals.length === 0 && kpis.length === 0 && (
        <EmptyState message="No business drivers extracted yet." />
      )}
    </div>
  )
}

// =============================================================================
// Tab 3: Market (enriched, expandable competitors & refs)
// =============================================================================

function MarketTab({
  companyInfo,
  competitors,
  status,
}: {
  companyInfo: CompanyInfo | null
  competitors: CompetitorRef[]
  status: ProjectStatusResponse | null
}) {
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  const toggleExpand = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const hasFastFacts = !!companyInfo?.fast_facts
  const hasTrends = !!companyInfo?.industry_trends
  const hasOverview = !!companyInfo?.industry_overview
  const hasCompetitors = competitors.length > 0
  const competitorItems = competitors.filter(c => c.reference_type === 'competitor')
  const designRefs = competitors.filter(c => c.reference_type === 'design_inspiration')
  const featureRefs = competitors.filter(c => c.reference_type === 'feature_inspiration')
  const hasStatusMarket = status?.market && (
    status.market.competitors.length > 0 ||
    status.market.design_refs.length > 0 ||
    status.market.constraints.length > 0
  )

  if (!hasFastFacts && !hasTrends && !hasOverview && !hasCompetitors && !hasStatusMarket) {
    return <EmptyState message="No market data available yet." />
  }

  return (
    <div className="space-y-6">
      {/* Industry Fast Facts */}
      {hasFastFacts && (
        <div>
          <SectionHeader title="Industry Fast Facts" />
          <div className="border-l-3 border-teal-400 pl-4 py-1">
            <RichContent content={companyInfo!.fast_facts!} />
          </div>
        </div>
      )}

      {/* Industry Trends */}
      {hasTrends && (
        <div>
          <SectionHeader title="Industry Trends" />
          <div className="border-l-3 border-emerald-400 pl-4 py-1">
            <RichContent content={companyInfo!.industry_trends!} />
          </div>
        </div>
      )}

      {/* Industry Overview */}
      {hasOverview && (
        <CollapsibleSection title="Industry Overview" defaultExpanded={false}>
          <RichContent content={companyInfo!.industry_overview!} />
        </CollapsibleSection>
      )}

      {/* Competitors — full objects, expandable */}
      {competitorItems.length > 0 && (
        <div>
          <SectionHeader title={`Competitors (${competitorItems.length})`} />
          <div className="grid grid-cols-2 gap-3">
            {competitorItems.map((comp) => (
              <CompetitorCard
                key={comp.id}
                competitor={comp}
                isExpanded={expandedIds.has(comp.id)}
                onToggle={() => toggleExpand(comp.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Design Inspiration — expandable */}
      {designRefs.length > 0 && (
        <div>
          <SectionHeader title={`Design Inspiration (${designRefs.length})`} />
          <div className="grid grid-cols-2 gap-3">
            {designRefs.map((ref) => (
              <ReferenceCard
                key={ref.id}
                reference={ref}
                accentClass="border-emerald-100 bg-emerald-50/50"
                isExpanded={expandedIds.has(ref.id)}
                onToggle={() => toggleExpand(ref.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Feature Inspiration — expandable */}
      {featureRefs.length > 0 && (
        <div>
          <SectionHeader title={`Feature Inspiration (${featureRefs.length})`} />
          <div className="grid grid-cols-2 gap-3">
            {featureRefs.map((ref) => (
              <ReferenceCard
                key={ref.id}
                reference={ref}
                accentClass="border-teal-100 bg-teal-50/50"
                isExpanded={expandedIds.has(ref.id)}
                onToggle={() => toggleExpand(ref.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Fallback: status-based market data when no full competitor objects */}
      {!hasCompetitors && status?.market && (
        <>
          {status.market.competitors.length > 0 && (
            <div>
              <SectionHeader title="Competitors" />
              <div className="grid grid-cols-2 gap-3">
                {status.market.competitors.map((comp, i) => (
                  <div key={i} className="bg-gray-50 rounded-lg p-3">
                    <p className="text-sm font-medium text-ui-headingDark">{comp.name}</p>
                    {comp.notes && (
                      <p className="text-[11px] text-ui-supportText mt-0.5">{comp.notes}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {status.market.design_refs.length > 0 && (
            <div>
              <SectionHeader title="Design References" />
              <div className="flex flex-wrap gap-1.5">
                {status.market.design_refs.map((ref, i) => (
                  <span key={i} className="px-2 py-0.5 text-[11px] rounded-full bg-emerald-50 text-emerald-700">
                    {ref}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Constraints */}
      {status?.market?.constraints && status.market.constraints.length > 0 && (
        <div>
          <SectionHeader title="Constraints" />
          <div className="space-y-1.5">
            {status.market.constraints.map((c, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="text-sm text-ui-bodyText">{c.name}</span>
                {c.type && (
                  <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-100 text-gray-600">{c.type}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function CompetitorCard({
  competitor: c,
  isExpanded,
  onToggle,
}: {
  competitor: CompetitorRef
  isExpanded: boolean
  onToggle: () => void
}) {
  const Chevron = isExpanded ? ChevronUp : ChevronDown
  const hasDetails = (c.strengths && c.strengths.length > 0) ||
    (c.weaknesses && c.weaknesses.length > 0) ||
    (c.features_to_study && c.features_to_study.length > 0) ||
    c.research_notes || c.notes

  return (
    <div className="bg-gray-50 rounded-lg overflow-hidden border border-gray-100">
      {/* Collapsed header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-gray-100/50 transition-colors"
      >
        <p className="flex-1 text-sm font-medium text-ui-headingDark">{c.name}</p>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {c.category && (
            <span className="px-1.5 py-0.5 text-[10px] rounded bg-gray-200 text-gray-600">{c.category}</span>
          )}
          {c.url && (
            <a
              href={c.url.startsWith('http') ? c.url : `https://${c.url}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-teal hover:text-brand-teal/80"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          {hasDetails && <Chevron className="w-3.5 h-3.5 text-ui-supportText" />}
        </div>
      </button>

      {/* Expanded details */}
      {isExpanded && hasDetails && (
        <div className="px-3 pb-3 pt-1 border-t border-gray-200 space-y-2">
          {c.strengths && c.strengths.length > 0 && (
            <div>
              <div className="text-[10px] font-medium text-emerald-700 mb-1">Strengths</div>
              <ul className="space-y-0.5">
                {c.strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                    <CheckCircle className="h-3 w-3 text-emerald-500 mt-0.5 flex-shrink-0" />
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {c.weaknesses && c.weaknesses.length > 0 && (
            <div>
              <div className="text-[10px] font-medium text-gray-500 mb-1">Weaknesses</div>
              <ul className="space-y-0.5">
                {c.weaknesses.map((w, i) => (
                  <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                    <AlertCircle className="h-3 w-3 text-gray-400 mt-0.5 flex-shrink-0" />
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {c.features_to_study && c.features_to_study.length > 0 && (
            <div>
              <div className="text-[10px] font-medium text-teal-700 mb-1">Features to Study</div>
              <div className="flex flex-wrap gap-1">
                {c.features_to_study.map((f, i) => (
                  <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-teal-50 text-teal-700 border border-teal-100">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          {(c.notes || c.research_notes) && (
            <div>
              <div className="text-[10px] font-medium text-ui-supportText mb-0.5">Notes</div>
              <p className="text-xs text-gray-600 italic">{c.notes || c.research_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ReferenceCard({
  reference: r,
  accentClass,
  isExpanded,
  onToggle,
}: {
  reference: CompetitorRef
  accentClass: string
  isExpanded: boolean
  onToggle: () => void
}) {
  const Chevron = isExpanded ? ChevronUp : ChevronDown
  const hasDetails = (r.features_to_study && r.features_to_study.length > 0) ||
    r.research_notes || r.notes

  return (
    <div className={`rounded-lg overflow-hidden border ${accentClass}`}>
      {/* Collapsed header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-white/50 transition-colors"
      >
        <p className="flex-1 text-sm font-medium text-gray-900">{r.name}</p>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {r.url && (
            <a
              href={r.url.startsWith('http') ? r.url : `https://${r.url}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-brand-teal hover:text-brand-teal/80"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          )}
          {hasDetails && <Chevron className="w-3.5 h-3.5 text-ui-supportText" />}
        </div>
      </button>

      {/* Expanded details */}
      {isExpanded && hasDetails && (
        <div className="px-3 pb-3 pt-1 border-t border-gray-200/60 space-y-2">
          {r.features_to_study && r.features_to_study.length > 0 && (
            <div>
              <div className="text-[10px] font-medium text-emerald-700 mb-1">Features to Study</div>
              <div className="flex flex-wrap gap-1">
                {r.features_to_study.map((f, i) => (
                  <span key={i} className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-50 text-emerald-700 border border-emerald-100">
                    {f}
                  </span>
                ))}
              </div>
            </div>
          )}

          {(r.notes || r.research_notes) && (
            <div>
              <div className="text-[10px] font-medium text-ui-supportText mb-0.5">Notes</div>
              <p className="text-xs text-gray-600 italic">{r.notes || r.research_notes}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Tab 4: Stakeholders (3-per-row grid)
// =============================================================================

function StakeholdersTab({ status }: { status: ProjectStatusResponse | null }) {
  if (!status?.stakeholders || status.stakeholders.items.length === 0) {
    return <EmptyState message="No stakeholders identified yet." />
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <SectionHeader title="Stakeholders" />
        <span className="text-[11px] text-ui-supportText">{status.stakeholders.total} total</span>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {status.stakeholders.items.map((s, i) => (
          <div key={i} className="bg-gray-50 rounded-lg p-3 flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-teal-50 flex items-center justify-center flex-shrink-0">
              <Users className="w-4 h-4 text-teal-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-ui-headingDark truncate">{s.name}</p>
              {s.role && <p className="text-[11px] text-ui-supportText truncate">{s.role}</p>}
            </div>
            {s.type && (
              <span className="px-1.5 py-0.5 text-[10px] rounded bg-emerald-50 text-emerald-700 flex-shrink-0">
                {s.type}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Shared sub-components
// =============================================================================

function SectionHeader({ title }: { title: string }) {
  return (
    <h5 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
      {title}
    </h5>
  )
}

function DataCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-ui-background rounded-lg p-4">
      <h4 className="text-sm font-semibold text-ui-headingDark mb-2">{title}</h4>
      {children}
    </div>
  )
}

function ConfidenceBar({ value }: { value?: number }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <div className="mt-2 flex items-center gap-2">
      <div className="flex-1 h-1 bg-gray-200 rounded-full overflow-hidden">
        <div
          className="h-full bg-brand-teal rounded-full"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] text-ui-supportText">{pct}%</span>
    </div>
  )
}

function StatusDot({ status }: { status: string | null }) {
  const isConfirmed = status?.startsWith('confirmed')
  return isConfirmed ? (
    <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
  ) : (
    <AlertCircle className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
  )
}

function InfoCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-ui-background rounded-lg px-3 py-2">
      <span className="text-[11px] text-ui-supportText">{label}</span>
      <p className="text-sm text-ui-bodyText">{value}</p>
    </div>
  )
}

/** Renders content that may be HTML or markdown at panel-appropriate size.
 *  Matches the text-sm / text-[13px] sizing used by the rest of the panel. */
function RichContent({ content }: { content: string }) {
  const looksLikeHtml = /<[a-z][\s\S]*>/i.test(content)
  if (looksLikeHtml) {
    return (
      <div
        className="max-w-none text-sm text-ui-bodyText leading-relaxed [&_h1]:text-sm [&_h1]:font-bold [&_h1]:mt-2 [&_h1]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h2]:mt-2 [&_h2]:mb-1 [&_h3]:text-sm [&_h3]:font-medium [&_h3]:mt-1.5 [&_h3]:mb-0.5 [&_p]:mb-1.5 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:list-inside [&_ul]:mb-1.5 [&_ul]:space-y-0.5 [&_ol]:list-decimal [&_ol]:list-inside [&_ol]:mb-1.5 [&_li]:ml-1 [&_a]:text-brand-teal [&_a]:underline [&_strong]:font-semibold [&_blockquote]:border-l-2 [&_blockquote]:border-gray-300 [&_blockquote]:pl-2.5 [&_blockquote]:italic [&_blockquote]:text-gray-500"
        dangerouslySetInnerHTML={{ __html: content }}
      />
    )
  }
  return (
    <Markdown
      content={content}
      className="text-sm text-ui-bodyText [&_h1]:text-sm [&_h2]:text-[13px] [&_h3]:text-[13px] [&_p]:text-sm [&_li]:text-sm"
    />
  )
}

function CollapsibleSection({
  title,
  defaultExpanded = true,
  children,
}: {
  title: string
  defaultExpanded?: boolean
  children: React.ReactNode
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded)
  const Chevron = isExpanded ? ChevronUp : ChevronDown

  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1.5 mb-2 group"
      >
        <h5 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide group-hover:text-brand-teal transition-colors">
          {title}
        </h5>
        <Chevron className="w-3.5 h-3.5 text-ui-supportText" />
      </button>
      {isExpanded && children}
    </div>
  )
}

function NotExtracted() {
  return <p className="text-sm text-ui-supportText italic">Not extracted yet</p>
}

function EmptyState({ message }: { message: string }) {
  return (
    <p className="text-sm text-ui-supportText text-center py-6">{message}</p>
  )
}
