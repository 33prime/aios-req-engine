/**
 * EvidencePanel - Sources and evidence quality view
 *
 * Layout:
 * 1. Source Usage (4 highlight cards)
 * 2. Evidence Quality (green palette bars)
 * 3. Chronological Timeline (newest first, expandable cards)
 *    - Notes: expand to show full text with highlights
 *    - Documents: expand to show analysis, scores, topics, keywords
 *    - Research: expand to show full markdown content
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  FileText,
  CheckCircle,
  AlertCircle,
  Clock,
  BarChart3,
  ChevronDown,
  ChevronUp,
  Mail,
  Mic,
  MessageSquare,
  PenSquare,
  Globe,
  Upload,
  Sparkles,
  Info,
  Download,
  Trash2,
  Copy,
  Check,
  Database,
  Lightbulb,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import {
  getEvidenceQuality,
  getDocumentsSummary,
  getSourceUsage,
  getSignal,
  getDocumentDownloadUrl,
  withdrawDocument,
  getRequirementsIntelligence,
} from '@/lib/api'
import type {
  EvidenceQualityResponse,
  DocumentSummaryResponse,
  SourceUsageResponse,
  SourceUsageItem,
  DocumentSummaryItem,
  RequirementsIntelligenceResponse,
} from '@/lib/api'
import { Markdown } from '@/components/ui/Markdown'
import { RequirementsIntelligenceTab } from './RequirementsIntelligenceTab'

interface EvidencePanelProps {
  projectId: string
}

type EvidenceTab = 'evidence' | 'intelligence'

const EVIDENCE_TABS: { id: EvidenceTab; label: string; Icon: typeof Database }[] = [
  { id: 'evidence', label: 'Evidence', Icon: Database },
  { id: 'intelligence', label: 'Intelligence', Icon: Lightbulb },
]

export function EvidencePanel({ projectId }: EvidencePanelProps) {
  const [evidence, setEvidence] = useState<EvidenceQualityResponse | null>(null)
  const [documents, setDocuments] = useState<DocumentSummaryResponse | null>(null)
  const [sourceUsage, setSourceUsage] = useState<SourceUsageResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Tab state
  const [activeTab, setActiveTab] = useState<EvidenceTab>('evidence')

  // Intelligence data (lazy-loaded)
  const [intelligence, setIntelligence] = useState<RequirementsIntelligenceResponse | null>(null)
  const [intelligenceLoading, setIntelligenceLoading] = useState(false)
  const [intelligenceLoaded, setIntelligenceLoaded] = useState(false)

  useEffect(() => {
    setIsLoading(true)
    Promise.all([
      getEvidenceQuality(projectId).catch(() => null),
      getDocumentsSummary(projectId).catch(() => null),
      getSourceUsage(projectId).catch(() => null),
    ])
      .then(([ev, docs, usage]) => {
        setEvidence(ev)
        setDocuments(docs)
        setSourceUsage(usage)
      })
      .finally(() => setIsLoading(false))
  }, [projectId])

  // Lazy-load intelligence on first tab activation
  useEffect(() => {
    if (activeTab === 'intelligence' && !intelligenceLoaded) {
      setIntelligenceLoading(true)
      getRequirementsIntelligence(projectId)
        .then(setIntelligence)
        .catch(() => setIntelligence(null))
        .finally(() => {
          setIntelligenceLoading(false)
          setIntelligenceLoaded(true)
        })
    }
  }, [activeTab, intelligenceLoaded, projectId])

  return (
    <div className="space-y-4">
      {/* Tab bar */}
      <div className="flex items-center gap-1">
        {EVIDENCE_TABS.map((tab) => {
          const Icon = tab.Icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-brand-teal/10 text-brand-teal'
                  : 'text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Evidence tab */}
      {activeTab === 'evidence' && (
        <>
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-teal" />
            </div>
          ) : !evidence && !documents && !sourceUsage ? (
            <p className="text-sm text-ui-supportText text-center py-8">
              No evidence data available yet.
            </p>
          ) : (
            <div className="space-y-6">
              {sourceUsage && sourceUsage.sources.length > 0 && (
                <SourceUsageCards sourceUsage={sourceUsage} />
              )}
              {evidence && <EvidenceQuality evidence={evidence} />}
              <SourceTimeline
                sources={sourceUsage?.sources || []}
                documents={documents?.documents || []}
                onDocumentRemoved={() => {
                  getDocumentsSummary(projectId).then(setDocuments).catch(() => {})
                }}
              />
            </div>
          )}
        </>
      )}

      {/* Intelligence tab */}
      {activeTab === 'intelligence' && (
        <RequirementsIntelligenceTab data={intelligence} isLoading={intelligenceLoading} />
      )}
    </div>
  )
}

// =============================================================================
// 1. Source Usage — 4 highlight cards
// =============================================================================

function SourceUsageCards({ sourceUsage }: { sourceUsage: SourceUsageResponse }) {
  const totals = useMemo(() => {
    const result = { feature: 0, persona: 0, vp_step: 0, business_driver: 0 }
    sourceUsage.sources.forEach((s) => {
      result.feature += s.uses_by_entity.feature || 0
      result.persona += s.uses_by_entity.persona || 0
      result.vp_step += s.uses_by_entity.vp_step || 0
      result.business_driver += s.uses_by_entity.business_driver || 0
    })
    return result
  }, [sourceUsage])

  const cards = [
    { label: 'Features', value: totals.feature, icon: Sparkles, accent: 'text-emerald-600 bg-emerald-50' },
    { label: 'Personas', value: totals.persona, icon: MessageSquare, accent: 'text-teal-600 bg-teal-50' },
    { label: 'VP Steps', value: totals.vp_step, icon: CheckCircle, accent: 'text-emerald-600 bg-emerald-50' },
    { label: 'Drivers', value: totals.business_driver, icon: BarChart3, accent: 'text-teal-600 bg-teal-50' },
  ]

  return (
    <div>
      <SectionHeader
        title="Source Usage"
        right={`${sourceUsage.sources.length} source${sourceUsage.sources.length !== 1 ? 's' : ''}`}
      />
      <div className="grid grid-cols-4 gap-3">
        {cards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.label} className="bg-ui-background rounded-lg px-3 py-2 flex items-center gap-2.5">
              <div className={`w-7 h-7 rounded-full ${card.accent} flex items-center justify-center flex-shrink-0`}>
                <Icon className="w-3.5 h-3.5" />
              </div>
              <div>
                <p className="text-base font-bold text-ui-headingDark leading-tight">{card.value}</p>
                <p className="text-[10px] text-ui-supportText leading-tight">{card.label}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// =============================================================================
// 2. Evidence Quality
// =============================================================================

const QUALITY_BARS: {
  key: keyof EvidenceQualityResponse['breakdown']
  label: string
  barColor: string
}[] = [
  { key: 'confirmed_client', label: 'Client Verified', barColor: 'bg-emerald-500' },
  { key: 'confirmed_consultant', label: 'Consultant Verified', barColor: 'bg-emerald-400' },
  { key: 'needs_client', label: 'Needs Review', barColor: 'bg-teal-400' },
  { key: 'ai_generated', label: 'AI Generated', barColor: 'bg-gray-300' },
]

function EvidenceQuality({ evidence }: { evidence: EvidenceQualityResponse }) {
  return (
    <div>
      <SectionHeader
        title="Evidence Quality"
        right={
          <span className="text-sm font-bold text-emerald-600">
            {Math.round(evidence.strong_evidence_percentage)}% strong
          </span>
        }
      />
      <div className="space-y-2">
        {QUALITY_BARS.map(({ key, label, barColor }) => {
          const data = evidence.breakdown[key]
          if (!data) return null
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="text-[11px] text-ui-supportText w-32 truncate">{label}</span>
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${barColor} rounded-full transition-all`}
                  style={{ width: `${data.percentage}%` }}
                />
              </div>
              <span className="text-[11px] text-ui-bodyText w-8 text-right">{data.count}</span>
            </div>
          )
        })}
      </div>
      {evidence.summary && (
        <p className="text-[11px] text-ui-supportText mt-2 italic">{evidence.summary}</p>
      )}
    </div>
  )
}

// =============================================================================
// 3. Chronological Timeline
// =============================================================================

interface TimelineItem {
  id: string
  type: 'signal' | 'research' | 'document'
  name: string
  signalType: string | null
  date: string | null
  sourceData: SourceUsageItem | null
  docData: DocumentSummaryItem | null
}

function SourceTimeline({
  sources,
  documents,
  onDocumentRemoved,
}: {
  sources: SourceUsageItem[]
  documents: DocumentSummaryItem[]
  onDocumentRemoved?: () => void
}) {
  const items = useMemo(() => {
    const list: TimelineItem[] = []

    sources.forEach((s) => {
      list.push({
        id: s.source_id,
        type: s.signal_type === 'research' ? 'research' : 'signal',
        name: s.source_name,
        signalType: s.signal_type,
        date: s.last_used,
        sourceData: s,
        docData: null,
      })
    })

    documents.forEach((d) => {
      list.push({
        id: d.id,
        type: 'document',
        name: d.original_filename,
        signalType: 'document',
        date: d.created_at || null,
        sourceData: null,
        docData: d,
      })
    })

    // Newest first
    list.sort((a, b) => {
      if (!a.date && !b.date) return 0
      if (!a.date) return 1
      if (!b.date) return -1
      return new Date(b.date).getTime() - new Date(a.date).getTime()
    })

    return list
  }, [sources, documents])

  if (items.length === 0) {
    return (
      <p className="text-sm text-ui-supportText text-center py-4">
        No sources available yet.
      </p>
    )
  }

  return (
    <div>
      <SectionHeader title="Sources" right={`${items.length} total`} />
      <div className="relative">
        {/* Vertical timeline line */}
        <div className="absolute left-[15px] top-4 bottom-4 w-px bg-gray-200" />

        <div className="space-y-2.5">
          {items.map((item) => (
            <TimelineCard key={`${item.type}-${item.id}`} item={item} onDocumentRemoved={onDocumentRemoved} />
          ))}
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Timeline Card — expandable, type-specific content
// =============================================================================

function TimelineCard({ item, onDocumentRemoved }: { item: TimelineItem; onDocumentRemoved?: () => void }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [content, setContent] = useState<string | null>(null)
  const [quality, setQuality] = useState<{
    score: 'excellent' | 'good' | 'basic' | 'sparse'
    message: string
    details: string[]
  } | null>(null)
  const [loadingContent, setLoadingContent] = useState(false)
  const [copied, setCopied] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [isWithdrawing, setIsWithdrawing] = useState(false)

  const handleToggle = async () => {
    if (!isExpanded) {
      // Load content on first expand
      if (content === null) {
        if (item.type === 'research' && item.sourceData?.content) {
          setContent(item.sourceData.content)
        } else if (item.type === 'document' && item.docData) {
          setContent(item.docData.content_summary || 'No summary available.')
        } else if (item.type === 'signal' && item.sourceData) {
          setLoadingContent(true)
          try {
            const response = await getSignal(item.sourceData.source_id)
            setContent(response.raw_text || 'No content available')
            const metadata = response.metadata || {}
            if (metadata.quality_score) {
              setQuality({
                score: metadata.quality_score,
                message: metadata.quality_message || '',
                details: metadata.quality_details || [],
              })
            }
          } catch {
            setContent('Failed to load content')
          }
          setLoadingContent(false)
        }
      }
    }
    setIsExpanded(!isExpanded)
  }

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!content) return
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      console.error('Failed to copy')
    }
  }

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!item.docData) return
    setIsDownloading(true)
    try {
      const result = await getDocumentDownloadUrl(item.docData.id)
      window.open(result.download_url, '_blank')
    } catch {
      console.error('Failed to download document')
    } finally {
      setIsDownloading(false)
    }
  }

  const handleWithdraw = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!item.docData) return
    setIsWithdrawing(true)
    try {
      await withdrawDocument(item.docData.id)
      onDocumentRemoved?.()
    } catch {
      console.error('Failed to withdraw document')
    } finally {
      setIsWithdrawing(false)
    }
  }

  const Chevron = isExpanded ? ChevronUp : ChevronDown

  return (
    <div className="flex gap-3 relative">
      {/* Timeline dot */}
      <div className={`w-[30px] h-[30px] rounded-full border flex items-center justify-center z-10 flex-shrink-0 ${getTimelineDotStyle(item)}`}>
        <TimelineIcon item={item} />
      </div>

      {/* Card */}
      <div className="flex-1 bg-gray-50 border border-gray-100 rounded-lg overflow-hidden">
        {/* Collapsed header */}
        <button
          onClick={handleToggle}
          className="w-full flex items-center gap-2 px-3 py-2.5 text-left hover:bg-gray-100/50 transition-colors"
        >
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-ui-headingDark truncate">{item.name}</h4>
            <div className="flex items-center gap-2 mt-0.5">
              {item.date && (
                <span className="text-[10px] text-ui-supportText">
                  {formatDistanceToNow(new Date(item.date), { addSuffix: true })}
                </span>
              )}
              {/* Usage count */}
              {item.sourceData && item.sourceData.total_uses > 0 && (
                <span className="text-[10px] text-emerald-600 font-medium">
                  {item.sourceData.total_uses} uses
                </span>
              )}
              {item.docData && item.docData.usage_count > 0 && (
                <span className="text-[10px] text-emerald-600 font-medium">
                  {item.docData.usage_count} uses
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            {/* Action buttons — document: download + trash + quality dots */}
            {item.type === 'document' && item.docData && (
              <>
                <button
                  onClick={handleDownload}
                  disabled={isDownloading}
                  className="p-1.5 rounded-md text-gray-400 hover:text-ui-headingDark hover:bg-gray-200/50 transition-colors disabled:opacity-40"
                  title="Download"
                >
                  <Download className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={handleWithdraw}
                  disabled={isWithdrawing}
                  className="p-1.5 rounded-md text-gray-400 hover:text-red-500 hover:bg-red-50 transition-colors disabled:opacity-40"
                  title="Remove"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
                {item.docData.quality_score != null && (
                  <QualityDots score={item.docData.quality_score} />
                )}
              </>
            )}
            {/* Action button — research: copy */}
            {item.type === 'research' && content && (
              <button
                onClick={handleCopy}
                className="p-1.5 rounded-md text-gray-400 hover:text-ui-headingDark hover:bg-gray-200/50 transition-colors"
                title={copied ? 'Copied!' : 'Copy'}
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            )}
            <TypeBadge item={item} />
            <Chevron className="w-3.5 h-3.5 text-ui-supportText" />
          </div>
        </button>

        {/* Expanded content */}
        {isExpanded && (
          <div className="px-3 pb-3 pt-1 border-t border-gray-200">
            {loadingContent ? (
              <div className="flex items-center gap-2 py-3">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-brand-teal" />
                <span className="text-xs text-ui-supportText">Loading...</span>
              </div>
            ) : (
              <div className="space-y-3 mt-2">
                {/* Quality badge (for signals with quality metadata) */}
                {quality && <QualityBadge quality={quality} />}

                {/* Document expanded view */}
                {item.type === 'document' && item.docData && (
                  <DocumentExpanded doc={item.docData} />
                )}

                {/* Signal / Research content */}
                {item.type !== 'document' && content && (
                  <div className="bg-white rounded-lg border border-gray-100 p-3">
                    <Markdown
                      content={content}
                      className="text-sm text-ui-bodyText [&_h1]:text-sm [&_h2]:text-[13px] [&_h3]:text-[13px] [&_p]:text-sm [&_li]:text-sm"
                    />
                  </div>
                )}

                {/* Copy button for research — shown when expanded and content loaded */}
                {item.type === 'research' && content && (
                  <div className="flex justify-end">
                    <button
                      onClick={handleCopy}
                      className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-ui-supportText hover:text-ui-headingDark bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
                    >
                      {copied ? (
                        <>
                          <Check className="w-3 h-3 text-emerald-500" />
                          <span className="text-emerald-600">Copied</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3 h-3" />
                          <span>Copy content</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* Impact breakdown for signals */}
                {item.sourceData && <ImpactBar source={item.sourceData} />}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Document expanded view — analysis, scores, topics, keywords
// =============================================================================

function DocumentExpanded({ doc }: { doc: DocumentSummaryItem }) {
  const hasScores = doc.quality_score != null || doc.relevance_score != null || doc.information_density != null
  const hasTopics = doc.key_topics && doc.key_topics.length > 0
  const hasKeywords = doc.keyword_tags && doc.keyword_tags.length > 0

  return (
    <div className="space-y-3">
      {/* File metadata */}
      <div className="flex items-center gap-3 text-[11px] text-ui-supportText">
        <span>{formatFileSize(doc.file_size_bytes)}</span>
        {doc.page_count && (
          <>
            <span>·</span>
            <span>{doc.page_count} pages</span>
          </>
        )}
        <span>·</span>
        <span className="uppercase">{doc.file_type}</span>
        {doc.processing_status && (
          <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
            doc.processing_status === 'processed' ? 'bg-emerald-50 text-emerald-700' :
            doc.processing_status === 'processing' ? 'bg-teal-50 text-teal-600' :
            'bg-gray-100 text-gray-600'
          }`}>
            {doc.processing_status}
          </span>
        )}
      </div>

      {/* Summary */}
      {doc.content_summary && (
        <div className="bg-white rounded-lg border border-gray-100 p-3">
          <Markdown
            content={doc.content_summary}
            className="text-sm text-ui-bodyText [&_h1]:text-sm [&_h2]:text-[13px] [&_h3]:text-[13px] [&_p]:text-sm [&_li]:text-sm"
          />
        </div>
      )}

      {/* Analysis scores */}
      {hasScores && (
        <div className="flex items-center gap-4 text-xs">
          {doc.quality_score != null && (
            <span className="text-emerald-700 font-medium">
              Quality: {formatScore(doc.quality_score)}
            </span>
          )}
          {doc.relevance_score != null && (
            <span className="text-teal-700 font-medium">
              Relevance: {formatScore(doc.relevance_score)}
            </span>
          )}
          {doc.information_density != null && (
            <span className="text-emerald-600 font-medium">
              Density: {formatScore(doc.information_density)}
            </span>
          )}
        </div>
      )}

      {/* Key Topics */}
      {hasTopics && (
        <div>
          <span className="text-[10px] font-medium text-ui-supportText uppercase tracking-wide">Key Topics</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {doc.key_topics!.map((topic, i) => (
              <span key={i} className="px-2 py-0.5 text-[11px] rounded bg-gray-100 text-gray-700 border border-gray-200">
                {topic}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Keywords */}
      {hasKeywords && (
        <div>
          <span className="text-[10px] font-medium text-ui-supportText uppercase tracking-wide">Keywords</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {doc.keyword_tags!.slice(0, 10).map((kw, i) => (
              <span key={i} className="px-2 py-0.5 text-[11px] rounded-full bg-emerald-50 text-emerald-700">
                {kw}
              </span>
            ))}
            {doc.keyword_tags!.length > 10 && (
              <span className="text-[10px] text-ui-supportText self-center">
                +{doc.keyword_tags!.length - 10} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Contributions */}
      {doc.usage_count > 0 && (
        <div className="flex items-center gap-3 text-[11px] text-ui-supportText pt-1 border-t border-gray-100">
          <span className="font-medium text-ui-bodyText">{doc.usage_count}x used</span>
          {doc.contributed_to.features > 0 && <span>{doc.contributed_to.features} features</span>}
          {doc.contributed_to.personas > 0 && <span>{doc.contributed_to.personas} personas</span>}
          {doc.contributed_to.vp_steps > 0 && <span>{doc.contributed_to.vp_steps} steps</span>}
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Sub-components
// =============================================================================

function QualityBadge({ quality }: { quality: { score: string; message: string; details: string[] } }) {
  const styles: Record<string, { bg: string; border: string; text: string; Icon: typeof Sparkles }> = {
    excellent: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', Icon: Sparkles },
    good: { bg: 'bg-teal-50', border: 'border-teal-200', text: 'text-teal-700', Icon: CheckCircle },
    basic: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600', Icon: Info },
    sparse: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-500', Icon: AlertCircle },
  }
  const style = styles[quality.score] || styles.basic
  const { Icon } = style

  return (
    <div className={`${style.bg} ${style.border} border rounded-lg p-2.5`}>
      <div className="flex items-start gap-2">
        <Icon className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${style.text}`} />
        <div className="flex-1">
          <p className={`text-xs font-medium ${style.text}`}>{quality.message}</p>
          {quality.details.length > 0 && (
            <ul className="mt-1 space-y-0.5">
              {quality.details.map((d, i) => (
                <li key={i} className="text-[11px] text-gray-600">{d}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

function ImpactBar({ source }: { source: SourceUsageItem }) {
  const uses = source.uses_by_entity
  const total = uses.feature + uses.persona + uses.vp_step + (uses.business_driver || 0)
  if (total === 0) return null

  return (
    <div className="flex items-center gap-3 text-[11px] text-ui-supportText pt-1 border-t border-gray-100">
      {/* Mini usage bar */}
      <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden flex-shrink-0">
        <div
          className="h-full bg-brand-teal rounded-full"
          style={{ width: `${Math.min(100, (source.total_uses / Math.max(source.total_uses * 2, 1)) * 100)}%` }}
        />
      </div>
      <span className="font-medium text-ui-bodyText">{source.total_uses} uses</span>
      {uses.feature > 0 && <span>{uses.feature} features</span>}
      {uses.persona > 0 && <span>{uses.persona} personas</span>}
      {uses.vp_step > 0 && <span>{uses.vp_step} steps</span>}
    </div>
  )
}

function QualityDots({ score }: { score: number }) {
  // score is 0-1, map to 1-5 dots
  const filled = Math.max(1, Math.round(score * 5))
  return (
    <div className="flex items-center gap-0.5" title={`Quality: ${Math.round(score * 100)}%`}>
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className={`w-1.5 h-1.5 rounded-full ${i < filled ? 'bg-emerald-400' : 'bg-gray-200'}`}
        />
      ))}
    </div>
  )
}

function TypeBadge({ item }: { item: TimelineItem }) {
  if (item.type === 'research') {
    return (
      <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-emerald-50 text-emerald-700 border border-emerald-100">
        Research
      </span>
    )
  }
  if (item.type === 'document') {
    return (
      <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-teal-50 text-teal-700 border border-teal-100">
        Document
      </span>
    )
  }
  // Signal types
  const typeMap: Record<string, string> = {
    email: 'Email',
    note: 'Note',
    transcript: 'Transcript',
    chat: 'Chat',
    file: 'File',
    portal_response: 'Portal',
  }
  const label = typeMap[item.signalType || ''] || item.signalType || 'Signal'
  return (
    <span className="px-1.5 py-0.5 text-[10px] font-medium rounded bg-gray-100 text-gray-600 border border-gray-200">
      {label}
    </span>
  )
}

function TimelineIcon({ item }: { item: TimelineItem }) {
  const cls = "w-3.5 h-3.5"
  if (item.type === 'research') return <Globe className={`${cls} text-emerald-600`} />
  if (item.type === 'document') return <FileText className={`${cls} text-teal-600`} />
  const iconMap: Record<string, React.ReactNode> = {
    email: <Mail className={`${cls} text-gray-500`} />,
    note: <PenSquare className={`${cls} text-gray-500`} />,
    transcript: <Mic className={`${cls} text-gray-500`} />,
    chat: <MessageSquare className={`${cls} text-gray-500`} />,
    file: <Upload className={`${cls} text-gray-500`} />,
  }
  return <>{iconMap[item.signalType || ''] || <FileText className={`${cls} text-gray-500`} />}</>
}

function getTimelineDotStyle(item: TimelineItem): string {
  if (item.type === 'research') return 'bg-emerald-50 border-emerald-200'
  if (item.type === 'document') return 'bg-teal-50 border-teal-200'
  return 'bg-white border-gray-200'
}

function SectionHeader({ title, right }: { title: string; right?: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-2.5">
      <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide">{title}</h4>
      {typeof right === 'string' ? (
        <span className="text-[11px] text-ui-supportText">{right}</span>
      ) : (
        right
      )}
    </div>
  )
}

// =============================================================================
// Helpers
// =============================================================================

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatScore(value: number): string {
  return `${Math.round(value * 100)}%`
}
