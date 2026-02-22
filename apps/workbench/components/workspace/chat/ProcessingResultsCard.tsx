/**
 * ProcessingResultsCard - Deterministic card shown in chat after document processing.
 *
 * Replaces the LLM auto-summary with a structured breakdown of what was extracted,
 * with inline confirm buttons.
 */

'use client'

import { useState, useEffect } from 'react'
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Sparkles,
  Brain,
  ArrowRight,
  Clock,
} from 'lucide-react'
import { getProcessingResults, batchConfirmFromSignal } from '@/lib/api'
import type {
  ProcessingResultsResponse,
  EntityChangeItem,
} from '@/types/api'

interface ProcessingResultsCardProps {
  signalId: string
  projectId: string
  filename: string
  onViewEvidence?: () => void
  onConfirmed?: () => void
}

const ENTITY_TYPE_LABELS: Record<string, string> = {
  feature: 'Features',
  persona: 'Personas',
  vp_step: 'Workflow Steps',
  stakeholder: 'Stakeholders',
  business_driver: 'Business Drivers',
  workflow: 'Workflows',
  data_entity: 'Data Entities',
  constraint: 'Constraints',
  competitor: 'Competitors',
}

export function ProcessingResultsCard({
  signalId,
  projectId,
  filename,
  onViewEvidence,
  onConfirmed,
}: ProcessingResultsCardProps) {
  const [data, setData] = useState<ProcessingResultsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['created']))
  const [confirming, setConfirming] = useState<string | null>(null)
  const [confirmed, setConfirmed] = useState<Set<string>>(new Set())

  useEffect(() => {
    getProcessingResults(signalId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [signalId])

  const handleConfirm = async (scope: 'new' | 'updates' | 'all') => {
    setConfirming(scope)
    try {
      await batchConfirmFromSignal(projectId, { signal_id: signalId, scope })
      setConfirmed((prev) => new Set([...prev, scope]))
      onConfirmed?.()
    } catch (err) {
      console.error('Confirm failed:', err)
    } finally {
      setConfirming(null)
    }
  }

  const handleDefer = async () => {
    setConfirming('defer')
    try {
      await batchConfirmFromSignal(projectId, { signal_id: signalId, scope: 'defer' })
      setConfirmed((prev) => new Set([...prev, 'defer']))
    } catch (err) {
      console.error('Defer failed:', err)
    } finally {
      setConfirming(null)
    }
  }

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-4 animate-pulse">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-gray-200 rounded" />
          <div className="h-4 bg-gray-200 rounded w-48" />
        </div>
        <div className="mt-3 space-y-2">
          <div className="h-3 bg-gray-100 rounded w-full" />
          <div className="h-3 bg-gray-100 rounded w-3/4" />
        </div>
      </div>
    )
  }

  if (!data || data.summary.total_entities_affected === 0) {
    return null
  }

  const { summary } = data
  const created = data.entity_changes.filter((c) => c.revision_type === 'created')
  const updated = data.entity_changes.filter((c) => c.revision_type !== 'created')

  const groupByType = (items: EntityChangeItem[]) => {
    const groups: Record<string, EntityChangeItem[]> = {}
    for (const item of items) {
      if (!groups[item.entity_type]) groups[item.entity_type] = []
      groups[item.entity_type].push(item)
    }
    return Object.entries(groups).sort((a, b) => b[1].length - a[1].length)
  }

  const allConfirmed = confirmed.has('all') || (confirmed.has('new') && confirmed.has('updates'))
  const MAX_ENTITIES_PER_TYPE = 5

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-100 bg-gray-50/50">
        <div className="flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          <span className="text-sm font-semibold text-[#333333] truncate">{filename}</span>
        </div>
        <p className="text-xs text-[#999999] mt-0.5">Processing complete</p>
      </div>

      <div className="px-4 py-3 space-y-3">
        {/* Created section */}
        {created.length > 0 && (
          <div>
            <button
              onClick={() => toggleSection('created')}
              className="flex items-center gap-1.5 text-left mb-1.5"
            >
              {expandedSections.has('created') ? (
                <ChevronDown className="w-3 h-3 text-[#999999]" />
              ) : (
                <ChevronRight className="w-3 h-3 text-[#999999]" />
              )}
              <Sparkles className="w-3 h-3 text-emerald-500" />
              <span className="text-xs font-semibold text-emerald-700">
                Created ({created.length})
              </span>
            </button>
            {expandedSections.has('created') && (
              <div className="space-y-2 pl-5">
                {groupByType(created).map(([entityType, items]) => (
                  <div key={entityType}>
                    <span className="text-[11px] font-medium text-[#999999]">
                      {ENTITY_TYPE_LABELS[entityType] || entityType} ({items.length})
                    </span>
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {items.slice(0, MAX_ENTITIES_PER_TYPE).map((item) => (
                        <span
                          key={item.entity_id}
                          className="px-1.5 py-0.5 text-[11px] rounded bg-emerald-50 text-emerald-700"
                        >
                          {item.entity_label}
                        </span>
                      ))}
                      {items.length > MAX_ENTITIES_PER_TYPE && (
                        <span className="px-1.5 py-0.5 text-[11px] text-[#999999]">
                          +{items.length - MAX_ENTITIES_PER_TYPE} more
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Updated section */}
        {updated.length > 0 && (
          <div>
            <button
              onClick={() => toggleSection('updated')}
              className="flex items-center gap-1.5 text-left mb-1.5"
            >
              {expandedSections.has('updated') ? (
                <ChevronDown className="w-3 h-3 text-[#999999]" />
              ) : (
                <ChevronRight className="w-3 h-3 text-[#999999]" />
              )}
              <ArrowRight className="w-3 h-3 text-indigo-500" />
              <span className="text-xs font-semibold text-indigo-600">
                Updated ({updated.length})
              </span>
            </button>
            {expandedSections.has('updated') && (
              <div className="space-y-1 pl-5">
                {updated.slice(0, MAX_ENTITIES_PER_TYPE).map((item) => (
                  <div key={item.entity_id} className="text-[11px]">
                    <span className="font-medium text-[#333333]">{item.entity_label}</span>
                    {item.diff_summary && (
                      <span className="text-[#999999] ml-1">— {item.diff_summary}</span>
                    )}
                  </div>
                ))}
                {updated.length > MAX_ENTITIES_PER_TYPE && (
                  <span className="text-[11px] text-[#999999]">
                    +{updated.length - MAX_ENTITIES_PER_TYPE} more
                  </span>
                )}
              </div>
            )}
          </div>
        )}

        {/* Memory section */}
        {data.memory_updates.length > 0 && (
          <div>
            <button
              onClick={() => toggleSection('memory')}
              className="flex items-center gap-1.5 text-left mb-1.5"
            >
              {expandedSections.has('memory') ? (
                <ChevronDown className="w-3 h-3 text-[#999999]" />
              ) : (
                <ChevronRight className="w-3 h-3 text-[#999999]" />
              )}
              <Brain className="w-3 h-3 text-[#999999]" />
              <span className="text-xs font-semibold text-[#999999]">
                {data.memory_updates.length} facts extracted
              </span>
            </button>
            {expandedSections.has('memory') && (
              <div className="space-y-1 pl-5">
                {data.memory_updates.slice(0, 3).map((mem) => (
                  <p key={mem.id} className="text-[11px] text-[#333333]">
                    &ldquo;{mem.content}&rdquo;
                  </p>
                ))}
                {data.memory_updates.length > 3 && (
                  <span className="text-[11px] text-[#999999]">
                    +{data.memory_updates.length - 3} more
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Action bar */}
      {!allConfirmed ? (
        <div className="px-4 py-2.5 border-t border-gray-100 flex items-center gap-2 flex-wrap">
          {created.length > 0 && !confirmed.has('new') && (
            <button
              onClick={() => handleConfirm('new')}
              disabled={confirming !== null}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 disabled:opacity-50 transition-colors"
            >
              {confirming === 'new' ? 'Confirming...' : `Accept New (${created.length})`}
            </button>
          )}
          {updated.length > 0 && !confirmed.has('updates') && (
            <button
              onClick={() => handleConfirm('updates')}
              disabled={confirming !== null}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 transition-colors"
            >
              {confirming === 'updates' ? 'Confirming...' : `Accept Updates (${updated.length})`}
            </button>
          )}
          {onViewEvidence && (
            <button
              onClick={onViewEvidence}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-[#333333] hover:bg-gray-50 transition-colors"
            >
              View Details
            </button>
          )}
          {!confirmed.has('defer') && (
            <button
              onClick={handleDefer}
              disabled={confirming !== null}
              className="ml-auto px-2 py-1 text-[11px] text-[#999999] hover:text-[#333333] transition-colors flex items-center gap-1"
            >
              <Clock className="w-3 h-3" />
              Later
            </button>
          )}
        </div>
      ) : (
        <div className="px-4 py-2 border-t border-gray-100 flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-xs text-emerald-700 font-medium">
            {confirmed.has('defer') ? 'Review tasks created' : 'Entities confirmed'}
          </span>
          {onViewEvidence && (
            <button
              onClick={onViewEvidence}
              className="ml-auto text-xs text-[#999999] hover:text-[#333333] transition-colors"
            >
              View Details
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default ProcessingResultsCard
