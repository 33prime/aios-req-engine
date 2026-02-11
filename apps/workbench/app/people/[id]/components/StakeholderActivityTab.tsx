'use client'

import { Activity, FileText, Check, Moon } from 'lucide-react'

export function StakeholderActivityTab() {
  return (
    <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-12 text-center">
      <div className="w-16 h-16 rounded-2xl bg-[#F4F4F4] flex items-center justify-center mx-auto mb-4">
        <Activity className="w-7 h-7 text-[#BBB]" />
      </div>
      <h3 className="text-[18px] font-semibold text-[#333] mb-1">Activity Timeline</h3>
      <p className="text-[14px] text-[#666] max-w-md mx-auto mb-8">
        A chronological feed of all interactions — signal mentions, confirmation changes, enrichment updates, and portal activity.
      </p>

      {/* Preview items at 50% opacity */}
      <div className="max-w-lg mx-auto text-left">
        <p className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-3 px-1">Preview</p>
        <div className="space-y-2.5 opacity-50">
          <div className="flex items-start gap-3 p-3.5 bg-[#F4F4F4] rounded-xl">
            <div className="w-8 h-8 rounded-xl bg-[#3FAF7A]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <FileText className="w-3.5 h-3.5 text-[#3FAF7A]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-[#333]"><span className="font-medium">Mentioned in signal</span> — Discovery Call #3</p>
              <p className="text-[11px] text-[#999] mt-0.5">2 days ago</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3.5 bg-[#F4F4F4] rounded-xl">
            <div className="w-8 h-8 rounded-xl bg-[#3FAF7A]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Check className="w-3.5 h-3.5 text-[#3FAF7A]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-[#333]"><span className="font-medium">Confirmed</span> by consultant</p>
              <p className="text-[11px] text-[#999] mt-0.5">3 days ago</p>
            </div>
          </div>
          <div className="flex items-start gap-3 p-3.5 bg-[#F4F4F4] rounded-xl">
            <div className="w-8 h-8 rounded-xl bg-[#3FAF7A]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <Moon className="w-3.5 h-3.5 text-[#3FAF7A]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[13px] text-[#333]"><span className="font-medium">AI enrichment</span> completed — added engagement strategy</p>
              <p className="text-[11px] text-[#999] mt-0.5">5 days ago</p>
            </div>
          </div>
        </div>
      </div>

      <p className="text-[12px] text-[#BBB] mt-8">Coming soon — will be part of system-wide activity infrastructure</p>
    </div>
  )
}
