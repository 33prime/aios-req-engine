'use client'

import { useState } from 'react'
import { Check, ChevronDown, ChevronUp, Layers } from 'lucide-react'
import type { ConfirmationCluster } from '@/types/workspace'
import { confirmCluster } from '@/lib/api'

const TYPE_LABELS: Record<string, string> = {
  feature: 'Features',
  persona: 'Personas',
  workflow: 'Workflows',
  data_entity: 'Data',
  business_driver: 'Drivers',
  constraint: 'Constraints',
  stakeholder: 'Stakeholders',
}

interface ConfirmationClustersProps {
  projectId: string
  clusters: ConfirmationCluster[]
  onConfirmed: () => void
}

export function ConfirmationClusters({
  projectId,
  clusters,
  onConfirmed,
}: ConfirmationClustersProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [confirming, setConfirming] = useState<string | null>(null)

  if (!clusters.length) return null

  const handleConfirm = async (cluster: ConfirmationCluster) => {
    try {
      setConfirming(cluster.cluster_id)
      await confirmCluster(
        projectId,
        cluster.entities.map(e => ({
          entity_id: e.entity_id,
          entity_type: e.entity_type,
        })),
      )
      onConfirmed()
    } catch (err) {
      console.error('Failed to confirm cluster:', err)
    } finally {
      setConfirming(null)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-3">
        <Layers className="w-4 h-4 text-brand-primary" />
        <span className="text-xs font-semibold text-text-body uppercase tracking-wide">
          Related Groups to Confirm
        </span>
        <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-brand-primary-light text-[#25785A] font-medium">
          {clusters.length}
        </span>
      </div>

      {clusters.map(cluster => {
        const isExpanded = expandedId === cluster.cluster_id
        const isConfirming = confirming === cluster.cluster_id

        return (
          <div
            key={cluster.cluster_id}
            className="border border-border rounded-lg overflow-hidden"
          >
            {/* Header */}
            <div
              className="flex items-center justify-between px-3 py-2.5 cursor-pointer hover:bg-gray-50 transition-colors"
              onClick={() => setExpandedId(isExpanded ? null : cluster.cluster_id)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-text-body truncate">
                    {cluster.theme}
                  </span>
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-100 text-[#666666] font-medium shrink-0">
                    {cluster.total}
                  </span>
                </div>
                <div className="flex gap-1.5 mt-1">
                  {Object.entries(cluster.entity_type_counts).map(([type, count]) => (
                    <span
                      key={type}
                      className="text-[10px] text-text-placeholder"
                    >
                      {count} {TYPE_LABELS[type] || type}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0 ml-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleConfirm(cluster)
                  }}
                  disabled={isConfirming}
                  className="flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-brand-primary bg-brand-primary-light rounded-md hover:bg-brand-primary-light transition-colors disabled:opacity-50"
                >
                  <Check className="w-3 h-3" />
                  {isConfirming ? 'Confirming...' : 'Confirm All'}
                </button>
                {isExpanded ? (
                  <ChevronUp className="w-3.5 h-3.5 text-text-placeholder" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5 text-text-placeholder" />
                )}
              </div>
            </div>

            {/* Expanded entity list */}
            {isExpanded && (
              <div className="border-t border-border bg-gray-50/50 px-3 py-2 space-y-1">
                {cluster.entities.map(entity => (
                  <div
                    key={entity.entity_id}
                    className="flex items-center gap-2 text-xs py-1"
                  >
                    <span className="px-1.5 py-0.5 rounded bg-[#0A1E2F]/5 text-[#0A1E2F] text-[10px] font-medium shrink-0">
                      {entity.entity_type.replace('_', ' ')}
                    </span>
                    <span className="text-text-body truncate">{entity.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
