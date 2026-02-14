'use client'

import {
  Globe,
  MapPin,
  Calendar,
  Users,
  DollarSign,
  Cpu,
  TrendingUp,
  Swords,
  Sparkles,
} from 'lucide-react'
import type { ClientDetail } from '@/types/workspace'

interface ClientOverviewTabProps {
  client: ClientDetail
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3 py-2">
      <span className="text-[#999] mt-0.5">{icon}</span>
      <div>
        <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide">{label}</p>
        <p className="text-[13px] text-[#333]">{value}</p>
      </div>
    </div>
  )
}

function MaturityBadge({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  const display = value.replace('_', ' ')
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-[12px] text-[#666]">{label}</span>
      <span className="px-2 py-0.5 text-[11px] font-medium text-[#25785A] bg-[#E8F5E9] rounded-md capitalize">
        {display}
      </span>
    </div>
  )
}

export function ClientOverviewTab({ client }: ClientOverviewTabProps) {
  const hasEnrichment = client.enrichment_status === 'completed'

  return (
    <div className="space-y-6">
      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Company Details */}
        <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-6">
          <h3 className="text-[14px] font-semibold text-[#333] mb-4">Company Details</h3>
          <div className="space-y-1">
            {client.website && (
              <InfoRow
                icon={<Globe className="w-3.5 h-3.5" />}
                label="Website"
                value={client.website}
              />
            )}
            {client.headquarters && (
              <InfoRow
                icon={<MapPin className="w-3.5 h-3.5" />}
                label="Headquarters"
                value={client.headquarters}
              />
            )}
            {client.founding_year && (
              <InfoRow
                icon={<Calendar className="w-3.5 h-3.5" />}
                label="Founded"
                value={String(client.founding_year)}
              />
            )}
            {client.employee_count && (
              <InfoRow
                icon={<Users className="w-3.5 h-3.5" />}
                label="Employees"
                value={client.employee_count.toLocaleString()}
              />
            )}
            {client.revenue_range && (
              <InfoRow
                icon={<DollarSign className="w-3.5 h-3.5" />}
                label="Revenue"
                value={client.revenue_range}
              />
            )}
            {client.size && (
              <InfoRow
                icon={<Users className="w-3.5 h-3.5" />}
                label="Size"
                value={`${client.size} employees`}
              />
            )}
            {client.description && (
              <div className="pt-3 mt-2 border-t border-[#E5E5E5]">
                <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Description</p>
                <p className="text-[13px] text-[#666] leading-relaxed">{client.description}</p>
              </div>
            )}
          </div>
        </div>

        {/* Right: AI Intelligence */}
        <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-6">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-[#3FAF7A]" />
            <h3 className="text-[14px] font-semibold text-[#333]">AI Intelligence</h3>
          </div>

          {!hasEnrichment ? (
            <div className="text-center py-8">
              <Sparkles className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
              <p className="text-[13px] text-[#666] mb-1">No enrichment data yet</p>
              <p className="text-[12px] text-[#999]">
                Enrich this client to get AI-powered insights
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {/* Summary */}
              {client.company_summary && (
                <div>
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Summary</p>
                  <p className="text-[13px] text-[#333] leading-relaxed">{client.company_summary}</p>
                </div>
              )}

              {/* Market Position */}
              {client.market_position && (
                <div className="pt-2">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Market Position</p>
                  <p className="text-[13px] text-[#666] leading-relaxed">{client.market_position}</p>
                </div>
              )}

              {/* Maturity badges */}
              <div className="pt-2 border-t border-[#E5E5E5]">
                <MaturityBadge label="Technology Maturity" value={client.technology_maturity} />
                <MaturityBadge label="Digital Readiness" value={client.digital_readiness} />
              </div>

              {/* Innovation score */}
              {client.innovation_score != null && (
                <div className="pt-2 border-t border-[#E5E5E5]">
                  <div className="flex items-center justify-between">
                    <span className="text-[12px] text-[#666]">Innovation Score</span>
                    <span className="text-[13px] font-semibold text-[#3FAF7A]">
                      {Math.round(client.innovation_score * 100)}%
                    </span>
                  </div>
                  <div className="mt-1 h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#3FAF7A] rounded-full transition-all"
                      style={{ width: `${client.innovation_score * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Tech Stack */}
      {client.tech_stack && client.tech_stack.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-6">
          <div className="flex items-center gap-2 mb-3">
            <Cpu className="w-4 h-4 text-[#666]" />
            <h3 className="text-[14px] font-semibold text-[#333]">Tech Stack</h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {client.tech_stack.map((tech, i) => (
              <span
                key={i}
                className="px-3 py-1 text-[12px] font-medium text-[#666] bg-[#F0F0F0] rounded-lg"
              >
                {tech}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Growth Signals */}
      {client.growth_signals && client.growth_signals.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-6">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp className="w-4 h-4 text-[#666]" />
            <h3 className="text-[14px] font-semibold text-[#333]">Growth Signals</h3>
          </div>
          <div className="space-y-2">
            {client.growth_signals.map((gs, i) => (
              <div key={i} className="flex items-start gap-3 py-2">
                <span className="px-2 py-0.5 text-[10px] font-medium text-[#666] bg-[#F0F0F0] rounded-md uppercase flex-shrink-0">
                  {gs.type}
                </span>
                <p className="text-[13px] text-[#333]">{gs.signal}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Competitors */}
      {client.competitors && client.competitors.length > 0 && (
        <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-6">
          <div className="flex items-center gap-2 mb-3">
            <Swords className="w-4 h-4 text-[#666]" />
            <h3 className="text-[14px] font-semibold text-[#333]">Competitors</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {client.competitors.map((comp, i) => (
              <div
                key={i}
                className="p-3 bg-[#FAFAFA] rounded-xl border border-[#E5E5E5]"
              >
                <p className="text-[13px] font-medium text-[#333]">{comp.name}</p>
                <p className="text-[12px] text-[#666] mt-0.5">{comp.relationship}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
