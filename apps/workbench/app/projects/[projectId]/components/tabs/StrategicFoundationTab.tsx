/**
 * Strategic Foundation Tab
 *
 * Central system of record for agents with 3 sub-tabs:
 * 1. Project Context - company info, stakeholders, strategic intent
 * 2. Business Drivers - KPIs, pains, goals, constraints
 * 3. References - competitors, design inspiration, creative brief
 */

'use client'

import React, { useState, useEffect } from 'react'
import {
  Building2,
  Users,
  Target,
  TrendingUp,
  AlertCircle,
  Compass,
  Sparkles,
  Loader2,
  Plus,
  ExternalLink,
  ChevronRight,
  Pencil,
  Globe,
  DollarSign,
  MapPin,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Card, CardHeader, EmptyState } from '@/components/ui'
import { updateCompanyInfo } from '@/lib/api'

interface StrategicFoundationTabProps {
  projectId: string
}

type SubTab = 'context' | 'drivers' | 'references'

// Types for new entities
interface CompanyInfo {
  id: string
  name: string
  industry: string | null
  stage: string | null
  size: string | null
  website: string | null
  description: string | null
  key_differentiators: string[]
  // Extended fields
  revenue: string | null
  address: string | null
  location: string | null
  employee_count: string | null
  // Enrichment fields
  unique_selling_point: string | null
  customers: string | null
  products_services: string | null
  industry_overview: string | null
  industry_trends: string | null
  fast_facts: string | null
  company_type: string | null
  industry_display: string | null
  industry_naics: string | null
  enrichment_source: string | null
  enrichment_confidence: number | null
  enriched_at: string | null
}

interface Stakeholder {
  id: string
  name: string
  role: string | null
  organization: string | null
  stakeholder_type: string
  influence_level: string
  is_economic_buyer: boolean
  priorities: string[]
  concerns: string[]
}

interface BusinessDriver {
  id: string
  driver_type: 'kpi' | 'pain' | 'goal'
  description: string
  measurement: string | null
  timeframe: string | null
  priority: number
  stakeholder_id: string | null
}

interface CompetitorRef {
  id: string
  reference_type: 'competitor' | 'design_inspiration' | 'feature_inspiration'
  name: string
  url: string | null
  category: string | null
  strengths: string[]
  weaknesses: string[]
  features_to_study: string[]
  research_notes: string | null
}

interface Constraint {
  id: string
  title: string
  constraint_type: string
  description: string | null
  severity?: string
}

// Strategic Context from generate_strategic_context
interface StrategicContext {
  id: string
  project_type: 'internal' | 'market_product'
  executive_summary: string | null
  opportunity: {
    problem_statement?: string
    business_opportunity?: string
    client_motivation?: string
    strategic_fit?: string
    market_gap?: string
  } | null
  risks: Array<{
    category: string
    description: string
    severity: string
    mitigation?: string
  }>
  investment_case: {
    efficiency_gains?: string
    cost_reduction?: string
    risk_mitigation?: string
    roi_estimate?: string
    roi_timeframe?: string
    // Market product fields
    tam?: string
    sam?: string
    som?: string
    revenue_projection?: string
    market_timing?: string
    competitive_advantage?: string
  } | null
  success_metrics: Array<{
    metric: string
    target: string
    current?: string
  }>
  constraints: {
    budget?: string
    timeline?: string
    team_size?: string
    technical?: string[]
    compliance?: string[]
  } | null
  confirmation_status: string
  generation_model?: string
  created_at: string
  updated_at: string
}

const subTabs = [
  { id: 'context' as SubTab, label: 'Project Context', icon: Building2 },
  { id: 'drivers' as SubTab, label: 'Business Drivers', icon: TrendingUp },
  { id: 'references' as SubTab, label: 'References', icon: Compass },
]

export function StrategicFoundationTab({ projectId }: StrategicFoundationTabProps) {
  const [activeSubTab, setActiveSubTab] = useState<SubTab>('context')
  const [loading, setLoading] = useState(true)
  const [companyInfo, setCompanyInfo] = useState<CompanyInfo | null>(null)
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([])
  const [businessDrivers, setBusinessDrivers] = useState<BusinessDriver[]>([])
  const [competitorRefs, setCompetitorRefs] = useState<CompetitorRef[]>([])
  const [constraints, setConstraints] = useState<Constraint[]>([])
  const [strategicContext, setStrategicContext] = useState<StrategicContext | null>(null)

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE

      // Load all data in parallel
      const [stakeholdersRes, constraintsRes] = await Promise.all([
        fetch(`${baseUrl}/v1/state/stakeholders?project_id=${projectId}`),
        fetch(`${baseUrl}/v1/state/constraints?project_id=${projectId}`),
      ])

      // New entity endpoints (may not exist yet, handle gracefully)
      let companyData = null
      let driversData: BusinessDriver[] = []
      let refsData: CompetitorRef[] = []
      let strategicContextData: StrategicContext | null = null

      // Fetch strategic context (from generate_strategic_context)
      try {
        const contextRes = await fetch(`${baseUrl}/v1/state/strategic-context?project_id=${projectId}`)
        if (contextRes.ok) {
          strategicContextData = await contextRes.json()
        }
      } catch (e) {
        console.log('Strategic context endpoint not available yet')
      }

      try {
        const companyRes = await fetch(`${baseUrl}/v1/state/company-info?project_id=${projectId}`)
        if (companyRes.ok) {
          const data = await companyRes.json()
          companyData = data.company_info
        }
      } catch (e) {
        console.log('Company info endpoint not available yet')
      }

      try {
        const driversRes = await fetch(`${baseUrl}/v1/state/business-drivers?project_id=${projectId}`)
        if (driversRes.ok) {
          const data = await driversRes.json()
          driversData = data.drivers || []
        }
      } catch (e) {
        console.log('Business drivers endpoint not available yet')
      }

      try {
        const refsRes = await fetch(`${baseUrl}/v1/state/competitor-refs?project_id=${projectId}`)
        if (refsRes.ok) {
          const data = await refsRes.json()
          refsData = data.references || []
        }
      } catch (e) {
        console.log('Competitor refs endpoint not available yet')
      }

      // Process responses
      if (stakeholdersRes.ok) {
        const data = await stakeholdersRes.json()
        // /state/stakeholders returns a list directly
        setStakeholders(Array.isArray(data) ? data : (data.stakeholders || []))
      }

      if (constraintsRes.ok) {
        const data = await constraintsRes.json()
        setConstraints(data.constraints || [])
      }

      setCompanyInfo(companyData)
      setBusinessDrivers(driversData)
      setCompetitorRefs(refsData)
      setStrategicContext(strategicContextData)

    } catch (error) {
      console.error('Error loading strategic foundation data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-brand-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Sub-tab Navigation */}
      <div className="border-b border-ui-cardBorder">
        <nav className="flex space-x-4 px-2">
          {subTabs.map((tab) => {
            const Icon = tab.icon
            const isActive = activeSubTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                className={`
                  flex items-center gap-2 px-3 py-2 text-sm font-medium border-b-2 transition-colors
                  ${isActive
                    ? 'border-brand-primary text-brand-primary'
                    : 'border-transparent text-ui-supportText hover:text-ui-bodyText'
                  }
                `}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Sub-tab Content */}
      {activeSubTab === 'context' && (
        <ProjectContextSubTab
          companyInfo={companyInfo}
          stakeholders={stakeholders}
          strategicContext={strategicContext}
          projectId={projectId}
          onRefresh={loadData}
        />
      )}

      {activeSubTab === 'drivers' && (
        <BusinessDriversSubTab
          drivers={businessDrivers}
          constraints={constraints}
          projectId={projectId}
        />
      )}

      {activeSubTab === 'references' && (
        <ReferencesSubTab
          references={competitorRefs}
          projectId={projectId}
        />
      )}
    </div>
  )
}

// Sub-tab Components

// HTML content card component for displaying Quill-generated content
function HtmlContentCard({
  title,
  content,
  icon: Icon,
  emptyText,
}: {
  title: string
  content: string | null
  icon: LucideIcon
  emptyText: string
}) {
  if (!content) {
    return (
      <Card>
        <CardHeader title={title} icon={Icon} />
        <div className="p-4">
          <p className="text-sm text-gray-500 italic">{emptyText}</p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader title={title} icon={Icon} />
      <div className="p-4">
        <div
          className="prose prose-sm max-w-none text-gray-700"
          dangerouslySetInnerHTML={{ __html: content }}
        />
      </div>
    </Card>
  )
}

// AI badge component following design guide
function AiBadge({ source, confidence }: { source: string | null; confidence: number | null }) {
  if (!source) return null

  return (
    <div className="flex items-center gap-2">
      <span className="inline-flex items-center px-2 py-0.5 bg-emerald-50 text-[#009b87] rounded-full text-xs font-medium">
        <Sparkles className="w-3 h-3 mr-1" />
        AI {source === 'website_scrape' ? '(Web)' : '(Inferred)'}
      </span>
      {confidence && (
        <span className="text-xs text-gray-500">
          {Math.round(confidence * 100)}% confidence
        </span>
      )}
    </div>
  )
}

function ProjectContextSubTab({
  companyInfo,
  stakeholders,
  strategicContext,
  projectId,
  onRefresh,
}: {
  companyInfo: CompanyInfo | null
  stakeholders: Stakeholder[]
  strategicContext: StrategicContext | null
  projectId: string
  onRefresh?: () => void
}) {
  const [industryTab, setIndustryTab] = useState<'overview' | 'trends'>('overview')
  const hasEnrichment = companyInfo?.enriched_at

  return (
    <div className="space-y-6">
      {/* Company Information Card - First (above Executive Summary) */}
      <CompanyInformationCard companyInfo={companyInfo} projectId={projectId} onSave={onRefresh} />

      {/* Strategic Context Overview - Show if available */}
      {strategicContext && (
        <div className="space-y-6">
          {/* Executive Summary Card */}
          <Card>
            <CardHeader title="Executive Summary" icon={Target} />
            <div className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <span className={`px-2 py-1 rounded text-xs font-medium ${
                  strategicContext.project_type === 'internal'
                    ? 'bg-blue-50 text-blue-700'
                    : 'bg-purple-50 text-purple-700'
                }`}>
                  {strategicContext.project_type === 'internal' ? 'Internal Tool' : 'Market Product'}
                </span>
                <span className="inline-flex items-center px-2 py-0.5 bg-emerald-50 text-[#009b87] rounded-full text-xs font-medium">
                  <Sparkles className="w-3 h-3 mr-1" />
                  AI Generated
                </span>
              </div>
              {strategicContext.executive_summary ? (
                <p className="text-sm text-gray-700 leading-relaxed">
                  {strategicContext.executive_summary}
                </p>
              ) : (
                <p className="text-sm text-gray-500 italic">No executive summary generated yet</p>
              )}
            </div>
          </Card>

          {/* Opportunity */}
          {strategicContext.opportunity && (
            <Card>
              <CardHeader title="Opportunity" icon={TrendingUp} />
              <div className="p-4 space-y-3">
                {strategicContext.opportunity.problem_statement && (
                  <div>
                    <div className="text-xs font-medium text-gray-500 mb-1">Problem</div>
                    <p className="text-sm text-gray-700">{strategicContext.opportunity.problem_statement}</p>
                  </div>
                )}
                {strategicContext.opportunity.business_opportunity && (
                  <div>
                    <div className="text-xs font-medium text-gray-500 mb-1">Business Opportunity</div>
                    <p className="text-sm text-gray-700">{strategicContext.opportunity.business_opportunity}</p>
                  </div>
                )}
                {strategicContext.opportunity.client_motivation && (
                  <div>
                    <div className="text-xs font-medium text-gray-500 mb-1">Why Now?</div>
                    <p className="text-sm text-gray-700">{strategicContext.opportunity.client_motivation}</p>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Stakeholders & Investment Case - Side by Side */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Stakeholders - Half Width */}
            <Card>
              <CardHeader title="Stakeholders" icon={Users} />
              <div className="p-4">
                {stakeholders.length > 0 ? (
                  <div className="space-y-3">
                    {stakeholders.map((s) => (
                      <div key={s.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                        <div className="flex-shrink-0 w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                          <Users className="h-5 w-5 text-[#009b87]" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900">{s.name}</span>
                            {s.is_economic_buyer && (
                              <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                                Decision Maker
                              </span>
                            )}
                          </div>
                          {s.role && (
                            <div className="text-sm text-gray-500">{s.role}</div>
                          )}
                          <div className="flex items-center gap-2 mt-1">
                            <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                              s.stakeholder_type === 'champion' ? 'bg-emerald-50 text-[#009b87]' :
                              s.stakeholder_type === 'sponsor' ? 'bg-emerald-100 text-emerald-700' :
                              s.stakeholder_type === 'blocker' ? 'bg-red-50 text-red-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {s.stakeholder_type}
                            </span>
                            <span className={`px-1.5 py-0.5 rounded text-xs ${
                              s.influence_level === 'high' ? 'bg-orange-50 text-orange-700' :
                              s.influence_level === 'medium' ? 'bg-yellow-50 text-yellow-700' :
                              'bg-gray-50 text-gray-600'
                            }`}>
                              {s.influence_level} influence
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<Users className="h-12 w-12" />}
                    title="No stakeholders yet"
                    description="Add a client transcript to extract stakeholder information"
                  />
                )}
              </div>
            </Card>

            {/* Investment Case - Half Width */}
            {strategicContext.investment_case && (
              <Card>
                <CardHeader title="Investment Case" icon={TrendingUp} />
                <div className="p-4 space-y-3">
                  {strategicContext.project_type === 'internal' ? (
                    <>
                      {strategicContext.investment_case.efficiency_gains && (
                        <div>
                          <div className="text-xs font-medium text-gray-500 mb-1">Efficiency Gains</div>
                          <p className="text-sm text-gray-700">{strategicContext.investment_case.efficiency_gains}</p>
                        </div>
                      )}
                      {strategicContext.investment_case.cost_reduction && (
                        <div>
                          <div className="text-xs font-medium text-gray-500 mb-1">Cost Reduction</div>
                          <p className="text-sm text-gray-700">{strategicContext.investment_case.cost_reduction}</p>
                        </div>
                      )}
                      {strategicContext.investment_case.risk_mitigation && (
                        <div>
                          <div className="text-xs font-medium text-gray-500 mb-1">Risk Mitigation</div>
                          <p className="text-sm text-gray-700">{strategicContext.investment_case.risk_mitigation}</p>
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                      {strategicContext.investment_case.competitive_advantage && (
                        <div>
                          <div className="text-xs font-medium text-gray-500 mb-1">Competitive Advantage</div>
                          <p className="text-sm text-gray-700">{strategicContext.investment_case.competitive_advantage}</p>
                        </div>
                      )}
                      {strategicContext.investment_case.market_timing && (
                        <div>
                          <div className="text-xs font-medium text-gray-500 mb-1">Market Timing</div>
                          <p className="text-sm text-gray-700">{strategicContext.investment_case.market_timing}</p>
                        </div>
                      )}
                    </>
                  )}
                </div>
              </Card>
            )}
          </div>

          {/* Risks & Success Metrics */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Risks */}
            {strategicContext.risks && strategicContext.risks.length > 0 && (
              <Card>
                <CardHeader title={`Risks (${strategicContext.risks.length})`} icon={AlertCircle} />
                <div className="p-4 space-y-2">
                  {strategicContext.risks.map((risk, idx) => (
                    <div key={idx} className="p-3 bg-gray-50 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                          risk.severity === 'high' ? 'bg-red-100 text-red-700' :
                          risk.severity === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {risk.severity}
                        </span>
                        <span className="text-xs text-gray-500 capitalize">{risk.category}</span>
                      </div>
                      <p className="text-sm text-gray-700">{risk.description}</p>
                      {risk.mitigation && (
                        <p className="text-xs text-gray-500 mt-1">
                          <span className="font-medium">Mitigation:</span> {risk.mitigation}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Success Metrics */}
            {strategicContext.success_metrics && strategicContext.success_metrics.length > 0 && (
              <Card>
                <CardHeader title={`Success Metrics (${strategicContext.success_metrics.length})`} icon={Target} />
                <div className="p-4 space-y-2">
                  {strategicContext.success_metrics.map((metric, idx) => (
                    <div key={idx} className="p-3 bg-emerald-50 rounded-lg">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-900">{metric.metric}</span>
                        <span className="text-sm text-[#009b87] font-medium">{metric.target}</span>
                      </div>
                      {metric.current && (
                        <p className="text-xs text-gray-500 mt-1">Current: {metric.current}</p>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {/* Constraints from Strategic Context */}
          {strategicContext.constraints && (
            <Card>
              <CardHeader title="Project Constraints" icon={AlertCircle} />
              <div className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {strategicContext.constraints.budget && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs font-medium text-gray-500 mb-1">Budget</div>
                      <p className="text-sm text-gray-700">{strategicContext.constraints.budget}</p>
                    </div>
                  )}
                  {strategicContext.constraints.timeline && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs font-medium text-gray-500 mb-1">Timeline</div>
                      <p className="text-sm text-gray-700">{strategicContext.constraints.timeline}</p>
                    </div>
                  )}
                  {strategicContext.constraints.team_size && (
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-xs font-medium text-gray-500 mb-1">Team Size</div>
                      <p className="text-sm text-gray-700">{strategicContext.constraints.team_size}</p>
                    </div>
                  )}
                </div>
                {strategicContext.constraints.technical && strategicContext.constraints.technical.length > 0 && (
                  <div className="mt-4">
                    <div className="text-xs font-medium text-gray-500 mb-2">Technical Constraints</div>
                    <div className="flex flex-wrap gap-2">
                      {strategicContext.constraints.technical.map((c, i) => (
                        <span key={i} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">{c}</span>
                      ))}
                    </div>
                  </div>
                )}
                {strategicContext.constraints.compliance && strategicContext.constraints.compliance.length > 0 && (
                  <div className="mt-4">
                    <div className="text-xs font-medium text-gray-500 mb-2">Compliance Requirements</div>
                    <div className="flex flex-wrap gap-2">
                      {strategicContext.constraints.compliance.map((c, i) => (
                        <span key={i} className="px-2 py-1 bg-purple-50 text-purple-700 rounded text-xs">{c}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Stakeholders Section - Show when no strategic context */}
      {!strategicContext && (
        <Card>
          <CardHeader title="Stakeholders" icon={Users} />
          <div className="p-4">
            {stakeholders.length > 0 ? (
              <div className="space-y-3">
                {stakeholders.map((s) => (
                  <div key={s.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                      <Users className="h-5 w-5 text-[#009b87]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900">{s.name}</span>
                        {s.is_economic_buyer && (
                          <span className="px-1.5 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                            Decision Maker
                          </span>
                        )}
                      </div>
                      {s.role && (
                        <div className="text-sm text-gray-500">{s.role}</div>
                      )}
                      <div className="flex items-center gap-2 mt-1">
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                          s.stakeholder_type === 'champion' ? 'bg-emerald-50 text-[#009b87]' :
                          s.stakeholder_type === 'sponsor' ? 'bg-emerald-100 text-emerald-700' :
                          s.stakeholder_type === 'blocker' ? 'bg-red-50 text-red-700' :
                          'bg-gray-100 text-gray-700'
                        }`}>
                          {s.stakeholder_type}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-xs ${
                          s.influence_level === 'high' ? 'bg-orange-50 text-orange-700' :
                          s.influence_level === 'medium' ? 'bg-yellow-50 text-yellow-700' :
                          'bg-gray-50 text-gray-600'
                        }`}>
                          {s.influence_level} influence
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<Users className="h-12 w-12" />}
                title="No stakeholders yet"
                description="Add a client transcript to extract stakeholder information"
              />
            )}
          </div>
        </Card>
      )}

      {/* Enrichment Section - Only show if company has been enriched */}
      {hasEnrichment && (
        <>
          {/* Products & Customers Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <HtmlContentCard
              title="Target Customers"
              content={companyInfo?.customers || null}
              icon={Users}
              emptyText="No customer information available"
            />
            <HtmlContentCard
              title="Products & Services"
              content={companyInfo?.products_services || null}
              icon={Building2}
              emptyText="No product information available"
            />
          </div>

          {/* Industry Card with Tabs */}
          {(companyInfo?.industry_overview || companyInfo?.industry_trends) && (
            <Card>
              <div className="flex items-center justify-between p-4 border-b border-gray-200">
                <div className="flex items-center gap-2">
                  <Compass className="h-5 w-5 text-[#778191]" />
                  <h3 className="text-lg font-semibold text-gray-900">Industry Context</h3>
                </div>
                <div className="flex border border-gray-300 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setIndustryTab('overview')}
                    className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                      industryTab === 'overview'
                        ? 'bg-[#009b87] text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Overview
                  </button>
                  <button
                    onClick={() => setIndustryTab('trends')}
                    className={`px-3 py-1.5 text-sm font-medium transition-colors border-l border-gray-300 ${
                      industryTab === 'trends'
                        ? 'bg-[#009b87] text-white'
                        : 'bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    Trends
                  </button>
                </div>
              </div>
              <div className="p-4">
                {industryTab === 'overview' && companyInfo?.industry_overview && (
                  <div
                    className="prose prose-sm max-w-none text-gray-700"
                    dangerouslySetInnerHTML={{ __html: companyInfo.industry_overview }}
                  />
                )}
                {industryTab === 'trends' && companyInfo?.industry_trends && (
                  <div
                    className="prose prose-sm max-w-none text-gray-700"
                    dangerouslySetInnerHTML={{ __html: companyInfo.industry_trends }}
                  />
                )}
                {!companyInfo?.industry_overview && !companyInfo?.industry_trends && (
                  <p className="text-sm text-gray-500 italic">No industry information available</p>
                )}
              </div>
            </Card>
          )}

          {/* Fast Facts Card */}
          {companyInfo?.fast_facts && (
            <HtmlContentCard
              title="Market Fast Facts"
              content={companyInfo.fast_facts}
              icon={TrendingUp}
              emptyText="No market facts available"
            />
          )}
        </>
      )}
    </div>
  )
}

function BusinessDriversSubTab({
  drivers,
  constraints,
  projectId,
}: {
  drivers: BusinessDriver[]
  constraints: Constraint[]
  projectId: string
}) {
  const kpis = drivers.filter(d => d.driver_type === 'kpi')
  const pains = drivers.filter(d => d.driver_type === 'pain')
  const goals = drivers.filter(d => d.driver_type === 'goal')

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* KPIs */}
      <Card>
        <CardHeader title="KPIs" icon={Target} />
        <div className="p-4">
          {kpis.length > 0 ? (
            <div className="space-y-3">
              {kpis.map((kpi) => (
                <div key={kpi.id} className="p-3 bg-green-50 rounded-lg border border-green-100">
                  <div className="font-medium text-green-900">{kpi.description}</div>
                  {kpi.measurement && (
                    <div className="text-sm text-green-700 mt-1">
                      Target: {kpi.measurement}
                    </div>
                  )}
                  {kpi.timeframe && (
                    <div className="text-xs text-green-600 mt-1">{kpi.timeframe}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Target className="h-12 w-12" />}
              title="No KPIs defined"
              description="Extract from client discussions"
            />
          )}
        </div>
      </Card>

      {/* Pain Points */}
      <Card>
        <CardHeader title="Pain Points" icon={AlertCircle} />
        <div className="p-4">
          {pains.length > 0 ? (
            <div className="space-y-3">
              {pains.map((pain) => (
                <div key={pain.id} className="p-3 bg-red-50 rounded-lg border border-red-100">
                  <div className="font-medium text-red-900">{pain.description}</div>
                  {pain.measurement && (
                    <div className="text-sm text-red-700 mt-1">
                      Impact: {pain.measurement}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<AlertCircle className="h-12 w-12" />}
              title="No pain points defined"
              description="Extract from client discussions"
            />
          )}
        </div>
      </Card>

      {/* Goals */}
      <Card>
        <CardHeader title="Goals" icon={Sparkles} />
        <div className="p-4">
          {goals.length > 0 ? (
            <div className="space-y-3">
              {goals.map((goal) => (
                <div key={goal.id} className="p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                  <div className="font-medium text-gray-900">{goal.description}</div>
                  {goal.timeframe && (
                    <div className="text-xs text-[#009b87] mt-1">{goal.timeframe}</div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Sparkles className="h-12 w-12" />}
              title="No goals defined"
              description="Extract from client discussions"
            />
          )}
        </div>
      </Card>

      {/* Constraints - Full Width */}
      <div className="lg:col-span-3">
        <Card>
          <CardHeader title="Constraints & Guardrails" icon={AlertCircle} />
          <div className="p-4">
            {constraints.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {constraints.map((c) => (
                  <div key={c.id} className="p-3 bg-ui-background rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="px-1.5 py-0.5 bg-gray-200 text-gray-700 rounded text-xs font-medium">
                        {c.constraint_type}
                      </span>
                      {c.severity && c.severity !== 'should_have' && (
                        <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                          c.severity === 'must_have'
                            ? 'bg-red-100 text-red-700'
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {c.severity.replace('_', ' ')}
                        </span>
                      )}
                    </div>
                    <div className="font-medium text-ui-headingDark">{c.title}</div>
                    {c.description && (
                      <div className="text-sm text-ui-supportText mt-1 line-clamp-2">{c.description}</div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<AlertCircle className="h-12 w-12" />}
                title="No constraints defined"
                description="Add budget, timeline, or technical constraints"
              />
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

function ReferencesSubTab({
  references,
  projectId,
}: {
  references: CompetitorRef[]
  projectId: string
}) {
  const competitors = references.filter(r => r.reference_type === 'competitor')
  const designRefs = references.filter(r => r.reference_type === 'design_inspiration')
  const featureRefs = references.filter(r => r.reference_type === 'feature_inspiration')

  return (
    <div className="space-y-6">
      {/* Competitors */}
      <Card>
        <CardHeader title="Competitors" icon={Target} />
        <div className="p-4">
          {competitors.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {competitors.map((c) => (
                <div key={c.id} className="p-4 bg-ui-background rounded-lg border border-ui-cardBorder">
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-ui-headingDark">{c.name}</span>
                    {c.url && (
                      <a href={c.url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-4 w-4 text-ui-supportText hover:text-brand-primary" />
                      </a>
                    )}
                  </div>
                  {c.category && (
                    <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                      {c.category}
                    </span>
                  )}
                  {c.strengths.length > 0 && (
                    <div className="mt-3">
                      <div className="text-xs font-medium text-green-700 mb-1">Strengths</div>
                      <ul className="text-sm text-ui-bodyText list-disc list-inside">
                        {c.strengths.slice(0, 3).map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {c.weaknesses.length > 0 && (
                    <div className="mt-2">
                      <div className="text-xs font-medium text-red-700 mb-1">Weaknesses</div>
                      <ul className="text-sm text-ui-bodyText list-disc list-inside">
                        {c.weaknesses.slice(0, 3).map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Target className="h-12 w-12" />}
              title="No competitors added"
              description="Mention competitors in client conversations to extract them"
            />
          )}
        </div>
      </Card>

      {/* Design Inspiration */}
      <Card>
        <CardHeader title="Design Inspiration" icon={Sparkles} />
        <div className="p-4">
          {designRefs.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {designRefs.map((d) => (
                <div key={d.id} className="p-3 bg-purple-50 rounded-lg border border-purple-100">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-purple-900">{d.name}</span>
                    {d.url && (
                      <a href={d.url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-4 w-4 text-purple-500 hover:text-purple-700" />
                      </a>
                    )}
                  </div>
                  {d.features_to_study.length > 0 && (
                    <div className="mt-2 text-sm text-purple-700">
                      Study: {d.features_to_study.slice(0, 2).join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Sparkles className="h-12 w-12" />}
              title="No design references"
              description="Reference products like 'make it feel like Linear' to add inspiration"
            />
          )}
        </div>
      </Card>

      {/* Feature Inspiration */}
      {featureRefs.length > 0 && (
        <Card>
          <CardHeader title="Feature Inspiration" icon={Compass} />
          <div className="p-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {featureRefs.map((f) => (
                <div key={f.id} className="p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-gray-900">{f.name}</span>
                    {f.url && (
                      <a href={f.url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-4 w-4 text-[#009b87] hover:text-[#007a6b]" />
                      </a>
                    )}
                  </div>
                  {f.features_to_study.length > 0 && (
                    <div className="mt-2 text-sm text-[#009b87]">
                      Features: {f.features_to_study.slice(0, 2).join(', ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

/**
 * Company Information Card
 * Editable card matching the design with grid layout for company details
 */
function CompanyInformationCard({
  companyInfo,
  projectId,
  onSave,
}: {
  companyInfo: CompanyInfo | null
  projectId: string
  onSave?: () => void
}) {
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState<Partial<CompanyInfo> & { city?: string; state?: string; country?: string }>({})

  // Parse location into city, state, country
  const parseLocation = (location: string | null) => {
    if (!location) return { city: '', state: '', country: '' }
    const parts = location.split(',').map((p) => p.trim())
    return {
      city: parts[0] || '',
      state: parts[1] || '',
      country: parts[2] || '',
    }
  }

  // Initialize edit data when entering edit mode
  const handleEdit = () => {
    const locationParts = parseLocation(companyInfo?.location || null)
    if (companyInfo) {
      setEditData({
        company_type: companyInfo.company_type || companyInfo.stage,
        size: companyInfo.size,
        employee_count: companyInfo.employee_count,
        industry: companyInfo.industry_display || companyInfo.industry,
        website: companyInfo.website,
        revenue: companyInfo.revenue,
        address: companyInfo.address,
        location: companyInfo.location,
        description: companyInfo.description,
        city: locationParts.city,
        state: locationParts.state,
        country: locationParts.country,
      })
    } else {
      setEditData({
        city: '',
        state: '',
        country: '',
      })
    }
    setIsEditing(true)
  }

  const handleSave = async () => {
    try {
      // Combine city, state, country into location string
      const locationParts = [editData.city, editData.state, editData.country].filter(Boolean)
      const combinedLocation = locationParts.length > 0 ? locationParts.join(', ') : null

      const { city, state, country, ...dataToSave } = editData

      // Validate company_type against allowed values
      const validCompanyTypes = ['Startup', 'SMB', 'Enterprise', 'Agency', 'Government', 'Non-Profit']
      const companyType = dataToSave.company_type && validCompanyTypes.includes(dataToSave.company_type)
        ? dataToSave.company_type
        : null

      await updateCompanyInfo(projectId, {
        ...dataToSave,
        company_type: companyType,
        location: combinedLocation,
      })

      setIsEditing(false)
      // Refresh data from parent
      onSave?.()
    } catch (error) {
      console.error('Failed to save company info:', error)
    }
  }

  const handleCancel = () => {
    setIsEditing(false)
    setEditData({})
  }

  // Helper to get company type display
  const getCompanyTypeDisplay = () => {
    const type = companyInfo?.company_type || companyInfo?.stage
    const size = companyInfo?.employee_count || companyInfo?.size
    if (type && size) {
      return `${type} ${size}`
    }
    return type || size || 'Not specified'
  }

  return (
    <Card>
      <div className="flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-emerald-50 rounded-lg">
            <Building2 className="h-4 w-4 text-[#009b87]" />
          </div>
          <h3 className="text-sm font-semibold text-gray-900">Company Information</h3>
        </div>
        {!isEditing ? (
          <button
            onClick={handleEdit}
            className="flex items-center gap-1.5 px-2.5 py-1 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
          >
            <Pencil className="h-3.5 w-3.5" />
            Edit
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={handleCancel}
              className="px-2.5 py-1 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-md transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-2.5 py-1 text-xs text-white bg-[#009b87] hover:bg-[#007a6b] rounded-md transition-colors"
            >
              Save
            </button>
          </div>
        )}
      </div>

      <div className="px-4 pb-4 pt-2 border-t border-gray-100">
        {companyInfo || isEditing ? (
          <div className="space-y-3">
            {/* Row 1: Company Type, Industry, Website */}
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Company Type</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={editData.company_type || ''}
                    onChange={(e) => setEditData({ ...editData, company_type: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none"
                    placeholder="e.g., SMB"
                  />
                ) : (
                  <p className="text-sm text-gray-900">{getCompanyTypeDisplay()}</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Industry</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={editData.industry || ''}
                    onChange={(e) => setEditData({ ...editData, industry: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none"
                    placeholder="e.g., Consulting"
                  />
                ) : (
                  <p className="text-sm text-gray-900">
                    {companyInfo?.industry_display || companyInfo?.industry || 'Not specified'}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-500 mb-1">Website</label>
                {isEditing ? (
                  <input
                    type="url"
                    value={editData.website || ''}
                    onChange={(e) => setEditData({ ...editData, website: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none"
                    placeholder="https://example.com"
                  />
                ) : companyInfo?.website ? (
                  <a
                    href={companyInfo.website.startsWith('http') ? companyInfo.website : `https://${companyInfo.website}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-[#009b87] hover:underline"
                  >
                    {companyInfo.website.replace(/^https?:\/\//, '')}
                  </a>
                ) : (
                  <p className="text-sm text-gray-400">Not specified</p>
                )}
              </div>
            </div>

            {/* Row 2: Revenue */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Revenue</label>
              {isEditing ? (
                <input
                  type="text"
                  value={editData.revenue || ''}
                  onChange={(e) => setEditData({ ...editData, revenue: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none"
                  placeholder="e.g., $1M - $10M"
                />
              ) : (
                <p className="text-sm text-gray-900">
                  {companyInfo?.revenue || 'Not specified'}
                </p>
              )}
            </div>

            {/* Row 3: Address */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Address</label>
              {isEditing ? (
                <input
                  type="text"
                  value={editData.address || ''}
                  onChange={(e) => setEditData({ ...editData, address: e.target.value })}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none"
                  placeholder="Full street address"
                />
              ) : (
                <p className="text-sm text-gray-900">
                  {companyInfo?.address || 'Not specified'}
                </p>
              )}
            </div>

            {/* Row 4: Location (City, State, Country) */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Location</label>
              {isEditing ? (
                <div className="grid grid-cols-3 gap-4">
                  <input
                    type="text"
                    value={editData.city || ''}
                    onChange={(e) => setEditData({ ...editData, city: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none"
                    placeholder="City"
                  />
                  <input
                    type="text"
                    value={editData.state || ''}
                    onChange={(e) => setEditData({ ...editData, state: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none"
                    placeholder="State"
                  />
                  <input
                    type="text"
                    value={editData.country || ''}
                    onChange={(e) => setEditData({ ...editData, country: e.target.value })}
                    className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none"
                    placeholder="Country"
                  />
                </div>
              ) : (
                <p className="text-sm text-gray-900">
                  {companyInfo?.location || 'Not specified'}
                </p>
              )}
            </div>

            {/* Row 5: Company Overview */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Company Overview</label>
              {isEditing ? (
                <textarea
                  value={editData.description || ''}
                  onChange={(e) => setEditData({ ...editData, description: e.target.value })}
                  rows={3}
                  className="w-full px-2.5 py-1.5 text-sm border border-gray-200 rounded-md focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87] outline-none resize-none"
                  placeholder="Company description and overview..."
                />
              ) : (
                <p className="text-sm text-gray-700 leading-relaxed">
                  {companyInfo?.description || companyInfo?.unique_selling_point || 'No company overview available.'}
                </p>
              )}
            </div>
          </div>
        ) : (
          <EmptyState
            icon={<Building2 className="h-10 w-10" />}
            title="No company info yet"
            description="Add a client transcript to extract company details"
          />
        )}
      </div>
    </Card>
  )
}
