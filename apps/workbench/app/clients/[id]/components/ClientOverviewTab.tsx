'use client'

import { useState } from 'react'
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
  AlertTriangle,
  BookOpen,
  Plus,
} from 'lucide-react'
import type { ClientDetail, ClientKnowledgeBase, KnowledgeItem } from '@/types/workspace'
import type { ClientIntelligenceProfile } from '@/lib/api'
import { addKnowledgeItem, deleteKnowledgeItem } from '@/lib/api'
import { CompletenessRing } from '@/components/workspace/brd/components/CompletenessRing'
import { OrgContextDisplay } from './OrgContextDisplay'
import { KnowledgeItemDetailDrawer } from './KnowledgeItemDetailDrawer'

interface ClientOverviewTabProps {
  client: ClientDetail
  intelligence: ClientIntelligenceProfile | null
  knowledgeBase?: ClientKnowledgeBase | null
  onKnowledgeBaseChange?: () => void
  onProcessDocGenerated?: () => void
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

const SOURCE_LABELS: Record<string, string> = {
  signal: 'Signal',
  stakeholder: 'Stakeholder',
  ai_inferred: 'AI Inferred',
  manual: 'Manual',
}

const CONFIDENCE_STYLES: Record<string, string> = {
  high: 'bg-[#E8F5E9] text-[#25785A]',
  medium: 'bg-[#F0F0F0] text-[#666]',
  low: 'bg-[#F0F0F0] text-[#999]',
}

function KnowledgeSection({
  title,
  items,
  category,
  clientId,
  onItemClick,
  onAdded,
}: {
  title: string
  items: KnowledgeItem[]
  category: 'business_processes' | 'sops' | 'tribal_knowledge'
  clientId: string
  onItemClick: (item: KnowledgeItem) => void
  onAdded?: () => void
}) {
  const [adding, setAdding] = useState(false)
  const [newText, setNewText] = useState('')

  const handleAdd = async () => {
    if (!newText.trim()) return
    try {
      await addKnowledgeItem(clientId, category, { text: newText.trim(), source: 'manual', confidence: 'medium' })
      setNewText('')
      setAdding(false)
      onAdded?.()
    } catch (err) {
      console.error('Failed to add knowledge item:', err)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-[12px] font-semibold text-[#999] uppercase tracking-wide">{title}</p>
        <button
          onClick={() => setAdding(!adding)}
          className="p-0.5 text-[#999] hover:text-brand-primary transition-colors"
          title={`Add ${title.toLowerCase()}`}
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>
      {adding && (
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={newText}
            onChange={(e) => setNewText(e.target.value)}
            placeholder={`Add ${title.toLowerCase()} item...`}
            className="flex-1 px-2 py-1.5 text-[12px] border border-border rounded-lg focus:outline-none focus:border-brand-primary"
            onKeyDown={(e) => e.key === 'Enter' && handleAdd()}
            autoFocus
          />
          <button
            onClick={handleAdd}
            className="px-3 py-1.5 text-[11px] font-medium text-white bg-brand-primary rounded-lg hover:bg-[#25785A] transition-colors"
          >
            Add
          </button>
        </div>
      )}
      {items.length === 0 ? (
        <div className="bg-[#F4F4F4] rounded-lg px-3 py-2">
          <p className="text-[12px] text-[#999] italic">No items yet</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-[#F4F4F4] rounded-lg px-3 py-2 cursor-pointer hover:bg-[#ECECEC] transition-colors"
              onClick={() => onItemClick(item)}
            >
              <p className="text-[12px] text-[#333] line-clamp-2">{item.text}</p>
              <div className="flex items-center gap-1.5 mt-1">
                <span className="px-1.5 py-0.5 text-[9px] font-medium text-[#666] bg-border rounded">
                  {SOURCE_LABELS[item.source] || item.source}
                </span>
                <span className={`px-1.5 py-0.5 text-[9px] font-medium rounded ${CONFIDENCE_STYLES[item.confidence] || CONFIDENCE_STYLES.medium}`}>
                  {item.confidence}
                </span>
                {item.stakeholder_name && (
                  <span className="text-[10px] text-[#999]">via {item.stakeholder_name}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function ClientOverviewTab({ client, intelligence, knowledgeBase, onKnowledgeBaseChange, onProcessDocGenerated }: ClientOverviewTabProps) {
  const [selectedKBItem, setSelectedKBItem] = useState<KnowledgeItem | null>(null)
  const [selectedKBCategory, setSelectedKBCategory] = useState<'business_processes' | 'sops' | 'tribal_knowledge'>('business_processes')

  const hasEnrichment = client.enrichment_status === 'completed'
  const completeness = intelligence?.profile_completeness ?? 0
  const constraints = intelligence?.sections?.constraints ?? []
  const vision = intelligence?.sections?.vision
  const orgContext = intelligence?.sections?.organizational_context as Record<string, unknown> | undefined

  const kb = knowledgeBase || { business_processes: [], sops: [], tribal_knowledge: [] }

  const handleKBItemClick = (item: KnowledgeItem, category: 'business_processes' | 'sops' | 'tribal_knowledge') => {
    setSelectedKBItem(item)
    setSelectedKBCategory(category)
  }

  const handleDeleteKBItem = async (itemId: string) => {
    try {
      await deleteKnowledgeItem(client.id, selectedKBCategory, itemId)
      setSelectedKBItem(null)
      onKnowledgeBaseChange?.()
    } catch (err) {
      console.error('Failed to delete knowledge item:', err)
    }
  }

  return (
    <div className="space-y-6">
      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Company Details */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-border shadow-md p-6">
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
                <div className="pt-3 mt-2 border-t border-border">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Description</p>
                  <p className="text-[13px] text-[#666] leading-relaxed">{client.description}</p>
                </div>
              )}
            </div>
          </div>

          {/* Knowledge Base */}
          <div className="bg-white rounded-2xl border border-border shadow-md p-6">
            <div className="flex items-center gap-2 mb-4">
              <BookOpen className="w-4 h-4 text-[#666]" />
              <h3 className="text-[14px] font-semibold text-[#333]">Knowledge Base</h3>
              {(kb.business_processes.length + kb.sops.length + kb.tribal_knowledge.length) > 0 && (
                <span className="text-[11px] text-[#999]">
                  {kb.business_processes.length + kb.sops.length + kb.tribal_knowledge.length} items
                </span>
              )}
            </div>
            <div className="space-y-4">
              <KnowledgeSection
                title="Business Processes"
                items={kb.business_processes}
                category="business_processes"
                clientId={client.id}
                onItemClick={(item) => handleKBItemClick(item, 'business_processes')}
                onAdded={onKnowledgeBaseChange}
              />
              <KnowledgeSection
                title="SOPs & Standards"
                items={kb.sops}
                category="sops"
                clientId={client.id}
                onItemClick={(item) => handleKBItemClick(item, 'sops')}
                onAdded={onKnowledgeBaseChange}
              />
              <KnowledgeSection
                title="Tribal Knowledge"
                items={kb.tribal_knowledge}
                category="tribal_knowledge"
                clientId={client.id}
                onItemClick={(item) => handleKBItemClick(item, 'tribal_knowledge')}
                onAdded={onKnowledgeBaseChange}
              />
            </div>
          </div>

          {/* Knowledge Item Detail Drawer */}
          {selectedKBItem && (
            <KnowledgeItemDetailDrawer
              item={selectedKBItem}
              category={selectedKBCategory}
              onClose={() => setSelectedKBItem(null)}
              onDelete={handleDeleteKBItem}
              clientId={client.id}
              clientProjects={client.projects}
              onProcessDocGenerated={() => {
                setSelectedKBItem(null)
                onProcessDocGenerated?.()
              }}
            />
          )}
        </div>

        {/* Right: AI Intelligence + CI Data */}
        <div className="space-y-6">
          <div className="bg-white rounded-2xl border border-border shadow-md p-6">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-4 h-4 text-brand-primary" />
              <h3 className="text-[14px] font-semibold text-[#333]">AI Intelligence</h3>
              {completeness > 0 && (
                <div className="ml-auto">
                  <CompletenessRing score={completeness} size="lg" />
                </div>
              )}
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
                {client.company_summary && (
                  <div>
                    <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Summary</p>
                    <p className="text-[13px] text-[#333] leading-relaxed">{client.company_summary}</p>
                  </div>
                )}
                {client.market_position && (
                  <div className="pt-2">
                    <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">Market Position</p>
                    <p className="text-[13px] text-[#666] leading-relaxed">{client.market_position}</p>
                  </div>
                )}
                <div className="pt-2 border-t border-border">
                  <MaturityBadge label="Technology Maturity" value={client.technology_maturity} />
                  <MaturityBadge label="Digital Readiness" value={client.digital_readiness} />
                </div>
                {client.innovation_score != null && (
                  <div className="pt-2 border-t border-border">
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] text-[#666]">Innovation Score</span>
                      <span className="text-[13px] font-semibold text-brand-primary">
                        {Math.round(client.innovation_score * 100)}%
                      </span>
                    </div>
                    <div className="mt-1 h-2 bg-[#F0F0F0] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-brand-primary rounded-full transition-all"
                        style={{ width: `${client.innovation_score * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Vision Synthesis */}
          {vision && (
            <div className="bg-white rounded-2xl border border-border shadow-md p-6">
              <div className="flex items-center gap-2 mb-3">
                <Sparkles className="w-4 h-4 text-brand-primary" />
                <h3 className="text-[14px] font-semibold text-[#333]">Vision Synthesis</h3>
              </div>
              <p className="text-[13px] text-[#666] leading-relaxed">{vision}</p>
            </div>
          )}

          {/* Top Constraints preview */}
          {constraints.length > 0 && (
            <div className="bg-white rounded-2xl border border-border shadow-md p-6">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-[#666]" />
                <h3 className="text-[14px] font-semibold text-[#333]">Top Constraints</h3>
              </div>
              <div className="space-y-2">
                {constraints.slice(0, 3).map((c, i) => (
                  <div key={i} className="bg-[#F4F4F4] rounded-lg px-3 py-2">
                    <div className="flex items-center gap-2">
                      <span className="text-[13px] font-medium text-[#333]">{c.title}</span>
                      <span className="px-1.5 py-0.5 text-[10px] font-medium text-[#666] bg-border rounded">
                        {c.severity}
                      </span>
                    </div>
                    <p className="text-[12px] text-[#666] mt-0.5 line-clamp-1">{c.description}</p>
                  </div>
                ))}
              </div>
              {constraints.length > 3 && (
                <p className="text-[12px] text-brand-primary mt-2 font-medium">
                  View all {constraints.length} in Intelligence tab
                </p>
              )}
            </div>
          )}

          {/* Org Context */}
          {orgContext && Object.keys(orgContext).length > 0 && (
            <div className="bg-white rounded-2xl border border-border shadow-md p-6">
              <h3 className="text-[14px] font-semibold text-[#333] mb-3">Organizational Context</h3>
              <OrgContextDisplay orgContext={orgContext} variant="compact" />
            </div>
          )}
        </div>
      </div>

      {/* Tech Stack */}
      {client.tech_stack && client.tech_stack.length > 0 && (
        <div className="bg-white rounded-2xl border border-border shadow-md p-6">
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
        <div className="bg-white rounded-2xl border border-border shadow-md p-6">
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
        <div className="bg-white rounded-2xl border border-border shadow-md p-6">
          <div className="flex items-center gap-2 mb-3">
            <Swords className="w-4 h-4 text-[#666]" />
            <h3 className="text-[14px] font-semibold text-[#333]">Competitors</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {client.competitors.map((comp, i) => (
              <div
                key={i}
                className="p-3 bg-surface-page rounded-xl border border-border"
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
