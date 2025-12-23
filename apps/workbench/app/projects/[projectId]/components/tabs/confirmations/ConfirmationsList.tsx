/**
 * ConfirmationsList Component
 *
 * Left column: Selectable list of confirmations
 * - Shows title, kind, priority
 * - Filterable by status
 * - Suggested method indicator (email/meeting)
 * - Complexity badge
 */

'use client'

import React, { useState } from 'react'
import { ListItem, EmptyState } from '@/components/ui'
import { ComplexityBadge } from '@/components/ui/StatusBadge'
import { CheckSquare, MessageSquare, Phone, Filter } from 'lucide-react'
import type { Confirmation } from '@/types/api'
import { getComplexityScore } from '@/lib/status-utils'

interface ConfirmationsListProps {
  confirmations: Confirmation[]
  selectedId: string | null
  onSelect: (confirmation: Confirmation) => void
}

type StatusType = 'open' | 'queued' | 'resolved' | 'dismissed'

const KIND_COLORS: Record<string, string> = {
  prd: 'bg-green-100 text-green-800',
  vp: 'bg-purple-100 text-purple-800',
  feature: 'bg-blue-100 text-blue-800',
  insight: 'bg-orange-100 text-orange-800',
  gate: 'bg-gray-100 text-gray-800',
}

export function ConfirmationsList({ confirmations, selectedId, onSelect }: ConfirmationsListProps) {
  const [statusFilter, setStatusFilter] = useState<StatusType | 'all'>('open')

  // Filter confirmations
  const filteredConfirmations = statusFilter === 'all'
    ? confirmations
    : confirmations.filter(c => c.status === statusFilter)

  // Count by status
  const statusCounts = confirmations.reduce((acc, c) => {
    acc[c.status] = (acc[c.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  if (confirmations.length === 0) {
    return (
      <EmptyState
        icon={<CheckSquare className="h-12 w-12" />}
        title="No Confirmations"
        description="Items marked for client confirmation will appear here."
      />
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with filter */}
      <div>
        <h2 className="heading-2 mb-2">Client Confirmations</h2>
        <p className="text-support text-ui-supportText mb-4">
          {filteredConfirmations.length} of {confirmations.length} confirmations
        </p>

        {/* Status Filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setStatusFilter('all')}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              statusFilter === 'all'
                ? 'bg-brand-primary text-white'
                : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
            }`}
          >
            All ({confirmations.length})
          </button>
          {(['open', 'queued', 'resolved', 'dismissed'] as StatusType[]).map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                statusFilter === status
                  ? 'bg-brand-primary text-white'
                  : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
              }`}
            >
              {status} ({statusCounts[status] || 0})
            </button>
          ))}
        </div>
      </div>

      {/* Confirmations List */}
      <div className="space-y-2">
        {filteredConfirmations.map((confirmation) => {
          const complexityScore = getComplexityScore(confirmation)

          return (
            <ListItem
              key={confirmation.id}
              title={
                <div className="flex items-center gap-2">
                  <span>{confirmation.title}</span>
                  {confirmation.suggested_method === 'email' ? (
                    <MessageSquare className="h-3 w-3 text-ui-supportText flex-shrink-0" />
                  ) : (
                    <Phone className="h-3 w-3 text-ui-supportText flex-shrink-0" />
                  )}
                </div>
              }
              subtitle={confirmation.ask}
              meta={
                <div className="flex items-center gap-2 mt-2">
                  <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${KIND_COLORS[confirmation.kind] || 'bg-gray-100 text-gray-800'}`}>
                    {confirmation.kind.toUpperCase()}
                  </span>
                  {confirmation.evidence.length > 0 && (
                    <span className="text-xs text-ui-supportText">
                      {confirmation.evidence.length} evidence
                    </span>
                  )}
                </div>
              }
              badge={<ComplexityBadge score={complexityScore} />}
              active={confirmation.id === selectedId}
              onClick={() => onSelect(confirmation)}
            />
          )
        })}
      </div>

      {filteredConfirmations.length === 0 && (
        <div className="text-center py-8">
          <Filter className="h-8 w-8 text-ui-supportText mx-auto mb-2" />
          <p className="text-support text-ui-supportText">
            No confirmations match the selected filter
          </p>
        </div>
      )}
    </div>
  )
}
