'use client'

import { FileText } from 'lucide-react'

interface SignalReviewPanelProps {
  patches: Record<string, unknown>
}

const entityTypeLabels: Record<string, string> = {
  feature: 'Features',
  persona: 'Personas',
  stakeholder: 'Stakeholders',
  business_driver: 'Business Drivers',
  vp_step: 'Value Path Steps',
  workflow_step: 'Workflow Steps',
  constraint: 'Constraints',
  data_entity: 'Data Entities',
  competitor: 'Competitors',
}

export function SignalReviewPanel({ patches }: SignalReviewPanelProps) {
  const applied = (patches.applied as Array<Record<string, unknown>>) || []
  const total = (patches.total as number) || applied.length

  if (applied.length === 0) {
    return (
      <div className="mb-4 p-3 bg-gray-50 rounded-lg text-[13px] text-[#999]">
        No patch data available for review.
      </div>
    )
  }

  // Group by entity type
  const grouped: Record<string, Array<Record<string, unknown>>> = {}
  for (const patch of applied) {
    const type = (patch.entity_type as string) || 'unknown'
    if (!grouped[type]) grouped[type] = []
    grouped[type].push(patch)
  }

  return (
    <div className="mb-4">
      <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[#999] mb-2">
        Extracted Entities ({total})
      </h3>
      <div className="space-y-2">
        {Object.entries(grouped).map(([type, items]) => (
          <div key={type} className="bg-white border border-border rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <FileText className="w-3.5 h-3.5 text-brand-primary" />
              <span className="text-[13px] font-medium text-[#0A1E2F]">
                {entityTypeLabels[type] || type} ({items.length})
              </span>
            </div>
            <div className="space-y-1">
              {items.slice(0, 8).map((item, idx) => {
                const name = (item.name as string) || (item.entity_name as string) || 'Unnamed'
                const op = (item.operation as string) || ''
                return (
                  <div key={idx} className="flex items-center gap-2 text-[13px]">
                    <span className={`px-1.5 py-0.5 rounded text-[11px] font-medium ${
                      op === 'create' ? 'bg-brand-primary-light text-[#25785A]' :
                      op === 'merge' ? 'bg-[#0A1E2F]/5 text-[#0A1E2F]' :
                      op === 'update' ? 'bg-amber-50 text-amber-700' :
                      'bg-gray-100 text-gray-600'
                    }`}>
                      {op || 'change'}
                    </span>
                    <span className="text-[#333] truncate">{name}</span>
                  </div>
                )
              })}
              {items.length > 8 && (
                <span className="text-[12px] text-[#999]">... and {items.length - 8} more</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
