'use client'

import { ArrowLeft, Building2, Sparkles, Loader2 } from 'lucide-react'
import type { ClientDetail } from '@/types/workspace'

interface ClientHeaderProps {
  client: ClientDetail
  enriching: boolean
  onBack: () => void
  onEnrich: () => void
}

export function ClientHeader({ client, enriching, onBack, onEnrich }: ClientHeaderProps) {
  const initials = client.name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()

  return (
    <div className="mb-6">
      {/* Back button */}
      <button
        onClick={onBack}
        className="inline-flex items-center gap-1.5 text-[13px] text-[#999] hover:text-[#666] transition-colors mb-4"
      >
        <ArrowLeft className="w-3.5 h-3.5" />
        Back to Clients
      </button>

      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          {client.logo_url ? (
            <img
              src={client.logo_url}
              alt={client.name}
              className="w-14 h-14 rounded-2xl object-cover"
            />
          ) : (
            <div className="w-14 h-14 rounded-2xl bg-[#F0F0F0] flex items-center justify-center">
              <span className="text-[18px] font-semibold text-[#666]">{initials}</span>
            </div>
          )}
          <div>
            <h1 className="text-[22px] font-bold text-[#333]">{client.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              {client.industry && (
                <span className="px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                  {client.industry}
                </span>
              )}
              {client.stage && (
                <span className="px-2 py-0.5 text-[11px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                  {client.stage.charAt(0).toUpperCase() + client.stage.slice(1)}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Enrich button */}
        <button
          onClick={onEnrich}
          disabled={enriching}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
        >
          {enriching ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Sparkles className="w-3.5 h-3.5" />
          )}
          {enriching ? 'Enriching...' : 'Enrich'}
        </button>
      </div>
    </div>
  )
}
