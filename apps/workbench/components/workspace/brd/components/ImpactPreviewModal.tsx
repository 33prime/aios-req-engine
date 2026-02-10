'use client'

import { useState, useEffect } from 'react'
import { X, AlertTriangle, Loader2 } from 'lucide-react'
import { getImpactAnalysis } from '@/lib/api'
import type { ImpactAnalysis } from '@/types/workspace'

interface ImpactPreviewModalProps {
  open: boolean
  projectId: string
  entityType: string
  entityId: string
  entityName: string
  onClose: () => void
  onConfirmDelete: () => void
}

const RECOMMENDATION_CONFIG = {
  auto: { bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', label: 'Low Impact' },
  review_suggested: { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'Review Suggested' },
  high_impact_warning: { bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', label: 'High Impact' },
}

const ENTITY_TYPE_LABELS: Record<string, string> = {
  feature: 'Feature',
  persona: 'Persona',
  vp_step: 'Workflow Step',
  data_entity: 'Data Entity',
  strategic_context: 'Strategic Context',
}

export function ImpactPreviewModal({
  open,
  projectId,
  entityType,
  entityId,
  entityName,
  onClose,
  onConfirmDelete,
}: ImpactPreviewModalProps) {
  const [impact, setImpact] = useState<ImpactAnalysis | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setImpact(null)
      setError(null)
      return
    }

    async function fetchImpact() {
      setIsLoading(true)
      setError(null)
      try {
        const result = await getImpactAnalysis(projectId, entityType, entityId)
        setImpact(result)
      } catch (err) {
        console.error('Failed to fetch impact analysis:', err)
        setError('Could not load impact analysis')
      } finally {
        setIsLoading(false)
      }
    }

    fetchImpact()
  }, [open, projectId, entityType, entityId])

  if (!open) return null

  const recConfig = impact
    ? RECOMMENDATION_CONFIG[impact.recommendation] || RECOMMENDATION_CONFIG.auto
    : null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <h3 className="text-[15px] font-semibold text-[#37352f]">Delete {ENTITY_TYPE_LABELS[entityType] || entityType}?</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100 text-gray-400">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-5 space-y-4">
          <p className="text-[13px] text-[rgba(55,53,47,0.65)]">
            You are about to delete <span className="font-medium text-[#37352f]">{entityName}</span>.
          </p>

          {isLoading && (
            <div className="flex items-center justify-center py-4">
              <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
              <span className="ml-2 text-[13px] text-gray-400">Analyzing impact...</span>
            </div>
          )}

          {error && (
            <p className="text-[12px] text-red-500">{error}</p>
          )}

          {impact && (
            <div className="space-y-3">
              {/* Recommendation badge */}
              {recConfig && (
                <div className={`inline-flex items-center px-2.5 py-1 rounded-full text-[12px] font-medium ${recConfig.bg} ${recConfig.text} border ${recConfig.border}`}>
                  {recConfig.label}
                </div>
              )}

              {/* Impact count */}
              <p className="text-[13px] text-[rgba(55,53,47,0.65)]">
                <span className="font-medium text-[#37352f]">{impact.total_affected}</span>{' '}
                {impact.total_affected === 1 ? 'entity' : 'entities'} will be affected.
              </p>

              {/* Direct impacts list */}
              {impact.direct_impacts.length > 0 && (
                <div>
                  <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wide">
                    Direct impacts ({impact.direct_impacts.length})
                  </span>
                  <ul className="mt-1 space-y-1">
                    {impact.direct_impacts.slice(0, 8).map((item, i) => (
                      <li key={i} className="flex items-center gap-2 text-[12px] text-[rgba(55,53,47,0.65)]">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-300 flex-shrink-0" />
                        <span className="text-[11px] text-gray-400">{ENTITY_TYPE_LABELS[item.type] || item.type}</span>
                        <span className="truncate">{item.id.slice(0, 8)}...</span>
                      </li>
                    ))}
                    {impact.direct_impacts.length > 8 && (
                      <li className="text-[11px] text-gray-400 ml-4">
                        +{impact.direct_impacts.length - 8} more
                      </li>
                    )}
                  </ul>
                </div>
              )}

              {impact.indirect_impacts.length > 0 && (
                <p className="text-[11px] text-gray-400">
                  +{impact.indirect_impacts.length} indirect {impact.indirect_impacts.length === 1 ? 'impact' : 'impacts'}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-4 border-t border-gray-200">
          <button
            onClick={onClose}
            className="px-4 py-2 text-[13px] font-medium text-gray-600 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onConfirmDelete()
              onClose()
            }}
            disabled={isLoading}
            className="px-4 py-2 text-[13px] font-medium text-white bg-red-600 rounded-md hover:bg-red-700 transition-colors disabled:opacity-40"
          >
            Delete Anyway
          </button>
        </div>
      </div>
    </div>
  )
}
