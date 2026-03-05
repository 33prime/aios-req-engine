'use client'

import { Users } from 'lucide-react'
import type { StakeholderIntel } from '@/types/call-intelligence'

export function StakeholderIntelSection({
  intel,
}: {
  intel: StakeholderIntel[]
}) {
  if (!intel || intel.length === 0) return null

  return (
    <div className="mt-7">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wide flex items-center gap-1.5 mb-3">
        <Users className="w-3.5 h-3.5" /> Stakeholder Intel
      </h3>
      <div className="space-y-2.5">
        {intel.map((s, i) => (
          <div key={i} className="p-3 bg-white rounded-lg border border-border">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[13px] font-semibold text-text-body">{s.name}</span>
              <span className={`px-1.5 py-0.5 text-[10px] font-semibold rounded-full ${
                s.influence === 'high' ? 'bg-red-100 text-red-700' :
                s.influence === 'medium' ? 'bg-amber-100 text-amber-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {s.influence}
              </span>
              {s.stakeholder_type && (
                <span className="text-[10px] text-text-muted">
                  {s.stakeholder_type}
                </span>
              )}
            </div>
            {s.role && <p className="text-[11px] text-text-muted">{s.role}</p>}
            {s.key_concerns.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1.5">
                {s.key_concerns.map((c, j) => (
                  <span key={j} className="px-1.5 py-0.5 text-[10px] bg-amber-50 text-amber-700 rounded">
                    {c.length > 50 ? c.slice(0, 50) + '...' : c}
                  </span>
                ))}
              </div>
            )}
            <p className="text-[11px] text-text-muted italic mt-1.5">{s.approach_notes}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
