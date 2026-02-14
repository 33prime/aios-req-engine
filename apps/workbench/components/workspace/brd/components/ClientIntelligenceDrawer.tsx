'use client'

import { useState, useEffect } from 'react'
import {
  X,
  Building2,
  Users,
  Target,
  HelpCircle,
  Globe,
  Server,
  TrendingUp,
  Clock,
  ChevronDown,
  ChevronRight,
  Shield,
} from 'lucide-react'
import { getProjectClientIntelligence } from '@/lib/api'
import type { ClientIntelligenceData } from '@/types/workspace'

interface ClientIntelligenceDrawerProps {
  projectId: string
  onClose: () => void
}

function formatDate(dateStr: string) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function FreshnessBadge({ dateStr }: { dateStr?: string | null }) {
  if (!dateStr) return null
  const d = new Date(dateStr)
  const daysAgo = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24))
  const label = daysAgo === 0 ? 'Today' : daysAgo === 1 ? '1 day ago' : `${daysAgo} days ago`
  const color = daysAgo <= 7 ? 'text-[#25785A] bg-[#E8F5E9]' : daysAgo <= 30 ? 'text-[#666666] bg-[#F0F0F0]' : 'text-[#999999] bg-[#F0F0F0]'

  return (
    <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded ${color}`}>
      <Clock className="w-2.5 h-2.5" />
      {label}
    </span>
  )
}

function SourceBadge({ source }: { source?: string | null }) {
  if (!source) return null
  const labels: Record<string, string> = {
    website_scrape: 'Website',
    ai_inference: 'AI',
    client_portal: 'Client Portal',
    manual: 'Manual',
  }
  return (
    <span className="text-[10px] text-[#999999] bg-[#F0F0F0] px-1.5 py-0.5 rounded">
      {labels[source] || source}
    </span>
  )
}

function AccordionSection({
  title,
  icon: Icon,
  defaultOpen,
  badge,
  children,
}: {
  title: string
  icon: typeof Building2
  defaultOpen?: boolean
  badge?: React.ReactNode
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(defaultOpen ?? false)

  return (
    <div className="border border-[#E5E5E5] rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50/50 transition-colors"
      >
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
        )}
        <Icon className="w-4 h-4 text-[#3FAF7A] flex-shrink-0" />
        <span className="text-[13px] font-semibold text-[#333333] flex-1 text-left">{title}</span>
        {badge}
      </button>
      {open && (
        <div className="px-4 pb-4 pt-1 border-t border-[#E5E5E5]">
          {children}
        </div>
      )}
    </div>
  )
}

function FieldRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null
  return (
    <div className="flex items-start gap-2 text-[13px]">
      <span className="text-[#999999] min-w-[120px] flex-shrink-0">{label}</span>
      <span className="text-[#333333]">{value}</span>
    </div>
  )
}

function TagList({ items, emptyText }: { items?: (string | null)[] | null; emptyText?: string }) {
  const filtered = (items || []).filter(Boolean) as string[]
  if (filtered.length === 0) {
    return emptyText ? <p className="text-[12px] text-[#999999] italic">{emptyText}</p> : null
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {filtered.map((item, i) => (
        <span key={i} className="px-2 py-0.5 text-[11px] bg-[#F0F0F0] text-[#666666] rounded-full">
          {item}
        </span>
      ))}
    </div>
  )
}

export function ClientIntelligenceDrawer({
  projectId,
  onClose,
}: ClientIntelligenceDrawerProps) {
  const [data, setData] = useState<ClientIntelligenceData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getProjectClientIntelligence(projectId)
      .then((result) => {
        if (!cancelled) setData(result)
      })
      .catch((err) => {
        console.error('Failed to load client intelligence:', err)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [projectId])

  const cp = data?.company_profile || {}
  const cd = data?.client_data || {}
  const sc = data?.strategic_context || {}
  const oq = data?.open_questions || []

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[560px] max-w-full bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex-shrink-0 border-b border-[#E5E5E5] px-6 py-4">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3 min-w-0 flex-1">
              <div className="w-8 h-8 rounded-full bg-[#0A1E2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                <Building2 className="w-4 h-4 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">
                  Client Intelligence
                </p>
                <h2 className="text-[15px] font-semibold text-[#333333] leading-snug">
                  {cp.name || cd.name || 'Background & Context'}
                </h2>
                {cd.profile_completeness != null && cd.profile_completeness > 0 && (
                  <div className="flex items-center gap-2 mt-1.5">
                    <div className="w-20 h-1.5 bg-[#F0F0F0] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#3FAF7A] rounded-full"
                        style={{ width: `${cd.profile_completeness}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-[#999999]">{cd.profile_completeness}% complete</span>
                  </div>
                )}
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors flex-shrink-0"
            >
              <X className="w-4 h-4 text-[#999999]" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
            </div>
          ) : (
            <div className="space-y-3">
              {/* Company Profile */}
              <AccordionSection
                title="Company Profile"
                icon={Building2}
                defaultOpen
                badge={
                  <div className="flex items-center gap-1.5">
                    <SourceBadge source={cp.enrichment_source} />
                    <FreshnessBadge dateStr={cp.enriched_at} />
                  </div>
                }
              >
                <div className="space-y-2">
                  <FieldRow label="Industry" value={cp.industry_display || cp.industry} />
                  <FieldRow label="Company Type" value={cp.company_type} />
                  <FieldRow label="Stage" value={cp.stage} />
                  <FieldRow label="Size" value={cp.size} />
                  <FieldRow label="Revenue" value={cp.revenue} />
                  <FieldRow label="Employees" value={cp.employee_count} />
                  <FieldRow label="Location" value={cp.location} />
                  {cp.website && (
                    <div className="flex items-start gap-2 text-[13px]">
                      <span className="text-[#999999] min-w-[120px] flex-shrink-0">Website</span>
                      <span className="text-[#3FAF7A] flex items-center gap-1">
                        <Globe className="w-3 h-3" />
                        {cp.website}
                      </span>
                    </div>
                  )}
                  {cp.description && (
                    <div className="mt-2">
                      <p className="text-[13px] text-[#666666] leading-relaxed">{cp.description}</p>
                    </div>
                  )}
                  {cp.unique_selling_point && (
                    <div className="mt-2 bg-[#F9F9F9] rounded-lg p-3">
                      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Unique Selling Point</p>
                      <p className="text-[13px] text-[#333333]">{cp.unique_selling_point}</p>
                    </div>
                  )}
                </div>
              </AccordionSection>

              {/* Organizational Context (from client enrichment) */}
              {data?.has_client && (
                <AccordionSection
                  title="Organizational Context"
                  icon={Users}
                  badge={<FreshnessBadge dateStr={cd.last_analyzed_at} />}
                >
                  <div className="space-y-3">
                    {cd.company_summary && (
                      <div>
                        <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Summary</p>
                        <p className="text-[13px] text-[#666666] leading-relaxed">{cd.company_summary}</p>
                      </div>
                    )}
                    {cd.organizational_context && Object.keys(cd.organizational_context).length > 0 && (
                      <div>
                        <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Org Context</p>
                        <div className="bg-[#F9F9F9] rounded-lg p-3 space-y-1">
                          {Object.entries(cd.organizational_context).map(([key, val]) => (
                            <div key={key} className="text-[12px]">
                              <span className="text-[#999999]">{key.replace(/_/g, ' ')}:</span>{' '}
                              <span className="text-[#333333]">{typeof val === 'string' ? val : JSON.stringify(val)}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <FieldRow label="Digital Readiness" value={cd.digital_readiness} />
                    <FieldRow label="Tech Maturity" value={cd.technology_maturity} />
                    {cd.role_gaps && (cd.role_gaps as Record<string, unknown>[]).length > 0 && (
                      <div>
                        <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Role Gaps</p>
                        <div className="space-y-1">
                          {(cd.role_gaps as Record<string, unknown>[]).map((gap, i) => (
                            <div key={i} className="text-[12px] text-[#666666] bg-[#F9F9F9] rounded-lg px-3 py-2">
                              {typeof gap === 'string' ? gap : (gap.title || gap.role || JSON.stringify(gap)) as string}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    {cd.tech_stack && (
                      <div>
                        <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Tech Stack</p>
                        <TagList items={cd.tech_stack} emptyText="No tech stack data" />
                      </div>
                    )}
                    {!cd.company_summary && !cd.organizational_context && (
                      <p className="text-[12px] text-[#999999] italic">
                        Run the Client Intelligence Agent to populate this section.
                      </p>
                    )}
                  </div>
                </AccordionSection>
              )}

              {/* Strategic Position */}
              <AccordionSection
                title="Strategic Position"
                icon={Target}
                badge={
                  sc.confirmation_status ? (
                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                      sc.confirmation_status === 'confirmed_consultant' || sc.confirmation_status === 'confirmed_client'
                        ? 'bg-[#E8F5E9] text-[#25785A]'
                        : 'bg-[#F0F0F0] text-[#999999]'
                    }`}>
                      {sc.confirmation_status === 'confirmed_consultant' ? 'Confirmed' : sc.confirmation_status?.replace(/_/g, ' ')}
                    </span>
                  ) : undefined
                }
              >
                <div className="space-y-3">
                  {sc.executive_summary && (
                    <div>
                      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Executive Summary</p>
                      <p className="text-[13px] text-[#666666] leading-relaxed">{sc.executive_summary}</p>
                    </div>
                  )}
                  {sc.opportunity && (
                    <div>
                      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Opportunity</p>
                      <div className="bg-[#F9F9F9] rounded-lg p-3 space-y-1 text-[12px]">
                        {Object.entries(sc.opportunity).map(([key, val]) => (
                          val ? (
                            <div key={key}>
                              <span className="text-[#999999]">{key.replace(/_/g, ' ')}:</span>{' '}
                              <span className="text-[#333333]">{typeof val === 'string' ? val : JSON.stringify(val)}</span>
                            </div>
                          ) : null
                        ))}
                      </div>
                    </div>
                  )}
                  {cd.market_position && (
                    <div>
                      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Market Position</p>
                      <p className="text-[13px] text-[#666666]">{cd.market_position}</p>
                    </div>
                  )}
                  {cd.vision_synthesis && (
                    <div>
                      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Vision Synthesis</p>
                      <p className="text-[13px] text-[#666666]">{cd.vision_synthesis}</p>
                    </div>
                  )}
                  {cd.growth_signals && (cd.growth_signals as string[]).length > 0 && (
                    <div>
                      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Growth Signals</p>
                      <TagList items={cd.growth_signals} />
                    </div>
                  )}
                  {cd.competitors && (cd.competitors as string[]).length > 0 && (
                    <div>
                      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Competitors</p>
                      <TagList items={cd.competitors} />
                    </div>
                  )}
                  {sc.risks && (sc.risks as Record<string, unknown>[]).length > 0 && (
                    <div>
                      <p className="text-[11px] font-medium text-[#999999] uppercase tracking-wide mb-1">Risks</p>
                      <div className="space-y-1.5">
                        {(sc.risks as Record<string, unknown>[]).slice(0, 5).map((risk, i) => (
                          <div key={i} className="flex items-start gap-2 text-[12px] bg-[#F9F9F9] rounded-lg px-3 py-2">
                            <Shield className="w-3 h-3 text-[#999999] mt-0.5 flex-shrink-0" />
                            <div>
                              <span className="text-[#333333]">
                                {typeof risk === 'string' ? risk : (risk.description || JSON.stringify(risk)) as string}
                              </span>
                              {typeof risk.severity === 'string' && (
                                <span className="ml-1.5 text-[10px] text-[#999999]">({risk.severity})</span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {!sc.executive_summary && !sc.opportunity && !cd.market_position && (
                    <p className="text-[12px] text-[#999999] italic">
                      No strategic context available yet. Process more signals to build this section.
                    </p>
                  )}
                </div>
              </AccordionSection>

              {/* Open Questions */}
              <AccordionSection
                title="Open Questions"
                icon={HelpCircle}
                badge={
                  oq.length > 0 ? (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                      {oq.length}
                    </span>
                  ) : undefined
                }
              >
                {oq.length === 0 ? (
                  <p className="text-[12px] text-[#999999] italic">
                    No open questions recorded. Questions surface as the Discovery Agent interacts with signals.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {oq.map((q, i) => {
                      const question = typeof q === 'string' ? q : (q.question || q.text || JSON.stringify(q)) as string
                      const answered = typeof q === 'object' && q !== null ? (q as Record<string, unknown>).answered : false
                      return (
                        <div
                          key={i}
                          className={`flex items-start gap-2 text-[13px] rounded-lg px-3 py-2 ${
                            answered ? 'bg-[#E8F5E9]/50 text-[#25785A]' : 'bg-[#F9F9F9] text-[#666666]'
                          }`}
                        >
                          <HelpCircle className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
                          <span>{question}</span>
                        </div>
                      )
                    })}
                  </div>
                )}
              </AccordionSection>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
