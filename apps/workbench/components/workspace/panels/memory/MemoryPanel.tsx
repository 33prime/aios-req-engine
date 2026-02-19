/**
 * MemoryPanel — Intelligence Module (upgraded)
 *
 * 5 tabs: Overview, Knowledge, Evolution, Evidence, Sales
 * Near-full-screen (95vw x 90vh) — managed by BottomDock.
 * "For AI" overlay accessible via utility button.
 */

'use client'

import { useState, useCallback } from 'react'
import { BarChart3, Share2, History, FileSearch, DollarSign, Code, RefreshCw } from 'lucide-react'
import { refreshUnifiedMemory } from '@/lib/api'
import { useMemoryVisualization, useUnifiedMemory } from '@/lib/hooks/use-api'
import { OverviewTab } from './OverviewTab'
import { KnowledgeTab } from './KnowledgeTab'
import { EvolutionTab } from './EvolutionTab'
import { EvidenceTab } from './EvidenceTab'
import { SalesTab } from './SalesTab'
import { ContextWindowTab } from './ContextWindowTab'

interface MemoryPanelProps {
  projectId: string
}

type MemoryTab = 'overview' | 'knowledge' | 'evolution' | 'evidence' | 'sales'

const TABS = [
  { id: 'overview' as const, icon: BarChart3, label: 'Overview' },
  { id: 'knowledge' as const, icon: Share2, label: 'Knowledge' },
  { id: 'evolution' as const, icon: History, label: 'Evolution' },
  { id: 'evidence' as const, icon: FileSearch, label: 'Evidence' },
  { id: 'sales' as const, icon: DollarSign, label: 'Sales' },
]

export function MemoryPanel({ projectId }: MemoryPanelProps) {
  const [activeTab, setActiveTab] = useState<MemoryTab>('overview')
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const [showForAI, setShowForAI] = useState(false)

  const { data: vizData, isLoading } = useMemoryVisualization(projectId)
  const { data: unifiedMemory, mutate: mutateUnifiedMemory } = useUnifiedMemory(
    showForAI ? projectId : undefined,
  )

  const handleSynthesize = useCallback(async () => {
    setIsSynthesizing(true)
    try {
      const result = await refreshUnifiedMemory(projectId)
      mutateUnifiedMemory(result, false)
    } catch {
      // Synthesis may fail if no data
    } finally {
      setIsSynthesizing(false)
    }
  }, [projectId, mutateUnifiedMemory])

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar + utility actions */}
      <div className="flex items-center justify-between px-6 py-3 border-b border-ui-cardBorder bg-white shrink-0">
        <div className="flex gap-1">
          {TABS.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => { setActiveTab(tab.id); setShowForAI(false) }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                  isActive && !showForAI
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

        {/* Utility actions */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowForAI(!showForAI)}
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium rounded-lg transition-colors ${
              showForAI
                ? 'bg-brand-teal/10 text-brand-teal'
                : 'text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background'
            }`}
          >
            <Code className="w-3 h-3" />
            For AI
          </button>
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

      {/* Content area — flex-1 fills remaining space */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-teal" />
          </div>
        ) : showForAI ? (
          <div className="h-full overflow-y-auto p-6">
            <ContextWindowTab
              projectId={projectId}
              unifiedMemory={unifiedMemory ?? null}
              onRefresh={handleSynthesize}
              isSynthesizing={isSynthesizing}
            />
          </div>
        ) : (
          <>
            {activeTab === 'overview' && (
              <div className="h-full overflow-y-auto p-6">
                <OverviewTab projectId={projectId} data={vizData ?? null} />
              </div>
            )}
            {activeTab === 'knowledge' && (
              <KnowledgeTab projectId={projectId} data={vizData ?? null} />
            )}
            {activeTab === 'evolution' && (
              <div className="h-full overflow-y-auto p-6">
                <EvolutionTab projectId={projectId} data={vizData ?? null} />
              </div>
            )}
            {activeTab === 'evidence' && (
              <div className="h-full overflow-y-auto p-6">
                <EvidenceTab projectId={projectId} />
              </div>
            )}
            {activeTab === 'sales' && (
              <div className="h-full overflow-y-auto p-6">
                <SalesTab projectId={projectId} />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
