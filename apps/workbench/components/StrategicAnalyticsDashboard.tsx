/**
 * Strategic Analytics Dashboard
 *
 * Displays comprehensive analytics for strategic foundation entities:
 * - Entity counts by type
 * - Enrichment status distribution
 * - Confirmation status breakdown
 * - Source signal coverage
 * - Actionable recommendations
 */

'use client'

import React, { useState, useEffect } from 'react'
import {
  BarChart3,
  CheckCircle,
  Loader2,
  TrendingUp,
  AlertCircle,
  Target,
  Users,
  Zap,
  FileText,
  Sparkles,
} from 'lucide-react'
import { Card, CardHeader } from '@/components/ui'

interface EntityCounts {
  business_drivers: number
  kpis: number
  pains: number
  goals: number
  competitor_refs: number
  stakeholders: number
  risks: number
  total: number
}

interface EnrichmentStats {
  enriched: number
  none: number
  failed: number
  enrichment_rate: number
  avg_evidence_per_entity: number
}

interface ConfirmationStats {
  confirmed_client: number
  confirmed_consultant: number
  ai_generated: number
  needs_confirmation: number
  confirmation_rate: number
}

interface SourceCoverage {
  entities_with_sources: number
  total_entities: number
  coverage_rate: number
  avg_sources_per_entity: number
  top_source_signals: Array<{
    signal_id: string
    entity_count: number
  }>
}

interface StrategicAnalytics {
  entity_counts: EntityCounts
  enrichment_stats: EnrichmentStats
  confirmation_stats: ConfirmationStats
  source_coverage: SourceCoverage
  recent_activity: any[]
  recommendations: string[]
}

interface StrategicAnalyticsDashboardProps {
  projectId: string
}

export function StrategicAnalyticsDashboard({
  projectId,
}: StrategicAnalyticsDashboardProps) {
  const [analytics, setAnalytics] = useState<StrategicAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadAnalytics()
  }, [projectId])

  const loadAnalytics = async () => {
    try {
      setLoading(true)
      setError(null)
      const baseUrl = process.env.NEXT_PUBLIC_API_BASE
      const res = await fetch(
        `${baseUrl}/v1/projects/${projectId}/strategic-analytics`
      )

      if (!res.ok) throw new Error('Failed to load analytics')

      const data = await res.json()
      setAnalytics(data)
    } catch (err) {
      console.error('Error loading analytics:', err)
      setError('Failed to load analytics')
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

  if (error || !analytics) {
    return (
      <div className="p-8 text-center">
        <AlertCircle className="h-12 w-12 mx-auto text-red-400 mb-3" />
        <p className="text-sm text-gray-500">{error || 'No analytics available'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Entities */}
        <Card>
          <div className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Entities</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {analytics.entity_counts.total}
                </p>
              </div>
              <div className="p-3 bg-emerald-50 rounded-lg">
                <BarChart3 className="h-6 w-6 text-[#009b87]" />
              </div>
            </div>
          </div>
        </Card>

        {/* Enrichment Rate */}
        <Card>
          <div className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Enriched</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {Math.round(analytics.enrichment_stats.enrichment_rate * 100)}%
                </p>
              </div>
              <div className="p-3 bg-blue-50 rounded-lg">
                <Sparkles className="h-6 w-6 text-blue-600" />
              </div>
            </div>
            <div className="mt-2">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all"
                  style={{
                    width: `${analytics.enrichment_stats.enrichment_rate * 100}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Confirmation Rate */}
        <Card>
          <div className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Confirmed</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {Math.round(analytics.confirmation_stats.confirmation_rate * 100)}%
                </p>
              </div>
              <div className="p-3 bg-green-50 rounded-lg">
                <CheckCircle className="h-6 w-6 text-green-600" />
              </div>
            </div>
            <div className="mt-2">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-green-600 h-2 rounded-full transition-all"
                  style={{
                    width: `${analytics.confirmation_stats.confirmation_rate * 100}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </Card>

        {/* Source Coverage */}
        <Card>
          <div className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Source Coverage</p>
                <p className="text-2xl font-bold text-gray-900 mt-1">
                  {Math.round(analytics.source_coverage.coverage_rate * 100)}%
                </p>
              </div>
              <div className="p-3 bg-purple-50 rounded-lg">
                <FileText className="h-6 w-6 text-purple-600" />
              </div>
            </div>
            <div className="mt-2">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-purple-600 h-2 rounded-full transition-all"
                  style={{
                    width: `${analytics.source_coverage.coverage_rate * 100}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Entity Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Entity Counts */}
        <Card>
          <CardHeader title="Entity Distribution" icon={BarChart3} />
          <div className="p-4">
            <div className="space-y-3">
              <EntityCountBar
                label="Business Drivers"
                count={analytics.entity_counts.business_drivers}
                total={analytics.entity_counts.total}
                color="bg-emerald-500"
                icon={<TrendingUp className="h-4 w-4" />}
                breakdown={`${analytics.entity_counts.kpis} KPIs, ${analytics.entity_counts.pains} Pains, ${analytics.entity_counts.goals} Goals`}
              />
              <EntityCountBar
                label="Stakeholders"
                count={analytics.entity_counts.stakeholders}
                total={analytics.entity_counts.total}
                color="bg-blue-500"
                icon={<Users className="h-4 w-4" />}
              />
              <EntityCountBar
                label="Competitors"
                count={analytics.entity_counts.competitor_refs}
                total={analytics.entity_counts.total}
                color="bg-purple-500"
                icon={<Target className="h-4 w-4" />}
              />
              <EntityCountBar
                label="Risks"
                count={analytics.entity_counts.risks}
                total={analytics.entity_counts.total}
                color="bg-red-500"
                icon={<AlertCircle className="h-4 w-4" />}
              />
            </div>
          </div>
        </Card>

        {/* Enrichment Status */}
        <Card>
          <CardHeader title="Enrichment Status" icon={Sparkles} />
          <div className="p-4">
            <div className="space-y-3">
              <StatusBar
                label="Enriched"
                count={analytics.enrichment_stats.enriched}
                total={analytics.entity_counts.total}
                color="bg-emerald-500"
              />
              <StatusBar
                label="Not Enriched"
                count={analytics.enrichment_stats.none}
                total={analytics.entity_counts.total}
                color="bg-gray-400"
              />
              {analytics.enrichment_stats.failed > 0 && (
                <StatusBar
                  label="Failed"
                  count={analytics.enrichment_stats.failed}
                  total={analytics.entity_counts.total}
                  color="bg-red-500"
                />
              )}
            </div>

            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Avg Evidence per Entity</span>
                <span className="font-medium text-gray-900">
                  {analytics.enrichment_stats.avg_evidence_per_entity}
                </span>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Confirmation Status */}
      <Card>
        <CardHeader title="Confirmation Status" icon={CheckCircle} />
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <ConfirmationBadge
              label="Client Confirmed"
              count={analytics.confirmation_stats.confirmed_client}
              color="bg-green-100 text-green-700"
            />
            <ConfirmationBadge
              label="Consultant Confirmed"
              count={analytics.confirmation_stats.confirmed_consultant}
              color="bg-blue-100 text-blue-700"
            />
            <ConfirmationBadge
              label="AI Generated"
              count={analytics.confirmation_stats.ai_generated}
              color="bg-purple-100 text-purple-700"
            />
            <ConfirmationBadge
              label="Needs Confirmation"
              count={analytics.confirmation_stats.needs_confirmation}
              color="bg-orange-100 text-orange-700"
            />
          </div>
        </div>
      </Card>

      {/* Recommendations */}
      {analytics.recommendations.length > 0 && (
        <Card>
          <CardHeader title="Recommendations" icon={Zap} />
          <div className="p-4">
            <div className="space-y-2">
              {analytics.recommendations.map((rec, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-3 p-3 bg-amber-50 border border-amber-200 rounded-lg"
                >
                  <AlertCircle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <p className="text-sm text-amber-900">{rec}</p>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}

// Helper Components

function EntityCountBar({
  label,
  count,
  total,
  color,
  icon,
  breakdown,
}: {
  label: string
  count: number
  total: number
  color: string
  icon: React.ReactNode
  breakdown?: string
}) {
  const percentage = total > 0 ? (count / total) * 100 : 0

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center gap-2">
          <div className="text-gray-500">{icon}</div>
          <span className="text-sm font-medium text-gray-700">{label}</span>
        </div>
        <span className="text-sm font-bold text-gray-900">{count}</span>
      </div>
      {breakdown && (
        <div className="text-xs text-gray-500 mb-1 ml-6">{breakdown}</div>
      )}
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

function StatusBar({
  label,
  count,
  total,
  color,
}: {
  label: string
  count: number
  total: number
  color: string
}) {
  const percentage = total > 0 ? (count / total) * 100 : 0

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm text-gray-500">
          {count} ({Math.round(percentage)}%)
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}

function ConfirmationBadge({
  label,
  count,
  color,
}: {
  label: string
  count: number
  color: string
}) {
  return (
    <div className={`p-4 rounded-lg ${color}`}>
      <div className="text-sm font-medium mb-1">{label}</div>
      <div className="text-2xl font-bold">{count}</div>
    </div>
  )
}
