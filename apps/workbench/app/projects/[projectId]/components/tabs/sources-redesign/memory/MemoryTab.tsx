/**
 * MemoryTab Component
 *
 * Displays the unified synthesized memory document.
 * Shows freshness indicators, stale warnings, and refresh functionality.
 */

'use client'

import { useState } from 'react'
import { Info, BookOpen, RefreshCw, Clock, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'
import { UnifiedMemoryResponse } from '@/lib/api'

interface MemoryTabProps {
  /** Unified memory data from API */
  unifiedMemory: UnifiedMemoryResponse | null
  /** Loading state */
  isLoading: boolean
  /** Whether a refresh is in progress */
  isRefreshing?: boolean
  /** Callback to trigger refresh */
  onRefresh?: () => void
}

export function MemoryTab({ unifiedMemory, isLoading, isRefreshing, onRefresh }: MemoryTabProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Warning banner skeleton */}
        <div className="h-14 bg-amber-50 rounded-lg animate-pulse" />

        {/* Content skeleton */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 animate-pulse">
          <div className="space-y-4">
            <div className="h-5 bg-gray-200 rounded w-1/4" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-100 rounded w-full" />
              <div className="h-3 bg-gray-100 rounded w-5/6" />
              <div className="h-3 bg-gray-100 rounded w-4/6" />
            </div>
            <div className="h-5 bg-gray-200 rounded w-1/4 mt-6" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-100 rounded w-full" />
              <div className="h-3 bg-gray-100 rounded w-3/4" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Info banner */}
      <div className="flex items-start gap-3 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-blue-800">
            <strong>Unified Project Memory.</strong> Synthesized from knowledge graph and project records.
          </p>
          <p className="text-xs text-blue-600 mt-1">
            Use <code className="bg-blue-100 px-1 rounded">/remember</code> in chat to add decisions, learnings, or questions.
          </p>
        </div>
      </div>

      {/* Stale warning banner */}
      {unifiedMemory?.is_stale && (
        <div className="flex items-center gap-3 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
          <div className="flex-1">
            <p className="text-sm text-amber-800">
              <strong>Updates available.</strong> New information has been added since this was synthesized.
            </p>
            {unifiedMemory.stale_reason && (
              <p className="text-xs text-amber-600 mt-0.5">
                Reason: {formatStaleReason(unifiedMemory.stale_reason)}
              </p>
            )}
          </div>
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="px-3 py-1.5 text-sm font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 rounded-lg transition-colors disabled:opacity-50"
            >
              {isRefreshing ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                'Refresh'
              )}
            </button>
          )}
        </div>
      )}

      {/* Memory content */}
      {unifiedMemory?.content ? (
        <div className="bg-gray-50 border border-gray-200 rounded-xl overflow-hidden">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-pink-50 rounded-lg flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-pink-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Project Memory</h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <Clock className="w-3 h-3 text-gray-400" />
                  <span className="text-xs text-gray-500">
                    Synthesized {unifiedMemory.freshness?.age_human || 'recently'}
                  </span>
                  {unifiedMemory.is_stale && (
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
                      Stale
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {onRefresh && !unifiedMemory.is_stale && (
                <button
                  onClick={onRefresh}
                  disabled={isRefreshing}
                  className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
                  title="Refresh memory"
                >
                  <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                </button>
              )}
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
              >
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          {/* Content */}
          {isExpanded && (
            <div className="p-6">
              <div className="prose prose-sm max-w-none">
                <Markdown content={unifiedMemory.content} />
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <BookOpen className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No memory synthesized yet</h3>
          <p className="text-sm text-gray-500 max-w-sm mb-4">
            Project memory will be automatically generated once you have signals, decisions, or learnings.
          </p>
          {onRefresh && (
            <button
              onClick={onRefresh}
              disabled={isRefreshing}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-pink-700 bg-pink-50 hover:bg-pink-100 rounded-lg transition-colors disabled:opacity-50"
            >
              {isRefreshing ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4" />
                  Generate Memory
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Format stale reason for display
 */
function formatStaleReason(reason: string): string {
  const reasonMap: Record<string, string> = {
    signal_processed: 'New signal processed',
    bulk_signal_processed: 'Document processed',
    decision_added: 'Decision added',
    learning_added: 'Learning added',
    question_added: 'Question added',
    beliefs_updated: 'Knowledge graph updated',
  }
  return reasonMap[reason] || reason.replace(/_/g, ' ')
}
