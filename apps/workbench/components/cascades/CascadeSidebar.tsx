'use client'

import { useState } from 'react'
import { X, Check, ChevronRight, ArrowRight, Zap, AlertCircle, Bell, ChevronDown, ChevronUp } from 'lucide-react'

interface CascadeEvent {
  id: string
  source_entity_type: string
  source_entity_id: string
  source_summary: string
  target_entity_type: string
  target_entity_id: string
  target_summary: string
  cascade_type: 'auto' | 'suggested' | 'logged'
  confidence: number
  changes: Record<string, any>
  rationale?: string
  created_at: string
}

interface CascadeSidebarProps {
  cascades: CascadeEvent[]
  isOpen: boolean
  onToggle: () => void
  onApply: (cascadeId: string) => Promise<void>
  onDismiss: (cascadeId: string) => Promise<void>
  isLoading?: boolean
}

export default function CascadeSidebar({
  cascades,
  isOpen,
  onToggle,
  onApply,
  onDismiss,
  isLoading = false,
}: CascadeSidebarProps) {
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set())
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const handleApply = async (id: string) => {
    setProcessingIds(prev => new Set(prev).add(id))
    try {
      await onApply(id)
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const handleDismiss = async (id: string) => {
    setProcessingIds(prev => new Set(prev).add(id))
    try {
      await onDismiss(id)
    } finally {
      setProcessingIds(prev => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600 bg-green-50'
    if (confidence >= 0.5) return 'text-amber-600 bg-amber-50'
    return 'text-gray-600 bg-gray-50'
  }

  const getEntityIcon = (entityType: string) => {
    switch (entityType) {
      case 'feature':
        return '⭐'
      case 'vp_step':
        return '📍'
      case 'persona':
        return '👤'
      case 'business_driver':
        return '📊'
      default:
        return '📦'
    }
  }

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMins / 60)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    return `${diffHours}h ago`
  }

  // Check if there are any conflict-type cascades (need review urgently)
  const hasConflicts = cascades.some(c => c.changes?.conflict_type)
  const conflictCount = cascades.filter(c => c.changes?.conflict_type).length

  // Collapsed state - show notification badge with red for pending items
  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className={`fixed right-4 top-1/2 -translate-y-1/2 z-40 bg-white border rounded-lg shadow-lg p-3 hover:bg-gray-50 transition-colors ${
          cascades.length > 0 ? 'border-red-200 animate-pulse' : 'border-gray-200'
        }`}
      >
        <div className="relative">
          <Zap className={`h-5 w-5 ${cascades.length > 0 ? 'text-red-500' : 'text-purple-600'}`} />
          {cascades.length > 0 && (
            <span className="absolute -top-2 -right-2 h-5 w-5 bg-red-500 text-white text-xs font-medium rounded-full flex items-center justify-center">
              {cascades.length}
            </span>
          )}
        </div>
      </button>
    )
  }

  return (
    <div className="fixed right-0 top-0 bottom-0 w-80 bg-white border-l border-gray-200 shadow-xl z-50 flex flex-col">
      {/* Header */}
      <div className={`flex-shrink-0 px-4 py-3 border-b border-gray-200 ${
        hasConflicts ? 'bg-gradient-to-r from-red-50 to-orange-50' : 'bg-gradient-to-r from-purple-50 to-blue-50'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className={`h-5 w-5 ${hasConflicts ? 'text-red-500' : 'text-purple-600'}`} />
            <h3 className="font-semibold text-gray-900">AI Suggestions</h3>
            {cascades.length > 0 && (
              <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                hasConflicts ? 'bg-red-100 text-red-700' : 'bg-purple-100 text-purple-700'
              }`}>
                {cascades.length}
              </span>
            )}
            {hasConflicts && (
              <span className="px-2 py-0.5 bg-red-500 text-white text-xs font-medium rounded-full flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                {conflictCount} conflict{conflictCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
          <button
            onClick={onToggle}
            className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <p className="text-xs text-gray-600 mt-1">
          {hasConflicts
            ? 'Review feature conflicts and AI-suggested updates'
            : 'AI-suggested updates based on recent changes'
          }
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {cascades.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="font-medium">No pending suggestions</p>
            <p className="text-sm mt-1">Cascades will appear here when entities are modified</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {cascades.map((cascade) => {
              const isProcessing = processingIds.has(cascade.id)
              const isExpanded = expandedId === cascade.id
              const isConflict = !!cascade.changes?.conflict_type

              return (
                <div
                  key={cascade.id}
                  className={`p-4 transition-colors ${
                    isConflict
                      ? 'bg-red-50 hover:bg-red-100 border-l-4 border-l-red-500'
                      : 'hover:bg-gray-50'
                  }`}
                >
                  {/* Conflict Badge */}
                  {isConflict && (
                    <div className="flex items-center gap-1 mb-2">
                      <AlertCircle className="h-4 w-4 text-red-600" />
                      <span className="text-xs font-semibold text-red-700 uppercase">
                        Feature Conflict
                      </span>
                    </div>
                  )}

                  {/* Source → Target */}
                  <div className="flex items-center gap-2 text-sm mb-2">
                    <span className="flex items-center gap-1.5">
                      <span>{getEntityIcon(cascade.source_entity_type)}</span>
                      <span className="font-medium text-gray-900 truncate max-w-[100px]">
                        {cascade.source_summary.replace(/^(Feature|VP Step|PRD|Persona):?\s*/i, '')}
                      </span>
                    </span>
                    <ArrowRight className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <span className="flex items-center gap-1.5">
                      <span>{getEntityIcon(cascade.target_entity_type)}</span>
                      <span className="text-gray-700 truncate max-w-[100px]">
                        {cascade.target_summary.replace(/^(Feature|VP Step|PRD|Persona):?\s*/i, '')}
                      </span>
                    </span>
                  </div>

                  {/* Confidence and Time */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium ${getConfidenceColor(cascade.confidence)}`}>
                      {(cascade.confidence * 100).toFixed(0)}% confidence
                    </span>
                    <span className="text-xs text-gray-500">
                      {formatTimeAgo(cascade.created_at)}
                    </span>
                  </div>

                  {/* Rationale */}
                  {cascade.rationale && (
                    <p className="text-xs text-gray-600 mb-3 line-clamp-2">
                      {cascade.rationale}
                    </p>
                  )}

                  {/* Expandable Changes */}
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : cascade.id)}
                    className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mb-2"
                  >
                    {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    View changes
                  </button>

                  {isExpanded && (
                    <div className="bg-gray-50 rounded-md p-2 mb-3 text-xs font-mono text-gray-700 overflow-x-auto">
                      <pre>{JSON.stringify(cascade.changes, null, 2)}</pre>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleApply(cascade.id)}
                      disabled={isProcessing}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-purple-600 hover:bg-purple-700 rounded-md transition-colors disabled:opacity-50"
                    >
                      <Check className="h-4 w-4" />
                      Apply
                    </button>
                    <button
                      onClick={() => handleDismiss(cascade.id)}
                      disabled={isProcessing}
                      className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 rounded-md transition-colors disabled:opacity-50"
                    >
                      <X className="h-4 w-4" />
                      Dismiss
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 px-4 py-3 border-t border-gray-200 bg-gray-50">
        <div className="text-xs text-gray-500">
          <p>
            <span className="font-medium text-green-600">High confidence (&gt;80%)</span>: Auto-applied
          </p>
          <p>
            <span className="font-medium text-amber-600">Medium (50-80%)</span>: Shown here
          </p>
          <p>
            <span className="font-medium text-gray-600">Low (&lt;50%)</span>: Logged for review
          </p>
        </div>
      </div>
    </div>
  )
}
