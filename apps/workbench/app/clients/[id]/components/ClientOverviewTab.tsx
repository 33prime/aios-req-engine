'use client'

import { useState } from 'react'
import {
  Globe,
  MapPin,
  Calendar,
  Users,
  DollarSign,
  Sparkles,
  AlertTriangle,
  BookOpen,
  Plus,
  X,
  Check,
} from 'lucide-react'
import type { ClientDetail, ClientKnowledgeBase, KnowledgeItem } from '@/types/workspace'
import type { ClientIntelligenceProfile } from '@/lib/api'
import { addKnowledgeItem, updateKnowledgeItem, deleteKnowledgeItem } from '@/lib/api'

interface ClientOverviewTabProps {
  client: ClientDetail
  intelligence: ClientIntelligenceProfile | null
  knowledgeBase?: ClientKnowledgeBase | null
  onKnowledgeBaseChange?: () => void
}

function MaturityBadge({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-[12px] text-[#666]">{label}</span>
      <span className="px-2 py-0.5 text-[11px] font-medium text-[#25785A] bg-[#E8F5E9] rounded-md capitalize">
        {value.replace('_', ' ')}
      </span>
    </div>
  )
}

const SECTION_LABELS: Record<string, { label: string; max: number }> = {
  firmographics: { label: 'Firmographics', max: 15 },
  stakeholder_map: { label: 'Stakeholders', max: 20 },
  organizational_context: { label: 'Org Context', max: 15 },
  constraints: { label: 'Constraints', max: 15 },
  vision_strategy: { label: 'Vision', max: 10 },
  competitive_context: { label: 'Competitors', max: 10 },
  data_landscape: { label: 'Data', max: 10 },
  portfolio_health: { label: 'Portfolio', max: 5 },
}

function SectionBars({ intelligence }: { intelligence: ClientIntelligenceProfile }) {
  // Derive section scores from intelligence sections
  const sections: Record<string, number> = {}

  // Firmographics
  let firm = 0
  const f = intelligence.sections?.firmographics
  if (f?.company_summary) firm += 5
  if (f?.market_position) firm += 5
  const fFields = [f?.employee_count, f?.revenue_range, f?.headquarters]
  firm += Math.min(5, fFields.filter(Boolean).length * 2)
  sections.firmographics = Math.min(15, firm)

  // Others — derive from presence of data
  const constraints = intelligence.sections?.constraints
  sections.constraints = Array.isArray(constraints)
    ? Math.min(15, constraints.length * 2 + new Set(constraints.map((c: { category?: string }) => c.category)).size * 2)
    : 0
  sections.vision_strategy = intelligence.sections?.vision ? 10 : 0
  const org = intelligence.sections?.organizational_context as Record<string, unknown> | undefined
  const assessment = (org?.assessment ?? org) as Record<string, unknown> | undefined
  sections.organizational_context =
    assessment?.decision_making_style && assessment.decision_making_style !== 'unknown' ? 15 : 0
  const competitors = intelligence.sections?.competitors
  sections.competitive_context = Array.isArray(competitors) ? Math.min(10, competitors.length * 5) : 0
  sections.stakeholder_map = intelligence.profile_completeness > 30 ? 10 : 0
  sections.data_landscape = 0
  sections.portfolio_health = 5

  return (
    <div className="space-y-2">
      {Object.entries(SECTION_LABELS).map(([key, { label, max }]) => {
        const score = sections[key] ?? 0
        const pct = max > 0 ? Math.min(100, (score / max) * 100) : 0
        return (
          <div key={key} className="flex items-center gap-3">
            <span className="text-[11px] text-[#666] w-24 flex-shrink-0">{label}</span>
            <div className="flex-1 h-1.5 bg-[#F0F0F0] rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-primary rounded-full transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-[10px] text-[#999] w-8 text-right">
              {score}/{max}
            </span>
          </div>
        )
      })}
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
  onAdded,
}: {
  title: string
  items: KnowledgeItem[]
  category: 'business_processes' | 'sops' | 'tribal_knowledge'
  clientId: string
  onAdded?: () => void
}) {
  const [adding, setAdding] = useState(false)
  const [newText, setNewText] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')

  const handleAdd = async () => {
    if (!newText.trim()) return
    try {
      await addKnowledgeItem(clientId, category, {
        text: newText.trim(),
        source: 'manual',
        confidence: 'medium',
      })
      setNewText('')
      setAdding(false)
      onAdded?.()
    } catch (err) {
      console.error('Failed to add knowledge item:', err)
    }
  }

  const handleUpdate = async (itemId: string) => {
    if (!editText.trim()) return
    try {
      await updateKnowledgeItem(clientId, category, itemId, { text: editText.trim() })
      setEditingId(null)
      onAdded?.()
    } catch (err) {
      console.error('Failed to update knowledge item:', err)
    }
  }

  const handleDelete = async (itemId: string) => {
    try {
      await deleteKnowledgeItem(clientId, category, itemId)
      onAdded?.()
    } catch (err) {
      console.error('Failed to delete knowledge item:', err)
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
            <div key={item.id} className="group relative bg-[#F4F4F4] rounded-lg px-3 py-2">
              {editingId === item.id ? (
                <div className="flex items-center gap-1.5">
                  <input
                    type="text"
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                    className="flex-1 px-2 py-1 text-[12px] border border-border rounded-lg focus:outline-none focus:border-brand-primary bg-white"
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleUpdate(item.id)
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    autoFocus
                  />
                  <button
                    onClick={() => handleUpdate(item.id)}
                    className="p-1 text-brand-primary hover:text-[#25785A] transition-colors"
                    title="Save"
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="p-1 text-[#999] hover:text-[#666] transition-colors"
                    title="Cancel"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              ) : (
                <>
                  <button
                    onClick={() => {
                      setEditingId(item.id)
                      setEditText(item.text)
                    }}
                    className="text-left w-full"
                  >
                    <p className="text-[12px] text-[#333] line-clamp-2">{item.text}</p>
                  </button>
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="absolute top-1.5 right-1.5 p-0.5 opacity-0 group-hover:opacity-100 text-[#CCC] hover:text-red-500 transition-all"
                    title="Delete item"
                  >
                    <X className="w-3 h-3" />
                  </button>
                  <div className="flex items-center gap-1.5 mt-1">
                    <span className="px-1.5 py-0.5 text-[9px] font-medium text-[#666] bg-border rounded">
                      {SOURCE_LABELS[item.source] || item.source}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 text-[9px] font-medium rounded ${
                        CONFIDENCE_STYLES[item.confidence] || CONFIDENCE_STYLES.medium
                      }`}
                    >
                      {item.confidence}
                    </span>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function ClientOverviewTab({
  client,
  intelligence,
  knowledgeBase,
  onKnowledgeBaseChange,
}: ClientOverviewTabProps) {
  const hasEnrichment = client.enrichment_status === 'completed'
  const constraints = intelligence?.sections?.constraints ?? []
  const vision = intelligence?.sections?.vision

  const kb = knowledgeBase || { business_processes: [], sops: [], tribal_knowledge: [] }
  const [kbExpanded, setKbExpanded] = useState(false)
  const kbCount = kb.business_processes.length + kb.sops.length + kb.tribal_knowledge.length

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6">
      {/* Left: AI Intelligence (primary) */}
      <div className="space-y-6">
        <div className="bg-white rounded-2xl border border-border shadow-md p-6">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-4 h-4 text-brand-primary" />
            <h3 className="text-[14px] font-semibold text-[#333]">AI Intelligence</h3>
          </div>

          {!hasEnrichment ? (
            <div className="text-center py-8">
              <Sparkles className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
              <p className="text-[13px] text-[#666] mb-1">No enrichment data yet</p>
              <p className="text-[12px] text-[#999]">
                Click Analyze to build the client profile
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {client.company_summary && (
                <div>
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">
                    Summary
                  </p>
                  <p className="text-[13px] text-[#333] leading-relaxed">
                    {client.company_summary}
                  </p>
                </div>
              )}
              {client.market_position && (
                <div className="pt-2">
                  <p className="text-[11px] text-[#999] font-medium uppercase tracking-wide mb-1">
                    Market Position
                  </p>
                  <p className="text-[13px] text-[#666] leading-relaxed">
                    {client.market_position}
                  </p>
                </div>
              )}
              <div className="pt-2 border-t border-border">
                <MaturityBadge label="Technology Maturity" value={client.technology_maturity} />
                <MaturityBadge label="Digital Readiness" value={client.digital_readiness} />
              </div>
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

        {/* Top Constraints */}
        {Array.isArray(constraints) && constraints.length > 0 && (
          <div className="bg-white rounded-2xl border border-border shadow-md p-6">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-[#666]" />
              <h3 className="text-[14px] font-semibold text-[#333]">
                Top Constraints
              </h3>
            </div>
            <div className="space-y-2">
              {constraints.slice(0, 3).map((c: { title?: string; severity?: string; description?: string }, i: number) => (
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
          </div>
        )}

        {/* Section Completeness Bars */}
        {intelligence && intelligence.profile_completeness > 0 && (
          <div className="bg-white rounded-2xl border border-border shadow-md p-6">
            <h3 className="text-[14px] font-semibold text-[#333] mb-3">Profile Gaps</h3>
            <p className="text-[12px] text-[#999] mb-3">
              Click Analyze to fill the weakest section automatically.
            </p>
            <SectionBars intelligence={intelligence} />
          </div>
        )}
      </div>

      {/* Right: Company Details + Knowledge Base (secondary) */}
      <div className="space-y-6">
        {/* Company Details — compact */}
        <div className="bg-white rounded-xl border border-border shadow-sm p-4">
          <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-3">Company Details</h3>
          <div className="flex flex-wrap gap-x-6 gap-y-2">
            {client.website && (
              <div className="flex items-center gap-1.5">
                <Globe className="w-3 h-3 text-[#999]" />
                <a href={client.website} target="_blank" rel="noopener noreferrer" className="text-[12px] text-brand-primary hover:underline truncate max-w-[200px]">{client.website}</a>
              </div>
            )}
            {client.founding_year && (
              <div className="flex items-center gap-1.5">
                <Calendar className="w-3 h-3 text-[#999]" />
                <span className="text-[12px] text-[#333]">Founded {client.founding_year}</span>
              </div>
            )}
            {client.employee_count && (
              <div className="flex items-center gap-1.5">
                <Users className="w-3 h-3 text-[#999]" />
                <span className="text-[12px] text-[#333]">{client.employee_count.toLocaleString()} employees</span>
              </div>
            )}
            {client.headquarters && (
              <div className="flex items-center gap-1.5">
                <MapPin className="w-3 h-3 text-[#999]" />
                <span className="text-[12px] text-[#333]">{client.headquarters}</span>
              </div>
            )}
            {client.revenue_range && (
              <div className="flex items-center gap-1.5">
                <DollarSign className="w-3 h-3 text-[#999]" />
                <span className="text-[12px] text-[#333]">{client.revenue_range}</span>
              </div>
            )}
          </div>
          {client.description && (
            <p className="text-[12px] text-[#666] mt-3 leading-relaxed line-clamp-2">{client.description}</p>
          )}
        </div>

        {/* Knowledge Base — collapsible */}
        <div className="bg-white rounded-xl border border-border shadow-sm p-4">
          <button
            onClick={() => setKbExpanded(!kbExpanded)}
            className="flex items-center justify-between w-full"
          >
            <div className="flex items-center gap-2">
              <BookOpen className="w-3.5 h-3.5 text-[#666]" />
              <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em]">Knowledge Base</h3>
              {kbCount > 0 && (
                <span className="text-[11px] text-[#999]">{kbCount} items</span>
              )}
            </div>
            <span className="text-[10px] text-[#999]">{kbExpanded ? '\u25BC' : '\u25B6'}</span>
          </button>
          {kbExpanded && (
            <div className="space-y-4 mt-4">
              <KnowledgeSection title="Business Processes" items={kb.business_processes} category="business_processes" clientId={client.id} onAdded={onKnowledgeBaseChange} />
              <KnowledgeSection title="SOPs & Standards" items={kb.sops} category="sops" clientId={client.id} onAdded={onKnowledgeBaseChange} />
              <KnowledgeSection title="Tribal Knowledge" items={kb.tribal_knowledge} category="tribal_knowledge" clientId={client.id} onAdded={onKnowledgeBaseChange} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
