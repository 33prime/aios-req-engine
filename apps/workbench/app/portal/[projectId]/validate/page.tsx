/**
 * Validation Queue Page
 *
 * Cards grouped by entity_type with filter dropdown.
 * Each card uses the ValidationCard component for confirm/refine/flag.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useParams } from 'next/navigation'
import { getValidationQueue, submitVerdict } from '@/lib/api'
import ValidationCard from '@/components/portal/ValidationCard'
import type { ValidationQueueResponse, VerdictType, ValidationItem } from '@/types/portal'

const ENTITY_TYPE_LABELS: Record<string, string> = {
  workflow: 'Workflows',
  business_driver: 'Business Drivers',
  feature: 'Features',
  persona: 'Personas',
  vp_step: 'Value Path Steps',
  prototype_epic: 'Epics',
}

export default function ValidatePage() {
  const params = useParams()
  const projectId = params.projectId as string

  const [loading, setLoading] = useState(true)
  const [queue, setQueue] = useState<ValidationQueueResponse | null>(null)
  const [filter, setFilter] = useState<string>('all')
  const [error, setError] = useState<string | null>(null)

  const loadQueue = useCallback(async () => {
    try {
      setError(null)
      const data = await getValidationQueue(projectId, filter === 'all' ? undefined : filter)
      setQueue(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [projectId, filter])

  useEffect(() => {
    setLoading(true)
    loadQueue()
  }, [loadQueue])

  const handleVerdict = async (entityType: string, entityId: string, verdict: VerdictType, notes?: string) => {
    await submitVerdict(projectId, {
      entity_type: entityType,
      entity_id: entityId,
      verdict,
      notes,
    })
    // Refresh queue after verdict
    await loadQueue()
  }

  if (loading && !queue) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[#009b87] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-500">Loading validation queue...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <button onClick={loadQueue} className="text-sm text-[#009b87] hover:underline">
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Group items by entity_type
  const grouped: Record<string, ValidationItem[]> = {}
  for (const item of queue?.items || []) {
    const key = item.entity_type
    if (!grouped[key]) grouped[key] = []
    grouped[key].push(item)
  }

  // Get entity types present for filter options
  const availableTypes = Object.keys(queue?.by_type || {}).filter(
    t => (queue?.by_type[t] || 0) > 0
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Validation Queue</h1>
          <p className="text-gray-500 mt-1">
            {queue?.total_pending || 0} items pending review
          </p>
        </div>

        {/* Filter */}
        {availableTypes.length > 1 && (
          <select
            value={filter}
            onChange={e => setFilter(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
          >
            <option value="all">All types</option>
            {availableTypes.map(type => (
              <option key={type} value={type}>
                {ENTITY_TYPE_LABELS[type] || type} ({queue?.by_type[type] || 0})
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Grouped validation cards */}
      {Object.keys(grouped).length === 0 ? (
        <div className="text-center py-12">
          <div className="w-16 h-16 bg-green-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">&#10003;</span>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">All Caught Up</h2>
          <p className="text-gray-500 max-w-md mx-auto">
            No items awaiting your validation. Check back later as your consultant adds more.
          </p>
        </div>
      ) : (
        Object.entries(grouped).map(([entityType, items]) => (
          <div key={entityType} className="space-y-3">
            <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
              {ENTITY_TYPE_LABELS[entityType] || entityType}
              <span className="ml-2 text-gray-400">({items.length})</span>
            </h2>
            {items.map(item => (
              <ValidationCard
                key={item.id}
                item={item}
                onVerdict={handleVerdict}
              />
            ))}
          </div>
        ))
      )}
    </div>
  )
}
