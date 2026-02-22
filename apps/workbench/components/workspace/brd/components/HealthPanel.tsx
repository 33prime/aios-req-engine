'use client'

import { useState, useEffect, useCallback } from 'react'
import { AlertTriangle, ChevronRight, RefreshCw, Loader2 } from 'lucide-react'
import { getBRDHealth, refreshStaleEntity, processCascades } from '@/lib/api'
import type { BRDHealthData, ScopeAlert } from '@/types/workspace'

interface HealthPanelProps {
  projectId: string
  onDataRefresh: () => void
}

const ENTITY_TYPE_LABELS: Record<string, string> = {
  features: 'Features',
  personas: 'Personas',
  vp_steps: 'Workflow Steps',
  data_entities: 'Data Entities',
  strategic_context: 'Strategic Context',
}

function AlertPill({ alert }: { alert: ScopeAlert }) {
  const isWarning = alert.severity === 'warning'
  return (
    <div className={`flex items-start gap-2 px-3 py-2 rounded-md text-[12px] ${
      isWarning ? 'bg-amber-50 text-amber-800' : 'bg-blue-50 text-blue-700'
    }`}>
      <AlertTriangle className={`w-3.5 h-3.5 flex-shrink-0 mt-0.5 ${
        isWarning ? 'text-amber-500' : 'text-blue-400'
      }`} />
      <span>{alert.message}</span>
    </div>
  )
}

export function HealthPanel({ projectId, onDataRefresh }: HealthPanelProps) {
  const [health, setHealth] = useState<BRDHealthData | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const loadHealth = useCallback(async () => {
    try {
      setIsLoading(true)
      const data = await getBRDHealth(projectId)
      setHealth(data)
    } catch (err) {
      console.error('Failed to load BRD health:', err)
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadHealth()
  }, [loadHealth])

  const handleRefreshEntity = useCallback(async (entityType: string, entityId: string) => {
    try {
      await refreshStaleEntity(projectId, entityType, entityId)
      loadHealth()
      onDataRefresh()
    } catch (err) {
      console.error('Failed to refresh entity:', err)
    }
  }, [projectId, loadHealth, onDataRefresh])

  const handleRefreshAll = useCallback(async () => {
    setIsRefreshing(true)
    try {
      await processCascades(projectId)
      await loadHealth()
      onDataRefresh()
    } catch (err) {
      console.error('Failed to process cascades:', err)
    } finally {
      setIsRefreshing(false)
    }
  }, [projectId, loadHealth, onDataRefresh])

  // Don't render if loading or nothing to show
  if (isLoading) return null
  if (!health) return null

  const totalStale = health.stale_entities.total_stale
  const alertCount = health.scope_alerts.length
  if (totalStale === 0 && alertCount === 0) return null

  const summaryParts: string[] = []
  if (totalStale > 0) summaryParts.push(`${totalStale} stale`)
  if (alertCount > 0) summaryParts.push(`${alertCount} ${alertCount === 1 ? 'alert' : 'alerts'}`)

  return (
    <div className="mb-6 border border-amber-200 rounded-lg bg-amber-50/50 overflow-hidden">
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-4 py-2.5 hover:bg-amber-50/80 transition-colors"
      >
        <ChevronRight className={`w-4 h-4 text-amber-500 transition-transform ${expanded ? 'rotate-90' : ''}`} />
        <AlertTriangle className="w-4 h-4 text-amber-500" />
        <span className="text-[13px] font-medium text-amber-800">
          {summaryParts.join(', ')} need attention
        </span>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 pt-1 border-t border-amber-200/60 space-y-4">
          {/* Stale entities by type */}
          {totalStale > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[12px] font-medium text-amber-700 uppercase tracking-wide">
                  Stale Entities
                </span>
                <button
                  onClick={handleRefreshAll}
                  disabled={isRefreshing}
                  className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-amber-700 bg-amber-100 rounded hover:bg-amber-200 transition-colors disabled:opacity-50"
                >
                  {isRefreshing ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <RefreshCw className="w-3 h-3" />
                  )}
                  Refresh All
                </button>
              </div>

              {(['features', 'personas', 'vp_steps', 'data_entities', 'strategic_context'] as const).map((type) => {
                const items = health.stale_entities[type]
                if (!items || items.length === 0) return null
                return (
                  <div key={type}>
                    <span className="text-[11px] text-gray-500 font-medium">
                      {ENTITY_TYPE_LABELS[type]} ({items.length})
                    </span>
                    <div className="mt-1 space-y-1">
                      {items.map((item) => {
                        const name = 'name' in item ? item.name : ('label' in item ? item.label : item.id.slice(0, 8))
                        const entityType = type === 'features' ? 'feature'
                          : type === 'personas' ? 'persona'
                          : type === 'vp_steps' ? 'vp_step'
                          : type === 'data_entities' ? 'data_entity'
                          : 'strategic_context'
                        return (
                          <div
                            key={item.id}
                            className="flex items-center justify-between gap-2 pl-2 py-1 text-[12px] text-[#666666]"
                          >
                            <div className="flex items-center gap-1.5 min-w-0">
                              <span className="w-1.5 h-1.5 rounded-full bg-orange-400 flex-shrink-0" />
                              <span className="truncate">{name}</span>
                              {item.stale_reason && (
                                <span className="text-[10px] text-gray-400 truncate">
                                  — {item.stale_reason}
                                </span>
                              )}
                            </div>
                            <button
                              onClick={() => handleRefreshEntity(entityType, item.id)}
                              className="text-[10px] text-amber-600 hover:text-amber-800 font-medium flex-shrink-0"
                            >
                              Refresh
                            </button>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {/* Scope alerts */}
          {alertCount > 0 && (
            <div className="space-y-2">
              <span className="text-[12px] font-medium text-amber-700 uppercase tracking-wide">
                Scope Alerts
              </span>
              <div className="space-y-1.5">
                {health.scope_alerts.map((alert, i) => (
                  <AlertPill key={i} alert={alert} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
