/**
 * Strategic Context Tab
 *
 * The "big picture" view for consultants showing:
 * - Executive Summary
 * - Opportunity & Risks (side-by-side)
 * - Investment Case (adapts to project type)
 * - Stakeholder Map
 * - Success Metrics
 * - Constraints
 */

'use client'

import React, { useState, useEffect } from 'react'
import {
  Compass,
  AlertTriangle,
  Target,
  Users,
  TrendingUp,
  Clock,
  Shield,
  Check,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react'
import { EmptyState, Card, CardHeader } from '@/components/ui'

interface StrategicContextTabProps {
  projectId: string
}

interface StrategicContext {
  id: string
  project_id: string
  project_type: 'internal' | 'market_product'
  executive_summary: string | null
  opportunity: {
    problem_statement?: string
    business_opportunity?: string
    client_motivation?: string
    strategic_fit?: string
    market_gap?: string
  }
  risks: Array<{
    category: string
    description: string
    severity: 'high' | 'medium' | 'low'
    mitigation: string | null
    evidence_ids: string[]
  }>
  investment_case: Record<string, string>
  success_metrics: Array<{
    metric: string
    target: string
    current: string | null
    evidence_ids: string[]
  }>
  constraints: {
    budget?: string
    timeline?: string
    team_size?: string
    technical?: string[]
    compliance?: string[]
  }
  confirmation_status: string
  enrichment_status: string
}

interface Stakeholder {
  id: string
  name: string
  role: string | null
  organization: string | null
  stakeholder_type: 'champion' | 'sponsor' | 'blocker' | 'influencer' | 'end_user'
  influence_level: 'high' | 'medium' | 'low'
  priorities: string[]
  concerns: string[]
  confirmation_status: string
}

export function StrategicContextTab({ projectId }: StrategicContextTabProps) {
  const [context, setContext] = useState<StrategicContext | null>(null)
  const [stakeholders, setStakeholders] = useState<Stakeholder[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['opportunity', 'risks', 'stakeholders']))

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      const [contextRes, stakeholdersRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/state/strategic-context?project_id=${projectId}`),
        fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/state/stakeholders?project_id=${projectId}`),
      ])

      if (contextRes.ok) {
        const data = await contextRes.json()
        setContext(data)
      }

      if (stakeholdersRes.ok) {
        const data = await stakeholdersRes.json()
        setStakeholders(data)
      }
    } catch (error) {
      console.error('Failed to load strategic context:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev)
      if (next.has(section)) {
        next.delete(section)
      } else {
        next.add(section)
      }
      return next
    })
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'bg-red-100 text-red-800 border-red-200'
      case 'medium': return 'bg-amber-100 text-amber-800 border-amber-200'
      case 'low': return 'bg-green-100 text-green-800 border-green-200'
      default: return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  const getStakeholderTypeColor = (type: string) => {
    switch (type) {
      case 'champion': return 'bg-green-100 text-green-800'
      case 'sponsor': return 'bg-blue-100 text-blue-800'
      case 'blocker': return 'bg-red-100 text-red-800'
      case 'influencer': return 'bg-purple-100 text-purple-800'
      case 'end_user': return 'bg-gray-100 text-gray-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const getInfluenceIcon = (level: string) => {
    switch (level) {
      case 'high': return '***'
      case 'medium': return '**'
      case 'low': return '*'
      default: return ''
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!context) {
    return (
      <EmptyState
        icon={<Compass className="h-16 w-16" />}
        title="No Strategic Context Yet"
        description="Ask the AI assistant to generate strategic context from your signals and research."
        action={
          <button
            onClick={() => {
              // This would trigger the chat to run generate_strategic_context
              alert('Use the chat assistant to run: "generate strategic context"')
            }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Generate Strategic Context
          </button>
        }
      />
    )
  }

  const projectTypeLabel = context.project_type === 'internal'
    ? 'Internal Software'
    : 'Market Product'

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Header with Project Type Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Strategic Context</h2>
          <p className="text-sm text-gray-500 mt-1">Business case and stakeholder overview</p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${
            context.project_type === 'internal'
              ? 'bg-blue-100 text-blue-800'
              : 'bg-purple-100 text-purple-800'
          }`}>
            {projectTypeLabel}
          </span>
          <button
            onClick={loadData}
            className="p-2 text-gray-400 hover:text-gray-600"
            title="Refresh"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Executive Summary */}
      {context.executive_summary && (
        <Card>
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <Compass className="w-5 h-5 text-blue-600" />
                Executive Summary
              </span>
            }
          />
          <p className="text-gray-700 leading-relaxed">{context.executive_summary}</p>
        </Card>
      )}

      {/* Opportunity & Risks - Side by Side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Opportunity */}
        <Card>
          <div
            className="cursor-pointer"
            onClick={() => toggleSection('opportunity')}
          >
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-green-600" />
                  The Opportunity
                </span>
              }
              actions={expandedSections.has('opportunity') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            />
          </div>
          {expandedSections.has('opportunity') && (
            <div className="space-y-4">
              {context.opportunity.problem_statement && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-1">Problem Statement</h4>
                  <p className="text-gray-700">{context.opportunity.problem_statement}</p>
                </div>
              )}
              {context.opportunity.business_opportunity && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-1">Business Opportunity</h4>
                  <p className="text-gray-700">{context.opportunity.business_opportunity}</p>
                </div>
              )}
              {context.opportunity.client_motivation && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-1">Client Motivation</h4>
                  <p className="text-gray-700">{context.opportunity.client_motivation}</p>
                </div>
              )}
              {context.opportunity.strategic_fit && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-1">Strategic Fit</h4>
                  <p className="text-gray-700">{context.opportunity.strategic_fit}</p>
                </div>
              )}
              {context.project_type === 'market_product' && context.opportunity.market_gap && (
                <div>
                  <h4 className="text-sm font-medium text-gray-500 mb-1">Market Gap</h4>
                  <p className="text-gray-700">{context.opportunity.market_gap}</p>
                </div>
              )}
              {!context.opportunity.problem_statement && !context.opportunity.business_opportunity && (
                <p className="text-gray-400 italic">No opportunity data yet</p>
              )}
            </div>
          )}
        </Card>

        {/* Risks */}
        <Card>
          <div
            className="cursor-pointer"
            onClick={() => toggleSection('risks')}
          >
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-amber-600" />
                  Risks ({context.risks.length})
                </span>
              }
              actions={expandedSections.has('risks') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            />
          </div>
          {expandedSections.has('risks') && (
            <div>
              {context.risks.length > 0 ? (
                <div className="space-y-3">
                  {context.risks.map((risk, idx) => (
                    <div key={idx} className={`p-3 rounded-lg border ${getSeverityColor(risk.severity)}`}>
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1">
                          <span className="text-xs font-medium uppercase">{risk.category}</span>
                          <p className="text-sm mt-1">{risk.description}</p>
                          {risk.mitigation && (
                            <p className="text-xs mt-2 opacity-75">
                              <strong>Mitigation:</strong> {risk.mitigation}
                            </p>
                          )}
                        </div>
                        <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                          risk.severity === 'high' ? 'bg-red-200' :
                          risk.severity === 'medium' ? 'bg-amber-200' : 'bg-green-200'
                        }`}>
                          {risk.severity.toUpperCase()}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-400 italic">No risks identified yet</p>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Investment Case */}
      {Object.keys(context.investment_case).length > 0 && (
        <Card>
          <div
            className="cursor-pointer"
            onClick={() => toggleSection('investment')}
          >
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-indigo-600" />
                  Investment Case
                </span>
              }
              actions={expandedSections.has('investment') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            />
          </div>
          {expandedSections.has('investment') && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(context.investment_case).map(([key, value]) => (
                value && (
                  <div key={key} className="p-3 bg-gray-50 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-500 mb-1 capitalize">
                      {key.replace(/_/g, ' ')}
                    </h4>
                    <p className="text-gray-700">{value}</p>
                  </div>
                )
              ))}
            </div>
          )}
        </Card>
      )}

      {/* Stakeholders */}
      <Card>
        <div
          className="cursor-pointer"
          onClick={() => toggleSection('stakeholders')}
        >
          <CardHeader
            title={
              <span className="flex items-center gap-2">
                <Users className="w-5 h-5 text-blue-600" />
                Stakeholders ({stakeholders.length})
              </span>
            }
            actions={expandedSections.has('stakeholders') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          />
        </div>
        {expandedSections.has('stakeholders') && (
          <div>
            {stakeholders.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {stakeholders.map(sh => (
                  <div key={sh.id} className="p-4 border border-gray-200 rounded-lg bg-white">
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <h4 className="font-medium text-gray-900">{sh.name}</h4>
                        {sh.role && <p className="text-sm text-gray-500">{sh.role}</p>}
                        {sh.organization && <p className="text-xs text-gray-400">{sh.organization}</p>}
                      </div>
                      <span className="text-xs text-gray-400" title={`Influence: ${sh.influence_level}`}>
                        {getInfluenceIcon(sh.influence_level)}
                      </span>
                    </div>
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${getStakeholderTypeColor(sh.stakeholder_type)}`}>
                      {sh.stakeholder_type.replace('_', ' ')}
                    </span>
                    {sh.priorities.length > 0 && (
                      <div className="mt-3">
                        <p className="text-xs font-medium text-gray-500">Priorities:</p>
                        <ul className="text-xs text-gray-600 mt-1">
                          {sh.priorities.slice(0, 2).map((p, i) => (
                            <li key={i}>• {p}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {sh.concerns.length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs font-medium text-gray-500">Concerns:</p>
                        <ul className="text-xs text-gray-600 mt-1">
                          {sh.concerns.slice(0, 2).map((c, i) => (
                            <li key={i}>• {c}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-gray-400 italic">No stakeholders identified yet. Use the chat to run "identify stakeholders".</p>
            )}
          </div>
        )}
      </Card>

      {/* Success Metrics */}
      {context.success_metrics.length > 0 && (
        <Card>
          <div
            className="cursor-pointer"
            onClick={() => toggleSection('metrics')}
          >
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  <Check className="w-5 h-5 text-green-600" />
                  Success Metrics ({context.success_metrics.length})
                </span>
              }
              actions={expandedSections.has('metrics') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            />
          </div>
          {expandedSections.has('metrics') && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left border-b">
                    <th className="pb-2 font-medium text-gray-500">Metric</th>
                    <th className="pb-2 font-medium text-gray-500">Target</th>
                    <th className="pb-2 font-medium text-gray-500">Current</th>
                  </tr>
                </thead>
                <tbody>
                  {context.success_metrics.map((m, idx) => (
                    <tr key={idx} className="border-b last:border-0">
                      <td className="py-2 text-gray-900">{m.metric}</td>
                      <td className="py-2 text-gray-700">{m.target}</td>
                      <td className="py-2 text-gray-500">{m.current || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* Constraints */}
      {(context.constraints.budget || context.constraints.timeline ||
        context.constraints.technical?.length || context.constraints.compliance?.length) && (
        <Card>
          <div
            className="cursor-pointer"
            onClick={() => toggleSection('constraints')}
          >
            <CardHeader
              title={
                <span className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-gray-600" />
                  Constraints
                </span>
              }
              actions={expandedSections.has('constraints') ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            />
          </div>
          {expandedSections.has('constraints') && (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {context.constraints.budget && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-500 mb-1">Budget</h4>
                    <p className="text-gray-700">{context.constraints.budget}</p>
                  </div>
                )}
                {context.constraints.timeline && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-500 mb-1">Timeline</h4>
                    <p className="text-gray-700">{context.constraints.timeline}</p>
                  </div>
                )}
                {context.constraints.team_size && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <h4 className="text-sm font-medium text-gray-500 mb-1">Team Size</h4>
                    <p className="text-gray-700">{context.constraints.team_size}</p>
                  </div>
                )}
              </div>
              {((context.constraints.technical?.length ?? 0) > 0 || (context.constraints.compliance?.length ?? 0) > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                  {(context.constraints.technical?.length ?? 0) > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-500 mb-2">Technical Constraints</h4>
                      <ul className="space-y-1">
                        {context.constraints.technical?.map((c, i) => (
                          <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                            <span className="text-gray-400">•</span>
                            {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {(context.constraints.compliance?.length ?? 0) > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-500 mb-2">Compliance Requirements</h4>
                      <ul className="space-y-1">
                        {context.constraints.compliance?.map((c, i) => (
                          <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                            <span className="text-gray-400">•</span>
                            {c}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Status Footer */}
      <div className="flex items-center justify-between text-sm text-gray-500 pt-4 border-t">
        <span>
          Status: {context.confirmation_status === 'confirmed_consultant' ? (
            <span className="text-green-600">Confirmed</span>
          ) : context.confirmation_status === 'needs_client' ? (
            <span className="text-amber-600">Needs Client Review</span>
          ) : (
            <span className="text-gray-500">AI Generated</span>
          )}
        </span>
        <span>
          Enrichment: {context.enrichment_status === 'enriched' ? (
            <span className="text-green-600">Complete</span>
          ) : context.enrichment_status === 'stale' ? (
            <span className="text-amber-600">Stale</span>
          ) : (
            <span className="text-gray-500">Not enriched</span>
          )}
        </span>
      </div>
    </div>
  )
}

export default StrategicContextTab
