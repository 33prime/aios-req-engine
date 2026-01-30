/**
 * MemoryPanel - Memory & Intelligence view
 *
 * 5 tabs: Overview, Knowledge Graph, Connections, Evolution, For AI
 * Replaces the old HistoryPanel with rich graph/belief visualization.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { BarChart3, Share2, GitBranch, History, Code, RefreshCw } from 'lucide-react'
import {
  getMemoryVisualization,
  getUnifiedMemory,
  refreshUnifiedMemory,
} from '@/lib/api'
import type { MemoryVisualizationResponse, UnifiedMemoryResponse } from '@/lib/api'
import { OverviewTab } from './OverviewTab'
import { GraphTab } from './GraphTab'
import { ConnectionsTab } from './ConnectionsTab'
import { EvolutionTab } from './EvolutionTab'
import { ContextWindowTab } from './ContextWindowTab'

interface MemoryPanelProps {
  projectId: string
}

type MemoryTab = 'overview' | 'graph' | 'connections' | 'evolution' | 'context'

const TABS = [
  { id: 'overview' as const, icon: BarChart3, label: 'Overview' },
  { id: 'graph' as const, icon: Share2, label: 'Knowledge Graph' },
  { id: 'connections' as const, icon: GitBranch, label: 'Connections' },
  { id: 'evolution' as const, icon: History, label: 'Evolution' },
  { id: 'context' as const, icon: Code, label: 'For AI' },
]

export function MemoryPanel({ projectId }: MemoryPanelProps) {
  const [activeTab, setActiveTab] = useState<MemoryTab>('overview')
  const [vizData, setVizData] = useState<MemoryVisualizationResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const [unifiedMemory, setUnifiedMemory] = useState<UnifiedMemoryResponse | null>(null)

  useEffect(() => {
    getMemoryVisualization(projectId)
      .then(setVizData)
      .catch(() => setVizData(null))
      .finally(() => setIsLoading(false))
  }, [projectId])

  // Lazy-load unified memory when context tab is activated
  useEffect(() => {
    if (activeTab === 'context' && !unifiedMemory) {
      getUnifiedMemory(projectId)
        .then(setUnifiedMemory)
        .catch(() => setUnifiedMemory(null))
    }
  }, [activeTab, projectId, unifiedMemory])

  const handleSynthesize = useCallback(async () => {
    setIsSynthesizing(true)
    try {
      const result = await refreshUnifiedMemory(projectId)
      setUnifiedMemory(result)
    } catch {
      // Synthesis may fail if no data
    } finally {
      setIsSynthesizing(false)
    }
  }, [projectId])

  const freshnessLabel = unifiedMemory?.freshness?.age_human || null

  return (
    <div>
      {/* Tab bar + header actions */}
      <div className="flex items-center justify-between mb-4 -mt-1">
        <div className="flex gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                  isActive
                    ? 'bg-brand-teal/10 text-brand-teal'
                    : 'text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>

        {/* Header actions */}
        <div className="flex items-center gap-2">
          {freshnessLabel && (
            <span className="text-[11px] text-ui-supportText">
              Synthesized {freshnessLabel}
            </span>
          )}
          <button
            onClick={handleSynthesize}
            disabled={isSynthesizing}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-brand-teal hover:bg-brand-teal/10 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isSynthesizing ? 'animate-spin' : ''}`} />
            Synthesize
          </button>
        </div>
      </div>

      {/* Loading state */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-teal" />
        </div>
      ) : (
        <>
          {activeTab === 'overview' && <OverviewTab projectId={projectId} data={vizData} />}
          {activeTab === 'graph' && <GraphTab data={vizData} />}
          {activeTab === 'connections' && <ConnectionsTab data={vizData} />}
          {activeTab === 'evolution' && <EvolutionTab projectId={projectId} data={vizData} />}
          {activeTab === 'context' && (
            <ContextWindowTab
              projectId={projectId}
              unifiedMemory={unifiedMemory}
              onRefresh={handleSynthesize}
              isSynthesizing={isSynthesizing}
            />
          )}
        </>
      )}
    </div>
  )
}
