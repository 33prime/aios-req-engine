'use client'

import { Building2, FolderKanban, Users, CheckCircle2, Loader2, Minus } from 'lucide-react'
import type { ClientSummary } from '@/types/workspace'

interface ClientRowProps {
  client: ClientSummary
  onClick: () => void
}

function EnrichmentDot({ status }: { status: string }) {
  if (status === 'completed') return <span className="w-2 h-2 rounded-full bg-brand-primary inline-block" />
  if (status === 'in_progress') return <Loader2 className="w-3 h-3 text-[#999] animate-spin" />
  return <span className="w-2 h-2 rounded-full bg-gray-300 inline-block" />
}

function CompletenessBar({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-xs text-[#999]">&mdash;</span>
  const rounded = Math.round(value)
  const color = rounded >= 70 ? 'bg-brand-primary' : rounded >= 40 ? 'bg-emerald-300' : 'bg-gray-300'
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${Math.min(rounded, 100)}%` }} />
      </div>
      <span className="text-xs text-text-body tabular-nums">{rounded}%</span>
    </div>
  )
}

export function ClientRow({ client, onClick }: ClientRowProps) {
  const initials = client.name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()

  const isLowQualitySummary = client.company_summary &&
    (client.company_summary.includes('due to limited') ||
     client.company_summary.includes('appears to be') ||
     client.company_summary.includes('cannot be confirmed'))

  return (
    <tr onClick={onClick} className="hover:bg-surface-page cursor-pointer transition-colors">
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-2.5">
          {client.logo_url ? (
            <img src={client.logo_url} alt="" className="w-7 h-7 rounded-lg object-cover flex-shrink-0" />
          ) : (
            <div className="w-7 h-7 rounded-lg bg-[#F0F0F0] flex items-center justify-center flex-shrink-0">
              <span className="text-[10px] font-semibold text-[#666]">{initials}</span>
            </div>
          )}
          <span className="text-xs font-medium text-text-body truncate">{client.name}</span>
        </div>
      </td>
      <td className="px-3 py-2.5">
        {client.industry ? (
          <span className="text-[10px] px-2 py-0.5 rounded-md bg-[#F0F0F0] text-[#666] font-medium">
            {client.industry}
          </span>
        ) : (
          <span className="text-xs text-[#999]">-</span>
        )}
      </td>
      <td className="px-3 py-2.5 text-center">
        <span className="text-xs text-text-body tabular-nums">{client.project_count}</span>
      </td>
      <td className="px-3 py-2.5 text-center">
        <span className="text-xs text-text-body tabular-nums">{client.stakeholder_count}</span>
      </td>
      <td className="px-3 py-2.5">
        <CompletenessBar value={client.profile_completeness} />
      </td>
      <td className="px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <EnrichmentDot status={client.enrichment_status} />
          {isLowQualitySummary && (
            <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-600 font-medium">
              Needs input
            </span>
          )}
        </div>
      </td>
    </tr>
  )
}
