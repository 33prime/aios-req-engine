'use client'

import { useMermaidDiagram } from '../hooks/useMermaidDiagram'
import type { WorkflowPair } from '@/types/workspace'

interface WorkflowDiagramCardProps {
  pair: WorkflowPair
  index: number
}

export function WorkflowDiagramCard({ pair, index }: WorkflowDiagramCardProps) {
  const containerId = `wf-diagram-${pair.id.slice(0, 8)}-${index}`
  const { ref, error } = useMermaidDiagram(pair, containerId)

  const currentMin = pair.current_steps.reduce((sum, s) => sum + (s.time_minutes || 0), 0)
  const futureMin = pair.future_steps.reduce((sum, s) => sum + (s.time_minutes || 0), 0)
  const savedMin = currentMin - futureMin
  const automatedCount = pair.future_steps.filter(
    (s) => s.automation_level === 'fully_automated'
  ).length
  const totalSteps = pair.future_steps.length

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#E5E5E5]">
        <span className="text-[14px] font-semibold text-[#333333]">{pair.name}</span>
        {pair.roi && pair.roi.time_saved_percent > 0 && (
          <span className="text-[12px] font-medium text-[#25785A] bg-[#E8F5E9] px-2.5 py-1 rounded-lg">
            ROI: {pair.roi.time_saved_percent}% time saved
          </span>
        )}
      </div>

      {/* Diagram */}
      <div className="px-5 py-4">
        {error ? (
          <p className="text-[12px] text-[#999999] italic py-4 text-center">{error}</p>
        ) : (
          <div
            ref={ref}
            className="overflow-x-auto [&_svg]:max-w-full [&_svg]:h-auto"
          />
        )}
      </div>

      {/* ROI footer */}
      {currentMin > 0 && (
        <div className="px-5 py-3 border-t border-[#E5E5E5] flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-[#666666]">
          <span>
            Time: {currentMin}m → {futureMin}m
            {savedMin > 0 && (
              <span className="font-medium text-[#25785A]"> (saves {savedMin}m)</span>
            )}
          </span>
          {totalSteps > 0 && (
            <span>{automatedCount}/{totalSteps} automated</span>
          )}
          {pair.roi && pair.roi.cost_saved_per_year > 0 && (
            <span>${pair.roi.cost_saved_per_year.toLocaleString()}/yr saved</span>
          )}
        </div>
      )}
    </div>
  )
}
