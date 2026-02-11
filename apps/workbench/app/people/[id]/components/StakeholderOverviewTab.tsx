'use client'

import { Mail, Phone, Building2 } from 'lucide-react'
import type { StakeholderDetail } from '@/types/workspace'

interface StakeholderOverviewTabProps {
  stakeholder: StakeholderDetail
}

export function StakeholderOverviewTab({ stakeholder }: StakeholderOverviewTabProps) {
  const s = stakeholder

  return (
    <div className="space-y-6">
      {/* Contact Info */}
      <div>
        <h3 className="text-[13px] font-semibold text-[#37352f] mb-2">Contact Information</h3>
        <div className="space-y-2">
          {s.email && (
            <div className="flex items-center gap-2 text-[13px] text-[rgba(55,53,47,0.65)]">
              <Mail className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <a href={`mailto:${s.email}`} className="text-[#009b87] hover:underline">{s.email}</a>
            </div>
          )}
          {s.phone && (
            <div className="flex items-center gap-2 text-[13px] text-[rgba(55,53,47,0.65)]">
              <Phone className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <span>{s.phone}</span>
            </div>
          )}
          {s.organization && (
            <div className="flex items-center gap-2 text-[13px] text-[rgba(55,53,47,0.65)]">
              <Building2 className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
              <span>{s.organization}</span>
            </div>
          )}
          {!s.email && !s.phone && !s.organization && (
            <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No contact information available</p>
          )}
        </div>
      </div>

      {/* Domain Expertise */}
      {s.domain_expertise && s.domain_expertise.length > 0 && (
        <div>
          <h3 className="text-[13px] font-semibold text-[#37352f] mb-2">Domain Expertise</h3>
          <div className="flex flex-wrap gap-1.5">
            {s.domain_expertise.map((area, i) => (
              <span
                key={i}
                className="inline-flex items-center px-2.5 py-1 rounded-full text-[12px] font-medium bg-teal-50 text-teal-700"
              >
                {area}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Priorities */}
      {s.priorities && s.priorities.length > 0 && (
        <div>
          <h3 className="text-[13px] font-semibold text-[#37352f] mb-2">Priorities</h3>
          <ul className="space-y-1">
            {s.priorities.map((p, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-[rgba(55,53,47,0.65)]">
                <span className="text-[#009b87] mt-1">•</span>
                <span>{p}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Concerns */}
      {s.concerns && s.concerns.length > 0 && (
        <div>
          <h3 className="text-[13px] font-semibold text-[#37352f] mb-2">Concerns</h3>
          <ul className="space-y-1">
            {s.concerns.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-[13px] text-[rgba(55,53,47,0.65)]">
                <span className="text-orange-500 mt-1">•</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Notes */}
      {s.notes && (
        <div>
          <h3 className="text-[13px] font-semibold text-[#37352f] mb-2">Notes</h3>
          <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed whitespace-pre-wrap">{s.notes}</p>
        </div>
      )}
    </div>
  )
}
