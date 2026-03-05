'use client'

import { AlertTriangle } from 'lucide-react'
import type { CriticalRequirement } from '@/types/call-intelligence'

const TYPE_BADGES: Record<string, { bg: string; text: string }> = {
  feature: { bg: 'bg-purple-50', text: 'text-purple-700' },
  vp_step: { bg: 'bg-blue-50', text: 'text-blue-700' },
  persona: { bg: 'bg-emerald-50', text: 'text-emerald-700' },
}

const STATUS_LABELS: Record<string, { bg: string; text: string; label: string }> = {
  ai_generated: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'Unconfirmed' },
  needs_confirmation: { bg: 'bg-amber-50', text: 'text-amber-700', label: 'Needs Confirmation' },
  confirmed_consultant: { bg: 'bg-blue-50', text: 'text-blue-700', label: 'Consultant Confirmed' },
  confirmed_client: { bg: 'bg-green-50', text: 'text-green-700', label: 'Client Confirmed' },
}

export function CriticalRequirementsSection({
  requirements,
}: {
  requirements: CriticalRequirement[]
}) {
  if (!requirements || requirements.length === 0) return null

  return (
    <div className="mt-7">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5 mb-3">
        <AlertTriangle className="w-3.5 h-3.5" /> Critical Requirements
      </h3>
      <div className="space-y-2.5">
        {requirements.map((req, i) => {
          const typeBadge = TYPE_BADGES[req.entity_type] || TYPE_BADGES.feature
          const statusBadge = STATUS_LABELS[req.status] || STATUS_LABELS.ai_generated
          return (
            <div key={i} className="p-3 bg-white rounded-lg border border-border">
              <div className="flex items-center gap-2 mb-1.5">
                <span className={`px-1.5 py-0.5 text-[10px] font-semibold rounded ${typeBadge.bg} ${typeBadge.text}`}>
                  {req.entity_type === 'vp_step' ? 'workflow' : req.entity_type}
                </span>
                <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded ${statusBadge.bg} ${statusBadge.text}`}>
                  {statusBadge.label}
                </span>
              </div>
              <p className="text-[13px] font-medium text-text-body">{req.name}</p>
              {req.context && (
                <p className="text-[11px] text-text-muted mt-1">{req.context}</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
