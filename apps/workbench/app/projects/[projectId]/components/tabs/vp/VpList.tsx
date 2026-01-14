/**
 * VpList Component
 *
 * Left column: Selectable list of VP steps
 * - Shows step index, label, status, persona
 * - V2: Shows evidence and generation indicators
 * - Ordered by step_index
 * - Filterable by status
 */

'use client'

import React, { useState } from 'react'
import { ListItem, EmptyState } from '@/components/ui'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Zap, Filter, User, CheckCircle, Sparkles } from 'lucide-react'
import type { VpStep } from '@/types/api'

interface VpListProps {
  steps: VpStep[]
  selectedId: string | null
  onSelect: (step: VpStep) => void
}

export function VpList({ steps, selectedId, onSelect }: VpListProps) {
  const [statusFilter, setStatusFilter] = useState<string | null>(null)

  // Check if entity was recently updated (last 24 hours)
  const isRecentlyUpdated = (updatedAt: string) => {
    const diffMs = new Date().getTime() - new Date(updatedAt).getTime()
    return diffMs < 24 * 60 * 60 * 1000
  }

  // Sort steps by step_index
  const sortedSteps = [...steps].sort((a, b) => a.step_index - b.step_index)

  // Get status for filtering (use confirmation_status for v2, status for legacy)
  const getStepStatus = (step: VpStep) => step.confirmation_status || step.status

  // Filter steps
  const filteredSteps = statusFilter
    ? sortedSteps.filter(s => getStepStatus(s) === statusFilter)
    : sortedSteps

  // Count by status
  const statusCounts = steps.reduce((acc, s) => {
    const status = getStepStatus(s)
    acc[status] = (acc[status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  if (steps.length === 0) {
    return (
      <EmptyState
        icon={<Zap className="h-12 w-12" />}
        title="No VP Steps"
        description="Use the AI assistant to generate the Value Path from your features and personas."
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
          const isV2 = !!(step.narrative_user || step.narrative_system)
          const hasEvidence = step.has_signal_evidence || (step.evidence && step.evidence.some(e => e.source_type === 'signal'))
          const recentlyUpdated = isRecentlyUpdated(step.updated_at)
          const stepStatus = getStepStatus(step)

          // Build subtitle - prefer value_created for v2, fallback to description
          const subtitle = step.value_created || step.description || ''

          // Build additional info line for persona
          const personaInfo = step.actor_persona_name ? (
            <div className="flex items-center gap-1 text-xs text-ui-supportText mt-1">
              <User className="h-3 w-3" />
              <span>{step.actor_persona_name}</span>
            </div>
          ) : null

          return (
            <ListItem
              key={step.id}
              title={
                <div className="flex items-center gap-2">
                  <div className="flex items-center justify-center w-6 h-6 bg-brand-primary/10 rounded-full text-brand-primary text-xs font-semibold flex-shrink-0">
                    {step.step_index}
                  </div>
                  <span>{step.label}</span>
                  {isV2 && (
                    <Sparkles className="h-3.5 w-3.5 text-blue-500" />
                  )}
                  {hasEvidence && (
                    <CheckCircle className="h-3.5 w-3.5 text-green-500" />
                  )}
                  {recentlyUpdated && (
                    <span className="relative inline-flex h-2 w-2">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                    </span>
                  )}
                </div>
              }
              subtitle={subtitle}
              meta={personaInfo}
              badge={<StatusBadge status={stepStatus} />}
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
