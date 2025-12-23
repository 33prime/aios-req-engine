/**
 * InsightsList Component
 *
 * Left column: Selectable list of insights
 * - Shows title, severity, gate
 * - Filterable by severity and gate
 * - Status indicator
 */

'use client'

import React, { useState } from 'react'
import { ListItem, EmptyState } from '@/components/ui'
import { SeverityBadge, GateBadge } from '@/components/ui/StatusBadge'
import { AlertCircle, Filter } from 'lucide-react'
import type { Insight } from '@/types/api'

interface InsightsListProps {
  insights: Insight[]
  selectedId: string | null
  onSelect: (insight: Insight) => void
}

type SeverityType = 'minor' | 'important' | 'critical'
type GateType = 'completeness' | 'validation' | 'assumption' | 'scope' | 'wow'

export function InsightsList({ insights, selectedId, onSelect }: InsightsListProps) {
  const [severityFilter, setSeverityFilter] = useState<SeverityType | null>(null)
  const [gateFilter, setGateFilter] = useState<GateType | null>(null)

  // Filter insights
  let filteredInsights = insights
  if (severityFilter) {
    filteredInsights = filteredInsights.filter(i => i.severity === severityFilter)
  }
  if (gateFilter) {
    filteredInsights = filteredInsights.filter(i => i.gate === gateFilter)
  }

  // Count by severity
  const severityCounts = insights.reduce((acc, i) => {
    acc[i.severity] = (acc[i.severity] || 0) + 1
    return acc
  }, {} as Record<SeverityType, number>)

  // Count by gate
  const gateCounts = insights.reduce((acc, i) => {
    acc[i.gate] = (acc[i.gate] || 0) + 1
    return acc
  }, {} as Record<GateType, number>)

  if (insights.length === 0) {
    return (
      <EmptyState
        icon={<AlertCircle className="h-12 w-12" />}
        title="No Insights"
        description="Run the Red Team agent to generate gap analysis insights."
      />
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h2 className="heading-2 mb-2">Red Team Insights</h2>
        <p className="text-support text-ui-supportText mb-4">
          {filteredInsights.length} of {insights.length} insights
        </p>

        {/* Severity Filter */}
        <div className="mb-3">
          <div className="text-xs font-medium text-ui-supportText mb-2">Severity</div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setSeverityFilter(null)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                severityFilter === null
                  ? 'bg-brand-primary text-white'
                  : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
              }`}
            >
              All
            </button>
            {(['critical', 'important', 'minor'] as SeverityType[]).map((severity) => (
              <button
                key={severity}
                onClick={() => setSeverityFilter(severityFilter === severity ? null : severity)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  severityFilter === severity
                    ? 'bg-brand-primary text-white'
                    : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
                }`}
              >
                {severity} ({severityCounts[severity] || 0})
              </button>
            ))}
          </div>
        </div>

        {/* Gate Filter */}
        <div>
          <div className="text-xs font-medium text-ui-supportText mb-2">Gate</div>
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => setGateFilter(null)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                gateFilter === null
                  ? 'bg-brand-primary text-white'
                  : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
              }`}
            >
              All
            </button>
            {(['completeness', 'validation', 'assumption', 'scope', 'wow'] as GateType[]).map((gate) => (
              <button
                key={gate}
                onClick={() => setGateFilter(gateFilter === gate ? null : gate)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  gateFilter === gate
                    ? 'bg-brand-primary text-white'
                    : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
                }`}
              >
                {gate} ({gateCounts[gate] || 0})
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Insights List */}
      <div className="space-y-2">
        {filteredInsights.map((insight) => (
          <ListItem
            key={insight.id}
            title={insight.title}
            subtitle={insight.finding}
            meta={
              <div className="flex items-center gap-2 mt-2">
                <GateBadge gate={insight.gate} />
                {insight.targets.length > 0 && (
                  <span className="text-xs text-ui-supportText">
                    {insight.targets.length} target{insight.targets.length !== 1 ? 's' : ''}
                  </span>
                )}
              </div>
            }
            badge={<SeverityBadge severity={insight.severity} />}
            active={insight.id === selectedId}
            onClick={() => onSelect(insight)}
          />
        ))}
      </div>

      {filteredInsights.length === 0 && (
        <div className="text-center py-8">
          <Filter className="h-8 w-8 text-ui-supportText mx-auto mb-2" />
          <p className="text-support text-ui-supportText">
            No insights match the selected filters
          </p>
        </div>
      )}
    </div>
  )
}
