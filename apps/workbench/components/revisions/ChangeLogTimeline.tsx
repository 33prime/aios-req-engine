'use client'

import { useState, useEffect } from 'react'
import { Clock, Sparkles, ChevronDown, ChevronUp, AlertCircle } from 'lucide-react'
import { listEntityRevisions } from '@/lib/api'
import { formatDistanceToNow } from 'date-fns'

interface Revision {
  id: string
  entity_type: string
  entity_id: string
  entity_label: string
  revision_type: string
  trigger_event: string | null
  new_signals_count: number
  context_summary: string | null
  created_at: string
}

interface ChangeLogTimelineProps {
  entityType: 'prd_section' | 'vp_step' | 'feature'
  entityId: string
  limit?: number
}

export default function ChangeLogTimeline({
  entityType,
  entityId,
  limit = 10,
}: ChangeLogTimelineProps) {
  const [revisions, setRevisions] = useState<Revision[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    const fetchRevisions = async () => {
      try {
        setLoading(true)
        setError(null)
        const response = await listEntityRevisions(entityType, entityId, limit)
        setRevisions(response.revisions)
      } catch (err) {
        console.error('Failed to fetch revisions:', err)
        setError('Failed to load change history')
      } finally {
        setLoading(false)
      }
    }

    fetchRevisions()
  }, [entityType, entityId, limit])

  const toggleExpanded = (revisionId: string) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(revisionId)) {
      newExpanded.delete(revisionId)
    } else {
      newExpanded.add(revisionId)
    }
    setExpandedIds(newExpanded)
  }

  const getRevisionTypeBadge = (type: string) => {
    switch (type) {
      case 'created':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800">
            <Sparkles className="h-3 w-3 mr-1" />
            Created
          </span>
        )
      case 'enriched':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800">
            <Sparkles className="h-3 w-3 mr-1" />
            Enriched
          </span>
        )
      case 'updated':
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-purple-100 text-purple-800">
            <Clock className="h-3 w-3 mr-1" />
            Updated
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-800">
            {type}
          </span>
        )
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return formatDistanceToNow(date, { addSuffix: true })
    } catch {
      return timestamp
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center space-x-2 text-red-600 py-4">
        <AlertCircle className="h-5 w-5" />
        <span>{error}</span>
      </div>
    )
  }

  if (revisions.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <Clock className="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>No enrichment history yet</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

        {/* Revision entries */}
        <div className="space-y-6">
          {revisions.map((revision, index) => (
            <div key={revision.id} className="relative pl-10">
              {/* Timeline dot */}
              <div
                className={`absolute left-0 top-1 h-8 w-8 rounded-full border-4 border-white flex items-center justify-center ${
                  index === 0
                    ? 'bg-blue-500'
                    : revision.revision_type === 'created'
                    ? 'bg-green-500'
                    : 'bg-gray-300'
                }`}
              >
                <Sparkles className="h-4 w-4 text-white" />
              </div>

              {/* Revision content */}
              <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
                <div className="p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2">
                      {getRevisionTypeBadge(revision.revision_type)}
                      <span className="text-sm text-gray-500">{formatTimestamp(revision.created_at)}</span>
                    </div>
                    <button
                      onClick={() => toggleExpanded(revision.id)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      {expandedIds.has(revision.id) ? (
                        <ChevronUp className="h-5 w-5" />
                      ) : (
                        <ChevronDown className="h-5 w-5" />
                      )}
                    </button>
                  </div>

                  {/* Context summary */}
                  {revision.context_summary && (
                    <p className="text-sm text-gray-700 mb-2 italic">{revision.context_summary}</p>
                  )}

                  {/* Signal count badge */}
                  {revision.new_signals_count > 0 && (
                    <div className="inline-flex items-center px-2 py-1 rounded-md text-xs bg-indigo-50 text-indigo-700">
                      {revision.new_signals_count} new signal{revision.new_signals_count !== 1 ? 's' : ''}
                    </div>
                  )}

                  {/* Expanded details */}
                  {expandedIds.has(revision.id) && (
                    <div className="mt-4 pt-4 border-t border-gray-100">
                      <dl className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <dt className="font-medium text-gray-500">Trigger</dt>
                          <dd className="text-gray-900">{revision.trigger_event || 'Unknown'}</dd>
                        </div>
                        <div>
                          <dt className="font-medium text-gray-500">Entity</dt>
                          <dd className="text-gray-900">{revision.entity_label}</dd>
                        </div>
                      </dl>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
