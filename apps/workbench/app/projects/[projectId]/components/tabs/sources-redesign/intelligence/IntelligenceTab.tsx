/**
 * IntelligenceTab Component
 *
 * AI transparency dashboard showing:
 * - Stats grid (entities enriched, connections inferred)
 * - Evidence quality breakdown
 * - AI activity feed
 * - Suggested sources
 */

'use client'

import {
  Sparkles,
  Lightbulb,
  TrendingUp,
  AlertTriangle,
  FilePlus,
  type LucideIcon,
} from 'lucide-react'
import type { EvidenceQualityResponse } from '@/lib/api'

interface IntelligenceTabProps {
  evidenceQuality: EvidenceQualityResponse | null
  isLoading: boolean
}

export function IntelligenceTab({ evidenceQuality, isLoading }: IntelligenceTabProps) {
  if (isLoading) {
    return (
      <div className="space-y-6">
        {/* Stats skeleton */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-gray-50 rounded-xl p-4 animate-pulse">
              <div className="h-8 w-8 bg-gray-200 rounded-lg mb-3" />
              <div className="h-6 bg-gray-200 rounded w-1/2 mb-1" />
              <div className="h-3 bg-gray-100 rounded w-2/3" />
            </div>
          ))}
        </div>

        {/* Quality skeleton */}
        <div className="bg-gray-50 rounded-xl p-6 animate-pulse">
          <div className="h-5 bg-gray-200 rounded w-1/4 mb-4" />
          <div className="space-y-3">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-6 bg-gray-100 rounded" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* AI Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard
          icon={Sparkles}
          label="Entities Enriched"
          value={evidenceQuality?.total_entities || 0}
          color="violet"
        />
        <StatCard
          icon={Lightbulb}
          label="AI Generated"
          value={evidenceQuality?.breakdown.ai_generated.count || 0}
          color="amber"
        />
        <StatCard
          icon={TrendingUp}
          label="Strong Evidence"
          value={`${evidenceQuality?.strong_evidence_percentage || 0}%`}
          color="emerald"
        />
        <StatCard
          icon={AlertTriangle}
          label="Needs Review"
          value={evidenceQuality?.breakdown.needs_client.count || 0}
          color="orange"
        />
      </div>

      {/* Evidence Quality Section */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Evidence Quality</h3>

        {evidenceQuality && (
          <div className="space-y-4">
            {/* Summary callout */}
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <p className="text-sm text-gray-700">{evidenceQuality.summary}</p>
            </div>

            {/* Progress bars */}
            <div className="space-y-3">
              <QualityBar
                label="Client Verified"
                count={evidenceQuality.breakdown.confirmed_client.count}
                percentage={evidenceQuality.breakdown.confirmed_client.percentage}
                color="bg-emerald-500"
              />
              <QualityBar
                label="Consultant Verified"
                count={evidenceQuality.breakdown.confirmed_consultant.count}
                percentage={evidenceQuality.breakdown.confirmed_consultant.percentage}
                color="bg-emerald-400"
              />
              <QualityBar
                label="Needs Client Review"
                count={evidenceQuality.breakdown.needs_client.count}
                percentage={evidenceQuality.breakdown.needs_client.percentage}
                color="bg-amber-400"
              />
              <QualityBar
                label="AI Generated"
                count={evidenceQuality.breakdown.ai_generated.count}
                percentage={evidenceQuality.breakdown.ai_generated.percentage}
                color="bg-gray-300"
              />
            </div>
          </div>
        )}
      </div>

      {/* Suggested Sources (placeholder) */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Suggested Sources</h3>
          <button className="text-sm font-medium text-brand-primary hover:text-brand-primaryHover">
            Generate Suggestions
          </button>
        </div>

        <div className="flex flex-col items-center justify-center py-8 text-center">
          <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-3">
            <FilePlus className="w-6 h-6 text-gray-400" />
          </div>
          <p className="text-sm text-gray-500 max-w-sm">
            Run the DI Agent analysis to get AI-powered suggestions for
            documents that could strengthen your project evidence.
          </p>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: LucideIcon
  label: string
  value: number | string
  color: 'violet' | 'amber' | 'emerald' | 'orange'
}) {
  const colorClasses = {
    violet: 'bg-violet-50 text-violet-600',
    amber: 'bg-amber-50 text-amber-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    orange: 'bg-orange-50 text-orange-600',
  }

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className={`w-10 h-10 rounded-lg ${colorClasses[color]} flex items-center justify-center mb-3`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="text-2xl font-bold text-gray-900">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  )
}

function QualityBar({
  label,
  count,
  percentage,
  color,
}: {
  label: string
  count: number
  percentage: number
  color: string
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-gray-700">{label}</span>
        <span className="text-sm font-medium text-gray-900">
          {count} ({percentage}%)
        </span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-2 ${color} rounded-full transition-all duration-500`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
