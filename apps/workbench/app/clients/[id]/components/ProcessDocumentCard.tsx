'use client'

import { FileText, ArrowRight } from 'lucide-react'
import type { ProcessDocumentSummary } from '@/types/workspace'

interface ProcessDocumentCardProps {
  doc: ProcessDocumentSummary
  onClick: (doc: ProcessDocumentSummary) => void
}

const STATUS_STYLES: Record<string, { bg: string; text: string }> = {
  draft: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  review: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  confirmed: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  archived: { bg: 'bg-[#F0F0F0]', text: 'text-[#999]' },
}

const SCENARIO_LABELS: Record<string, string> = {
  reconstruct: 'Reconstructed',
  generate: 'Generated',
  tribal_capture: 'Tribal Capture',
}

export function ProcessDocumentCard({ doc, onClick }: ProcessDocumentCardProps) {
  const status = STATUS_STYLES[doc.status] || STATUS_STYLES.draft
  const scenario = doc.generation_scenario ? SCENARIO_LABELS[doc.generation_scenario] : null

  return (
    <button
      onClick={() => onClick(doc)}
      className="w-full text-left bg-white rounded-xl border border-[#E5E5E5] p-4 hover:border-[#3FAF7A] hover:shadow-sm transition-all group"
    >
      <div className="flex items-start gap-3">
        <div className="p-2 bg-[#F4F4F4] rounded-lg group-hover:bg-[#E8F5E9] transition-colors">
          <FileText className="w-4 h-4 text-[#666] group-hover:text-[#3FAF7A] transition-colors" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-[#333] line-clamp-1">{doc.title}</p>
          <div className="flex items-center gap-1.5 mt-1.5">
            <span className={`px-1.5 py-0.5 text-[9px] font-medium rounded ${status.bg} ${status.text}`}>
              {doc.status}
            </span>
            {scenario && (
              <span className="px-1.5 py-0.5 text-[9px] font-medium rounded bg-[#F0F0F0] text-[#666]">
                {scenario}
              </span>
            )}
            <span className="text-[10px] text-[#999]">
              {doc.step_count} steps &middot; {doc.role_count} roles
            </span>
          </div>
        </div>
        <ArrowRight className="w-4 h-4 text-[#CCC] group-hover:text-[#3FAF7A] transition-colors flex-shrink-0 mt-1" />
      </div>
    </button>
  )
}
