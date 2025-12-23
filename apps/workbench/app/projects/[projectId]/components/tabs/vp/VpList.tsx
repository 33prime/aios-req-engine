/**
 * VpList Component
 *
 * Left column: Selectable list of VP steps
 * - Shows step index, label, status
 * - Ordered by step_index
 * - Filterable by status
 * - Enrichment indicator
 */

'use client'

import React, { useState } from 'react'
import { ListItem, EmptyState } from '@/components/ui'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Zap, Filter } from 'lucide-react'
import type { VpStep } from '@/types/api'

interface VpListProps {
  steps: VpStep[]
  selectedId: string | null
  onSelect: (step: VpStep) => void
}

export function VpList({ steps, selectedId, onSelect }: VpListProps) {
  const [statusFilter, setStatusFilter] = useState<string | null>(null)

  // Sort steps by step_index
  const sortedSteps = [...steps].sort((a, b) => a.step_index - b.step_index)

  // Filter steps
  const filteredSteps = statusFilter
    ? sortedSteps.filter(s => s.status === statusFilter)
    : sortedSteps

  // Count by status
  const statusCounts = steps.reduce((acc, s) => {
    acc[s.status] = (acc[s.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  if (steps.length === 0) {
    return (
      <EmptyState
        icon={<Zap className="h-12 w-12" />}
        title="No VP Steps"
        description="Run the Build State agent to extract Value Path steps from your signals."
      />
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with filter */}
      <div>
        <h2 className="heading-2 mb-2">Value Path Steps</h2>
        <p className="text-support text-ui-supportText mb-4">
          {filteredSteps.length} of {steps.length} steps
        </p>

        {/* Status Filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setStatusFilter(null)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              statusFilter === null
                ? 'bg-brand-primary text-white'
                : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
            }`}
          >
            All ({steps.length})
          </button>
          {Object.entries(statusCounts).map(([status, count]) => (
            <button
              key={status}
              onClick={() => setStatusFilter(statusFilter === status ? null : status)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                statusFilter === status
                  ? 'bg-brand-primary text-white'
                  : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
              }`}
            >
              {status.replace(/_/g, ' ')} ({count})
            </button>
          ))}
        </div>
      </div>

      {/* Steps List */}
      <div className="space-y-2">
        {filteredSteps.map((step) => {
          const isEnriched = !!step.enrichment

          return (
            <ListItem
              key={step.id}
              title={
                <div className="flex items-center gap-2">
                  <div className="flex items-center justify-center w-6 h-6 bg-brand-primary/10 rounded-full text-brand-primary text-xs font-semibold flex-shrink-0">
                    {step.step_index}
                  </div>
                  <span>{step.label}</span>
                  {isEnriched && (
                    <span className="text-xs text-brand-accent">✨</span>
                  )}
                </div>
              }
              subtitle={step.description}
              badge={<StatusBadge status={step.status} />}
              active={step.id === selectedId}
              onClick={() => onSelect(step)}
            />
          )
        })}
      </div>

      {filteredSteps.length === 0 && (
        <div className="text-center py-8">
          <Filter className="h-8 w-8 text-ui-supportText mx-auto mb-2" />
          <p className="text-support text-ui-supportText">
            No steps match the selected filter
          </p>
        </div>
      )}
    </div>
  )
}
