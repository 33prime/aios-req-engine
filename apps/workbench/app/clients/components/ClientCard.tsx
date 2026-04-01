'use client'

import { Building2, FolderKanban, Users, CheckCircle2, Loader2, Minus } from 'lucide-react'
import type { ClientSummary } from '@/types/workspace'

interface ClientCardProps {
  client: ClientSummary
  onClick: () => void
}

function EnrichmentIndicator({ status }: { status: string }) {
  if (status === 'completed') {
    return <CheckCircle2 className="w-3.5 h-3.5 text-brand-primary" />
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
      className="w-full text-left bg-white rounded-xl border border-border shadow-sm p-5 hover:shadow-md hover:border-brand-primary/30 transition-all duration-200 group"
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
          <h3 className="text-[14px] font-semibold text-[#333] truncate group-hover:text-brand-primary transition-colors">
            {client.name}
          </h3>
          {client.industry && (
            <span className="inline-block mt-1 px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
              {client.industry}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          {client.company_summary && (client.company_summary.includes('due to limited') || client.company_summary.includes('appears to be') || client.company_summary.includes('cannot be confirmed')) && (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 font-medium">Needs input</span>
          )}
          <EnrichmentIndicator status={client.enrichment_status} />
        </div>
      </div>

      {/* Metrics row + completeness */}
      <div className="flex items-center gap-4 mb-3">
        <div className="flex items-center gap-1.5 text-[12px] text-[#666]">
          <FolderKanban className="w-3 h-3" />
          <span>{client.project_count} {client.project_count === 1 ? 'project' : 'projects'}</span>
        </div>
        <div className="flex items-center gap-1.5 text-[12px] text-[#666]">
          <Users className="w-3 h-3" />
          <span>{client.stakeholder_count} {client.stakeholder_count === 1 ? 'stakeholder' : 'stakeholders'}</span>
        </div>
        {client.profile_completeness != null && (
          <div className="flex items-center gap-1.5 ml-auto">
            <div className="w-12 h-1 bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${client.profile_completeness >= 70 ? 'bg-brand-primary' : client.profile_completeness >= 40 ? 'bg-emerald-300' : 'bg-gray-300'}`}
                style={{ width: `${Math.min(client.profile_completeness, 100)}%` }}
              />
            </div>
            <span className="text-[10px] text-[#999] tabular-nums">{Math.round(client.profile_completeness)}%</span>
          </div>
        )}
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
