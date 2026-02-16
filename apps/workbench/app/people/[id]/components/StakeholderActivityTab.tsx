'use client'

import { Brain } from 'lucide-react'
import { AnalysisHistoryTimeline } from './StakeholderInsightsTab'

interface StakeholderActivityTabProps {
  projectId: string
  stakeholderId: string
}

export function StakeholderActivityTab({ projectId, stakeholderId }: StakeholderActivityTabProps) {
  if (!projectId || !stakeholderId) {
    return (
      <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-12 text-center">
        <div className="w-16 h-16 rounded-2xl bg-[#F4F4F4] flex items-center justify-center mx-auto mb-4">
          <Brain className="w-7 h-7 text-[#BBB]" />
        </div>
        <h3 className="text-[18px] font-semibold text-[#333] mb-1">Activity Timeline</h3>
        <p className="text-[14px] text-[#666] max-w-md mx-auto">
          No project context available to load activity data.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
      <h3 className="text-[14px] font-semibold text-[#333] mb-4">Analysis History</h3>
      <AnalysisHistoryTimeline projectId={projectId} stakeholderId={stakeholderId} />
    </div>
  )
}
