'use client'

import { Building2, FolderKanban, Users, CheckCircle2, Loader2, Minus } from 'lucide-react'
import type { ClientSummary } from '@/types/workspace'

interface ClientCardProps {
  client: ClientSummary
  onClick: () => void
}

function EnrichmentIndicator({ status }: { status: string }) {
  if (status === 'completed') {
    return <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A]" />
  }
  if (status === 'in_progress') {
    return <Loader2 className="w-3.5 h-3.5 text-[#999] animate-spin" />
  }
  return <Minus className="w-3.5 h-3.5 text-[#CCC]" />
}

export function ClientCard({ client, onClick }: ClientCardProps) {
  const initials = client.name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-6 hover:shadow-lg hover:border-[#3FAF7A]/30 transition-all duration-200 group"
    >
      {/* Top row: avatar + name + enrichment */}
      <div className="flex items-start gap-3 mb-3">
        {client.logo_url ? (
          <img
            src={client.logo_url}
            alt={client.name}
            className="w-10 h-10 rounded-xl object-cover flex-shrink-0"
          />
        ) : (
          <div className="w-10 h-10 rounded-xl bg-[#F0F0F0] flex items-center justify-center flex-shrink-0">
            <span className="text-[13px] font-semibold text-[#666]">{initials}</span>
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h3 className="text-[14px] font-semibold text-[#333] truncate group-hover:text-[#3FAF7A] transition-colors">
            {client.name}
          </h3>
          {client.industry && (
            <span className="inline-block mt-1 px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
              {client.industry}
            </span>
          )}
        </div>
        <EnrichmentIndicator status={client.enrichment_status} />
      </div>

      {/* Metrics row */}
      <div className="flex items-center gap-4 mb-3">
        <div className="flex items-center gap-1.5 text-[12px] text-[#666]">
          <FolderKanban className="w-3 h-3" />
          <span>{client.project_count} {client.project_count === 1 ? 'project' : 'projects'}</span>
        </div>
        <div className="flex items-center gap-1.5 text-[12px] text-[#666]">
          <Users className="w-3 h-3" />
          <span>{client.stakeholder_count} {client.stakeholder_count === 1 ? 'stakeholder' : 'stakeholders'}</span>
        </div>
      </div>

      {/* Summary */}
      {client.company_summary ? (
        <p className="text-[12px] text-[#666] line-clamp-2 leading-relaxed">
          {client.company_summary}
        </p>
      ) : (
        <p className="text-[12px] text-[#999] italic">
          No summary yet — enrich to get AI insights
        </p>
      )}
    </button>
  )
}
