'use client'

import { useState } from 'react'
import { Check, X, AlertTriangle, Clock, Eye, ChevronDown, ChevronUp, Layers, Plus, Edit2, Trash2 } from 'lucide-react'

interface Contradiction {
  description: string
  severity: 'critical' | 'important' | 'minor'
  entity_type: string
  entity_name: string
  field_name: string
  proposed_value: any
  existing_value: any
  resolution_suggestion?: string
}

interface Proposal {
  id: string
  title: string
  description?: string
  proposal_type: string
  status: string
  creates_count: number
  updates_count: number
  deletes_count: number
  stale_reason?: string | null
  has_conflicts?: boolean
  conflicting_proposals?: string[]
  contradictions?: Contradiction[]
  overall_confidence?: number
  created_at: string
}

interface BatchReviewPanelProps {
  proposals: Proposal[]
  isLoading?: boolean
  onApply?: (proposalId: string) => Promise<void>
  onDiscard?: (proposalId: string) => Promise<void>
  onBatchApply?: (proposalIds: string[]) => Promise<void>
  onBatchDiscard?: (proposalIds: string[]) => Promise<void>
  onViewDetails?: (proposalId: string) => void
}

export default function BatchReviewPanel({
  proposals,
  isLoading = false,
  onApply,
  onDiscard,
  onBatchApply,
  onBatchDiscard,
  onViewDetails,
}: BatchReviewPanelProps) {
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set())

  const pendingProposals = proposals.filter(p => p.status === 'pending' || p.status === 'previewed')

  const toggleSelection = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const selectAll = () => {
    const nonStaleIds = pendingProposals
      .filter(p => !p.stale_reason)
      .map(p => p.id)
    setSelectedIds(new Set(nonStaleIds))
  }

  const clearSelection = () => {
    setSelectedIds(new Set())
  }

  const handleApply = async (proposalId: string) => {
    if (!onApply) return
    setProcessingIds(prev => new Set(prev).add(proposalId))
    try {
      await onApply(proposalId)
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev)
        next.delete(proposalId)
        return next
      })
    }
  }

  const handleDiscard = async (proposalId: string) => {
    if (!onDiscard) return
    setProcessingIds(prev => new Set(prev).add(proposalId))
    try {
      await onDiscard(proposalId)
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev)
        next.delete(proposalId)
        return next
      })
    }
  }

  const handleBatchApply = async () => {
    if (!onBatchApply || selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    ids.forEach(id => setProcessingIds(prev => new Set(prev).add(id)))
    try {
      await onBatchApply(ids)
      setSelectedIds(new Set())
    } finally {
      setProcessingIds(new Set())
    }
  }

  const handleBatchDiscard = async () => {
    if (!onBatchDiscard || selectedIds.size === 0) return
    const ids = Array.from(selectedIds)
    ids.forEach(id => setProcessingIds(prev => new Set(prev).add(id)))
    try {
      await onBatchDiscard(ids)
      setSelectedIds(new Set())
    } finally {
      setProcessingIds(new Set())
    }
  }

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  const getChangeBadges = (proposal: Proposal) => {
    const badges = []
    if (proposal.creates_count > 0) {
      badges.push(
        <span key="create" className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
          <Plus className="h-3 w-3" />
          {proposal.creates_count}
        </span>
      )
    }
    if (proposal.updates_count > 0) {
      badges.push(
        <span key="update" className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-700">
          <Edit2 className="h-3 w-3" />
          {proposal.updates_count}
        </span>
      )
    }
    if (proposal.deletes_count > 0) {
      badges.push(
        <span key="delete" className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
          <Trash2 className="h-3 w-3" />
          {proposal.deletes_count}
        </span>
      )
    }
    return badges
  }

  if (pendingProposals.length === 0) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="text-center text-gray-500">
          <Layers className="h-8 w-8 mx-auto mb-2 opacity-50" />
          <p className="font-medium">No pending proposals</p>
          <p className="text-sm">Proposals will appear here when created</p>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-5 w-5 text-gray-600" />
          <h3 className="font-semibold text-gray-900">
            Pending Proposals ({pendingProposals.length})
          </h3>
        </div>

        {/* Batch Actions */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">{selectedIds.size} selected</span>
            <button
              onClick={handleBatchApply}
              disabled={isLoading}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors disabled:opacity-50"
            >
              <Check className="h-4 w-4" />
              Apply Selected
            </button>
            <button
              onClick={handleBatchDiscard}
              disabled={isLoading}
              className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-md transition-colors disabled:opacity-50"
            >
              <X className="h-4 w-4" />
              Discard
            </button>
          </div>
        )}

        {selectedIds.size === 0 && (
          <button
            onClick={selectAll}
            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
          >
            Select all
          </button>
        )}
      </div>

      {/* Proposal List */}
      <div className="divide-y divide-gray-100">
        {pendingProposals.map((proposal) => {
          const isSelected = selectedIds.has(proposal.id)
          const isProcessing = processingIds.has(proposal.id)
          const isStale = !!proposal.stale_reason
          const hasConflicts = proposal.has_conflicts

          return (
            <div
              key={proposal.id}
              className={`px-4 py-3 transition-colors ${
                isSelected ? 'bg-blue-50' : isStale ? 'bg-amber-50' : 'hover:bg-gray-50'
              }`}
            >
              <div className="flex items-start gap-3">
                {/* Checkbox */}
                <div className="flex-shrink-0 pt-0.5">
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleSelection(proposal.id)}
                    disabled={isStale || isProcessing}
                    className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 disabled:opacity-50"
                  />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium text-gray-900 truncate">
                          {proposal.title}
                        </span>

                        {/* Status Badges */}
                        {isStale && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200">
                            <AlertTriangle className="h-3 w-3" />
                            Stale
                          </span>
                        )}
                        {hasConflicts && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800 border border-red-200">
                            <AlertTriangle className="h-3 w-3" />
                            Conflict
                          </span>
                        )}

                        {/* Change Badges */}
                        <div className="flex items-center gap-1">
                          {getChangeBadges(proposal)}
                        </div>
                      </div>

                      {/* Stale Reason */}
                      {isStale && proposal.stale_reason && (
                        <p className="text-xs text-amber-700 mt-1">
                          {proposal.stale_reason}
                        </p>
                      )}

                      {/* Meta */}
                      <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                        <span className="capitalize">{proposal.proposal_type}</span>
                        <span>{formatTimeAgo(proposal.created_at)}</span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      {!isStale && (
                        <>
                          <button
                            onClick={() => handleApply(proposal.id)}
                            disabled={isProcessing}
                            className="p-1.5 text-green-600 hover:bg-green-100 rounded transition-colors disabled:opacity-50"
                            title="Apply"
                          >
                            <Check className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDiscard(proposal.id)}
                            disabled={isProcessing}
                            className="p-1.5 text-gray-500 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
                            title="Discard"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        </>
                      )}
                      {onViewDetails && (
                        <button
                          onClick={() => onViewDetails(proposal.id)}
                          className="p-1.5 text-gray-500 hover:bg-gray-100 rounded transition-colors"
                          title="View Details"
                        >
                          <Eye className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => setExpandedId(expandedId === proposal.id ? null : proposal.id)}
                        className="p-1.5 text-gray-500 hover:bg-gray-100 rounded transition-colors"
                      >
                        {expandedId === proposal.id ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedId === proposal.id && (
                    <div className="mt-3 pt-3 border-t border-gray-200 space-y-3">
                      {proposal.description && (
                        <p className="text-sm text-gray-700">
                          {proposal.description}
                        </p>
                      )}

                      {/* Confidence Score */}
                      {proposal.overall_confidence !== undefined && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">Confidence:</span>
                          <div className="flex-1 max-w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div
                              className={`h-full rounded-full ${
                                proposal.overall_confidence >= 0.8
                                  ? 'bg-green-500'
                                  : proposal.overall_confidence >= 0.5
                                    ? 'bg-yellow-500'
                                    : 'bg-red-500'
                              }`}
                              style={{ width: `${proposal.overall_confidence * 100}%` }}
                            />
                          </div>
                          <span className="text-xs font-medium text-gray-700">
                            {Math.round(proposal.overall_confidence * 100)}%
                          </span>
                        </div>
                      )}

                      {/* Contradictions */}
                      {proposal.contradictions && proposal.contradictions.length > 0 && (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-amber-700 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            {proposal.contradictions.length} Contradiction{proposal.contradictions.length !== 1 ? 's' : ''} Found
                          </p>
                          <div className="space-y-2">
                            {proposal.contradictions.map((contradiction, idx) => (
                              <div
                                key={idx}
                                className={`p-3 rounded-lg border ${
                                  contradiction.severity === 'critical'
                                    ? 'bg-red-50 border-red-200'
                                    : contradiction.severity === 'important'
                                      ? 'bg-amber-50 border-amber-200'
                                      : 'bg-gray-50 border-gray-200'
                                }`}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                                        contradiction.severity === 'critical'
                                          ? 'bg-red-200 text-red-800'
                                          : contradiction.severity === 'important'
                                            ? 'bg-amber-200 text-amber-800'
                                            : 'bg-gray-200 text-gray-700'
                                      }`}>
                                        {contradiction.severity.toUpperCase()}
                                      </span>
                                      <span className="text-xs text-gray-500">
                                        {contradiction.entity_type}: {contradiction.entity_name}
                                      </span>
                                    </div>
                                    <p className="text-sm text-gray-800">{contradiction.description}</p>

                                    {/* Value comparison */}
                                    <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
                                      <div className="p-2 bg-red-100 rounded">
                                        <span className="font-medium text-red-700">Current:</span>
                                        <span className="ml-1 text-red-900">
                                          {JSON.stringify(contradiction.existing_value)}
                                        </span>
                                      </div>
                                      <div className="p-2 bg-green-100 rounded">
                                        <span className="font-medium text-green-700">Proposed:</span>
                                        <span className="ml-1 text-green-900">
                                          {JSON.stringify(contradiction.proposed_value)}
                                        </span>
                                      </div>
                                    </div>

                                    {/* Resolution suggestion */}
                                    {contradiction.resolution_suggestion && (
                                      <p className="mt-2 text-xs text-gray-600 italic">
                                        💡 {contradiction.resolution_suggestion}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Conflicting Proposals */}
                      {proposal.conflicting_proposals && proposal.conflicting_proposals.length > 0 && (
                        <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                          <p className="font-medium">Conflicts with {proposal.conflicting_proposals.length} other proposal(s)</p>
                          <p className="text-red-600 mt-1">
                            Apply or discard conflicting proposals first to resolve.
                          </p>
                        </div>
                      )}

                      <div className="text-xs text-gray-500">
                        <p>ID: {proposal.id}</p>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Footer with selection actions */}
      {selectedIds.size > 0 && (
        <div className="px-4 py-2 bg-blue-50 border-t border-blue-200 flex items-center justify-between">
          <button
            onClick={clearSelection}
            className="text-sm text-blue-600 hover:text-blue-700"
          >
            Clear selection
          </button>
          <span className="text-sm text-blue-700">
            {selectedIds.size} of {pendingProposals.length} selected
          </span>
        </div>
      )}
    </div>
  )
}
