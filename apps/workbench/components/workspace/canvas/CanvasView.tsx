'use client'

import { useState, useEffect, useCallback } from 'react'
import { Cpu, RefreshCw } from 'lucide-react'
import { CanvasActorsRow } from './CanvasActorsRow'
import { ValuePathSection } from './ValuePathSection'
import { ActorJourneySection } from './ActorJourneySection'
import { MvpFeaturesSection } from './MvpFeaturesSection'
import { getCanvasViewData, triggerValuePathSynthesis } from '@/lib/api'
import type { CanvasViewData } from '@/types/workspace'

interface CanvasViewProps {
  projectId: string
  onRefresh?: () => void
}

export function CanvasView({ projectId, onRefresh }: CanvasViewProps) {
  const [data, setData] = useState<CanvasViewData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const [selectedActorId, setSelectedActorId] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const result = await getCanvasViewData(projectId)
      setData(result)
    } catch (err) {
      console.error('Failed to load canvas view data:', err)
      setError('Failed to load canvas data')
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSynthesize = useCallback(async () => {
    try {
      setIsSynthesizing(true)
      await triggerValuePathSynthesis(projectId)
      await loadData()
    } catch (err) {
      console.error('Failed to synthesize value path:', err)
    } finally {
      setIsSynthesizing(false)
    }
  }, [projectId, loadData])

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#3FAF7A] mx-auto mb-3" />
        <p className="text-[13px] text-[#999999]">Loading Canvas View...</p>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="max-w-5xl mx-auto py-16 text-center">
        <p className="text-red-500 mb-3">{error || 'No data available'}</p>
        <button
          onClick={loadData}
          className="px-4 py-2 text-sm text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
        >
          Retry
        </button>
      </div>
    )
  }

  const hasActors = data.actors.length > 0
  const hasValuePath = data.value_path.length > 0

  return (
    <div className="max-w-5xl mx-auto py-8 px-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Cpu className="w-6 h-6 text-[#3FAF7A]" />
          <div>
            <h1 className="text-[24px] font-bold text-[#333333]">Prototype Blueprint</h1>
            <p className="text-[13px] text-[#999999] mt-0.5">
              Technical translation of your BRD — the data needed to build the prototype
            </p>
          </div>
        </div>
        <button
          onClick={() => { loadData(); onRefresh?.() }}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-[#666666] bg-white border border-[#E5E5E5] rounded-xl hover:bg-gray-50 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Empty state when no actors selected */}
      {!hasActors && (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-12 text-center">
          <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-[#F4F4F4] flex items-center justify-center">
            <Cpu className="w-7 h-7 text-[#999999]" />
          </div>
          <h3 className="text-[16px] font-semibold text-[#333333] mb-2">No canvas actors selected</h3>
          <p className="text-[13px] text-[#666666] max-w-md mx-auto">
            Switch to BRD View and click the star icon on personas to select them as canvas actors
            (max 2 primary + 1 secondary). Then return here to synthesize the value path.
          </p>
        </div>
      )}

      {/* Canvas sections */}
      {hasActors && (
        <div className="space-y-8">
          {/* Actors Row */}
          <CanvasActorsRow
            actors={data.actors}
            onSynthesize={handleSynthesize}
            isSynthesizing={isSynthesizing}
            synthesisStale={data.synthesis_stale}
            hasValuePath={hasValuePath}
            onActorClick={setSelectedActorId}
            selectedActorId={selectedActorId}
          />

          {/* Value Path */}
          <ValuePathSection
            steps={data.value_path}
            rationale={data.synthesis_rationale}
            isStale={data.synthesis_stale}
            onRegenerate={handleSynthesize}
            isSynthesizing={isSynthesizing}
          />

          {/* Actor Journey (drill-down) */}
          <ActorJourneySection
            workflowPairs={data.workflow_pairs}
            selectedActorId={selectedActorId}
            actors={data.actors}
          />

          {/* MVP Features */}
          <MvpFeaturesSection features={data.mvp_features} />
        </div>
      )}
    </div>
  )
}
