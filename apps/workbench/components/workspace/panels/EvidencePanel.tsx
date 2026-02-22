/**
 * EvidencePanel - Sources and evidence quality view
 *
 * Layout:
 * 1. Source Usage (dynamic highlight cards — only shows entity types with count > 0)
 * 2. Evidence Quality (green palette bars)
 * 3. Chronological Timeline (newest first, deduplicated, expandable cards)
 *    - Content tab: formatted transcript / document summary / research markdown
 *    - Analysis tab: extracted entities, scores, topics, keywords
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import {
  FileText,
  CheckCircle,
  AlertCircle,
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
  Users,
  GitBranch,
  ShieldCheck,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import {
  getEvidenceQuality,
  getDocumentsSummary,
  getSourceUsage,
  getSignal,
  getSignalImpact,
  getProcessingResults,
  getDocumentDownloadUrl,
  withdrawDocument,
  getRequirementsIntelligence,
} from '@/lib/api'
import type {
  EvidenceQualityResponse,
  DocumentSummaryResponse,
  SourceUsageResponse,
  SourceUsageItem,
  SourceUsageByEntity,
  DocumentSummaryItem,
  RequirementsIntelligenceResponse,
  SignalImpactResponse,
} from '@/lib/api'
import type {
  ProcessingResultsResponse,
  EntityChangeItem,
} from '@/types/api'
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
                  ? 'bg-[#3FAF7A]/10 text-[#3FAF7A]'
                  : 'text-[#999999] hover:text-[#333333] hover:bg-[#F9F9F9]'
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
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-[#3FAF7A]" />
            </div>
          ) : !evidence && !documents && !sourceUsage ? (
            <p className="text-sm text-[#999999] text-center py-8">
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
// 1. Source Usage — dynamic highlight cards (only non-zero types)
// =============================================================================

const ALL_ENTITY_CARDS: {
  key: keyof SourceUsageByEntity
  label: string
  icon: typeof Sparkles
  accent: string
}[] = [
  { key: 'feature', label: 'Features', icon: Sparkles, accent: 'text-emerald-600 bg-emerald-50' },
  { key: 'persona', label: 'Personas', icon: MessageSquare, accent: 'text-teal-600 bg-teal-50' },
  { key: 'vp_step', label: 'VP Steps', icon: CheckCircle, accent: 'text-emerald-600 bg-emerald-50' },
  { key: 'business_driver', label: 'Drivers', icon: BarChart3, accent: 'text-teal-600 bg-teal-50' },
  { key: 'stakeholder', label: 'Stakeholders', icon: Users, accent: 'text-emerald-600 bg-emerald-50' },
  { key: 'workflow', label: 'Workflows', icon: GitBranch, accent: 'text-teal-600 bg-teal-50' },
  { key: 'data_entity', label: 'Data Entities', icon: Database, accent: 'text-emerald-600 bg-emerald-50' },
  { key: 'constraint', label: 'Constraints', icon: ShieldCheck, accent: 'text-teal-600 bg-teal-50' },
]

function SourceUsageCards({ sourceUsage }: { sourceUsage: SourceUsageResponse }) {
  const totals = useMemo(() => {
    const result: Record<string, number> = {}
    for (const card of ALL_ENTITY_CARDS) {
      result[card.key] = 0
    }
    sourceUsage.sources.forEach((s) => {
      for (const card of ALL_ENTITY_CARDS) {
        result[card.key] += s.uses_by_entity[card.key] || 0
      }
    })
    return result
  }, [sourceUsage])

  // Only show cards with count > 0
  const visibleCards = ALL_ENTITY_CARDS.filter((card) => totals[card.key] > 0)

  if (visibleCards.length === 0) return null

  return (
    <div>
      <SectionHeader
        title="Source Usage"
        right={`${sourceUsage.sources.length} source${sourceUsage.sources.length !== 1 ? 's' : ''}`}
      />
      <div className="grid grid-cols-4 gap-3">
        {visibleCards.map((card) => {
          const Icon = card.icon
          return (
            <div key={card.key} className="bg-[#F9F9F9] rounded-lg px-3 py-2 flex items-center gap-2.5">
              <div className={`w-7 h-7 rounded-full ${card.accent} flex items-center justify-center flex-shrink-0`}>
                <Icon className="w-3.5 h-3.5" />
              </div>
              <div>
                <p className="text-base font-bold text-[#333333] leading-tight">{totals[card.key]}</p>
                <p className="text-[10px] text-[#999999] leading-tight">{card.label}</p>
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
              <span className="text-[11px] text-[#999999] w-32 truncate">{label}</span>
              <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className={`h-full ${barColor} rounded-full transition-all`}
                  style={{ width: `${data.percentage}%` }}
                />
              </div>
              <span className="text-[11px] text-[#333333] w-8 text-right">{data.count}</span>
            </div>
          )
        })}
      </div>
      {evidence.summary && (
        <p className="text-[11px] text-[#999999] mt-2 italic">{evidence.summary}</p>
      )}
    </div>
  )
}

// =============================================================================
// 3. Chronological Timeline — deduplicated (signals + documents merged)
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

    // Index documents by signal_id for dedup
    const docBySignalId = new Map<string, DocumentSummaryItem>()
    for (const d of documents) {
      if (d.signal_id) {
        docBySignalId.set(d.signal_id, d)
      }
    }
    const mergedDocIds = new Set<string>()

    // Process signals — merge with matching document if one exists
    sources.forEach((s) => {
      const matchingDoc = docBySignalId.get(s.source_id)
      if (matchingDoc) {
        // Merged entry: document + signal usage data
        mergedDocIds.add(matchingDoc.id)
        list.push({
          id: matchingDoc.id,
          type: 'document',
          name: matchingDoc.original_filename,
          signalType: 'document',
          date: matchingDoc.created_at || s.last_used,
          sourceData: s,
          docData: matchingDoc,
        })
      } else {
        list.push({
          id: s.source_id,
          type: s.signal_type === 'research' ? 'research' : 'signal',
          name: s.source_name,
          signalType: s.signal_type,
          date: s.last_used,
          sourceData: s,
          docData: null,
        })
      }
    })

    // Add remaining unmerged documents
    documents.forEach((d) => {
      if (!mergedDocIds.has(d.id)) {
        list.push({
          id: d.id,
          type: 'document',
          name: d.original_filename,
          signalType: 'document',
          date: d.created_at || null,
          sourceData: null,
          docData: d,
        })
      }
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
      <p className="text-sm text-[#999999] text-center py-4">
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
// Timeline Card — expandable, with Content / Analysis toggle
// =============================================================================

type ExpandedTab = 'content' | 'analysis'

function TimelineCard({ item, onDocumentRemoved }: { item: TimelineItem; onDocumentRemoved?: () => void }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [expandedTab, setExpandedTab] = useState<ExpandedTab>('content')
  const [content, setContent] = useState<string | null>(null)
  const [quality, setQuality] = useState<{
    score: 'excellent' | 'good' | 'basic' | 'sparse'
    message: string
    details: string[]
  } | null>(null)
  const [impactData, setImpactData] = useState<SignalImpactResponse | null>(null)
  const [loadingContent, setLoadingContent] = useState(false)
  const [loadingImpact, setLoadingImpact] = useState(false)
  const [copied, setCopied] = useState(false)
  const [isDownloading, setIsDownloading] = useState(false)
  const [isWithdrawing, setIsWithdrawing] = useState(false)

  // Determine which signal_id to use for impact loading
  const signalIdForImpact = item.sourceData?.source_id || item.docData?.signal_id || null

  const handleToggle = async () => {
    if (!isExpanded) {
      // Load content on first expand
      if (content === null) {
        if (item.type === 'research' && item.sourceData?.content) {
          setContent(item.sourceData.content)
        } else if (item.type === 'document' && item.docData) {
          // For documents, load the signal's raw text for Content tab
          if (item.docData.signal_id) {
            setLoadingContent(true)
            try {
              const response = await getSignal(item.docData.signal_id)
              setContent(response.raw_text || item.docData.content_summary || 'No content available.')
            } catch {
              setContent(item.docData.content_summary || 'No content available.')
            }
            setLoadingContent(false)
          } else {
            setContent(item.docData.content_summary || 'No summary available.')
          }
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

  // Lazy-load impact data when switching to analysis tab
  const handleTabSwitch = async (tab: ExpandedTab) => {
    setExpandedTab(tab)
    if (tab === 'analysis' && !impactData && !loadingImpact && signalIdForImpact) {
      setLoadingImpact(true)
      try {
        const data = await getSignalImpact(signalIdForImpact)
        setImpactData(data)
      } catch {
        // Silently fail — analysis view will show "no data"
      }
      setLoadingImpact(false)
    }
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

  // Show Content/Analysis toggle when the item has a signal behind it
  const showToggle = item.type === 'document' || item.type === 'signal'

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
            <h4 className="text-sm font-medium text-[#333333] truncate">{item.name}</h4>
            <div className="flex items-center gap-2 mt-0.5">
              {item.date && (
                <span className="text-[10px] text-[#999999]">
                  {formatDistanceToNow(new Date(item.date), { addSuffix: true })}
                </span>
              )}
              {/* Usage count */}
              {item.sourceData && item.sourceData.total_uses > 0 && (
                <span className="text-[10px] text-emerald-600 font-medium">
                  {item.sourceData.total_uses} uses
                </span>
              )}
              {!item.sourceData && item.docData && item.docData.usage_count > 0 && (
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
                  className="p-1.5 rounded-md text-gray-400 hover:text-[#333333] hover:bg-gray-200/50 transition-colors disabled:opacity-40"
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
                className="p-1.5 rounded-md text-gray-400 hover:text-[#333333] hover:bg-gray-200/50 transition-colors"
                title={copied ? 'Copied!' : 'Copy'}
              >
                {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            )}
            <TypeBadge item={item} />
            <Chevron className="w-3.5 h-3.5 text-[#999999]" />
          </div>
        </button>

        {/* Expanded content */}
        {isExpanded && (
          <div className="px-3 pb-3 pt-1 border-t border-gray-200">
            {/* Content / Analysis toggle */}
            {showToggle && (
              <div className="flex items-center gap-1 mb-2 mt-1">
                <button
                  onClick={() => handleTabSwitch('content')}
                  className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                    expandedTab === 'content'
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'text-[#999999] hover:text-[#333333] hover:bg-gray-100'
                  }`}
                >
                  Content
                </button>
                <button
                  onClick={() => handleTabSwitch('analysis')}
                  className={`px-2 py-1 rounded text-[11px] font-medium transition-colors ${
                    expandedTab === 'analysis'
                      ? 'bg-emerald-50 text-emerald-700'
                      : 'text-[#999999] hover:text-[#333333] hover:bg-gray-100'
                  }`}
                >
                  Analysis
                </button>
              </div>
            )}

            {loadingContent ? (
              <div className="flex items-center gap-2 py-3">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#3FAF7A]" />
                <span className="text-xs text-[#999999]">Loading...</span>
              </div>
            ) : (
              <div className="space-y-3 mt-1">
                {/* ===== CONTENT TAB ===== */}
                {expandedTab === 'content' && (
                  <>
                    {/* Quality badge (for signals with quality metadata) */}
                    {quality && <QualityBadge quality={quality} />}

                    {/* Document content view (lightweight) */}
                    {item.type === 'document' && item.docData && (
                      <DocumentContentView doc={item.docData} content={content} />
                    )}

                    {/* Signal content (formatted transcript) */}
                    {item.type === 'signal' && content && (
                      <div className="bg-white rounded-lg border border-gray-100 p-3">
                        <Markdown
                          content={formatTranscriptContent(content)}
                          className="text-sm text-[#333333] [&_h1]:text-sm [&_h2]:text-[13px] [&_h3]:text-[13px] [&_p]:text-sm [&_li]:text-sm"
                        />
                      </div>
                    )}

                    {/* Research content */}
                    {item.type === 'research' && content && (
                      <>
                        <div className="bg-white rounded-lg border border-gray-100 p-3">
                          <Markdown
                            content={content}
                            className="text-sm text-[#333333] [&_h1]:text-sm [&_h2]:text-[13px] [&_h3]:text-[13px] [&_p]:text-sm [&_li]:text-sm"
                          />
                        </div>
                        <div className="flex justify-end">
                          <button
                            onClick={handleCopy}
                            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-[#999999] hover:text-[#333333] bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
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
                      </>
                    )}
                  </>
                )}

                {/* ===== ANALYSIS TAB ===== */}
                {expandedTab === 'analysis' && (
                  <>
                    {/* Document analysis — show processing results if signal_id available */}
                    {item.type === 'document' && item.docData && (
                      <div className="space-y-3">
                        <DocumentAnalysisView doc={item.docData} />
                        {signalIdForImpact && (
                          <div className="pt-2 border-t border-gray-100">
                            <ProcessingResultsView signalId={signalIdForImpact} />
                          </div>
                        )}
                      </div>
                    )}

                    {/* Signal impact analysis — show processing results first, fallback to impact */}
                    {item.type === 'signal' && signalIdForImpact && (
                      <ProcessingResultsView signalId={signalIdForImpact} />
                    )}
                    {item.type === 'signal' && !signalIdForImpact && (
                      <ImpactAnalysisView
                        impactData={impactData}
                        loading={loadingImpact}
                        sourceData={item.sourceData}
                      />
                    )}
                  </>
                )}

                {/* Impact breakdown for signals (always visible at bottom of content tab) */}
                {expandedTab === 'content' && item.sourceData && <ImpactBar source={item.sourceData} />}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Document Content View — lightweight file metadata + summary
// =============================================================================

function DocumentContentView({ doc, content }: { doc: DocumentSummaryItem; content: string | null }) {
  return (
    <div className="space-y-3">
      {/* File metadata */}
      <div className="flex items-center gap-3 text-[11px] text-[#999999]">
        <span>{formatFileSize(doc.file_size_bytes)}</span>
        {doc.page_count && (
          <>
            <span>·</span>
            <span>{doc.page_count} pages</span>
          </>
        )}
        <span>·</span>
        <span className="uppercase">{doc.file_type}</span>
      </div>

      {/* Content — either full signal text or summary */}
      {content && (
        <div className="bg-white rounded-lg border border-gray-100 p-3">
          <Markdown
            content={formatTranscriptContent(content)}
            className="text-sm text-[#333333] [&_h1]:text-sm [&_h2]:text-[13px] [&_h3]:text-[13px] [&_p]:text-sm [&_li]:text-sm"
          />
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Document Analysis View — scores, topics, keywords, contributions
// =============================================================================

function DocumentAnalysisView({ doc }: { doc: DocumentSummaryItem }) {
  const hasScores = doc.quality_score != null || doc.relevance_score != null || doc.information_density != null
  const hasTopics = doc.key_topics && doc.key_topics.length > 0
  const hasKeywords = doc.keyword_tags && doc.keyword_tags.length > 0

  return (
    <div className="space-y-3">
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
          <span className="text-[10px] font-medium text-[#999999] uppercase tracking-wide">Key Topics</span>
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
          <span className="text-[10px] font-medium text-[#999999] uppercase tracking-wide">Keywords</span>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {doc.keyword_tags!.slice(0, 10).map((kw, i) => (
              <span key={i} className="px-2 py-0.5 text-[11px] rounded-full bg-emerald-50 text-emerald-700">
                {kw}
              </span>
            ))}
            {doc.keyword_tags!.length > 10 && (
              <span className="text-[10px] text-[#999999] self-center">
                +{doc.keyword_tags!.length - 10} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Contributions — dynamic */}
      {doc.usage_count > 0 && <ContributionsRow contributed_to={doc.contributed_to} usage_count={doc.usage_count} />}

      {!hasScores && !hasTopics && !hasKeywords && doc.usage_count === 0 && (
        <p className="text-xs text-[#999999] italic py-2">No analysis data available yet.</p>
      )}
    </div>
  )
}

// =============================================================================
// Processing Results View — rich breakdown from V2 pipeline
// =============================================================================

function ProcessingResultsView({
  signalId,
}: {
  signalId: string
}) {
  const [data, setData] = useState<ProcessingResultsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set(['created', 'updated', 'memory']))

  useEffect(() => {
    setLoading(true)
    getProcessingResults(signalId)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [signalId])

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-3">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#3FAF7A]" />
        <span className="text-xs text-[#999999]">Loading processing results...</span>
      </div>
    )
  }

  if (!data || data.summary.total_entities_affected === 0) {
    return <p className="text-xs text-[#999999] italic py-2">No processing results available.</p>
  }

  const { summary } = data

  // Group entity changes by revision_type, then by entity_type
  const created = data.entity_changes.filter((c) => c.revision_type === 'created')
  const updated = data.entity_changes.filter((c) => c.revision_type !== 'created')

  const groupByType = (items: EntityChangeItem[]) => {
    const groups: Record<string, EntityChangeItem[]> = {}
    for (const item of items) {
      if (!groups[item.entity_type]) groups[item.entity_type] = []
      groups[item.entity_type].push(item)
    }
    return groups
  }

  const toggleSection = (key: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  return (
    <div className="space-y-3">
      {/* Summary bar */}
      <div className="flex items-center gap-3 text-[11px] text-[#999999] flex-wrap">
        {summary.created > 0 && (
          <span className="font-medium text-emerald-700">{summary.created} created</span>
        )}
        {summary.updated > 0 && (
          <span className="font-medium text-indigo-600">{summary.updated} updated</span>
        )}
        {summary.merged > 0 && (
          <span className="font-medium text-amber-600">{summary.merged} merged</span>
        )}
        {summary.memory_facts_added > 0 && (
          <span>{summary.memory_facts_added} facts</span>
        )}
        <span className="text-gray-400">|</span>
        <span>Strategy: {summary.triage_strategy}</span>
      </div>

      {/* Created entities */}
      {created.length > 0 && (
        <div>
          <button
            onClick={() => toggleSection('created')}
            className="flex items-center gap-1.5 w-full text-left"
          >
            {expandedSections.has('created') ? (
              <ChevronDown className="w-3 h-3 text-[#999999]" />
            ) : (
              <ChevronUp className="w-3 h-3 text-[#999999]" />
            )}
            <span className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wide">
              Created ({created.length})
            </span>
          </button>
          {expandedSections.has('created') && (
            <div className="mt-1.5 space-y-2 pl-4">
              {Object.entries(groupByType(created)).map(([entityType, items]) => {
                const style = ENTITY_TYPE_STYLES[entityType] || { label: entityType, bg: 'bg-gray-100', text: 'text-gray-700' }
                return (
                  <div key={entityType}>
                    <span className="text-[10px] font-medium text-[#999999]">
                      {style.label} ({items.length})
                    </span>
                    <div className="flex flex-wrap gap-1 mt-0.5">
                      {items.map((item) => (
                        <span
                          key={item.entity_id}
                          className={`px-2 py-0.5 text-[11px] rounded-full ${style.bg} ${style.text}`}
                        >
                          {item.entity_label}
                        </span>
                      ))}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Updated entities */}
      {updated.length > 0 && (
        <div>
          <button
            onClick={() => toggleSection('updated')}
            className="flex items-center gap-1.5 w-full text-left"
          >
            {expandedSections.has('updated') ? (
              <ChevronDown className="w-3 h-3 text-[#999999]" />
            ) : (
              <ChevronUp className="w-3 h-3 text-[#999999]" />
            )}
            <span className="text-[10px] font-semibold text-indigo-600 uppercase tracking-wide">
              Updated ({updated.length})
            </span>
          </button>
          {expandedSections.has('updated') && (
            <div className="mt-1.5 space-y-1.5 pl-4">
              {updated.map((item) => {
                const style = ENTITY_TYPE_STYLES[item.entity_type] || { label: item.entity_type, bg: 'bg-gray-100', text: 'text-gray-700' }
                return (
                  <div key={item.entity_id} className="flex items-start gap-2">
                    <span className={`px-1.5 py-0.5 text-[10px] rounded ${style.bg} ${style.text} flex-shrink-0`}>
                      {style.label.replace(/s$/, '')}
                    </span>
                    <div className="min-w-0">
                      <span className="text-xs font-medium text-[#333333]">{item.entity_label}</span>
                      {item.diff_summary && (
                        <span className="text-[11px] text-[#999999] ml-1.5">
                          — {item.diff_summary}
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Memory updates */}
      {data.memory_updates.length > 0 && (
        <div>
          <button
            onClick={() => toggleSection('memory')}
            className="flex items-center gap-1.5 w-full text-left"
          >
            {expandedSections.has('memory') ? (
              <ChevronDown className="w-3 h-3 text-[#999999]" />
            ) : (
              <ChevronUp className="w-3 h-3 text-[#999999]" />
            )}
            <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">
              Memory ({data.memory_updates.length})
            </span>
          </button>
          {expandedSections.has('memory') && (
            <div className="mt-1.5 space-y-1 pl-4">
              {data.memory_updates.map((mem) => (
                <div key={mem.id} className="flex items-start gap-2 text-[11px]">
                  <span className="text-[#999999] flex-shrink-0">{mem.node_type}:</span>
                  <span className="text-[#333333]">&ldquo;{mem.content}&rdquo;</span>
                  {mem.confidence != null && (
                    <span className="text-[#999999] flex-shrink-0">({(mem.confidence * 100).toFixed(0)}%)</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pipeline decisions */}
      {(summary.confidence_distribution && Object.keys(summary.confidence_distribution).length > 0) && (
        <div className="pt-2 border-t border-gray-100">
          <span className="text-[10px] font-semibold text-[#999999] uppercase tracking-wide">
            Pipeline Decisions
          </span>
          <div className="flex flex-wrap gap-2 mt-1 text-[11px] text-[#999999]">
            {Object.entries(summary.confidence_distribution).map(([level, count]) => (
              <span key={level}>{count} {level}</span>
            ))}
            {summary.escalated > 0 && (
              <span className="text-amber-600">{summary.escalated} escalated</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Impact Analysis View — entities grouped by type with colored pills
// =============================================================================

const ENTITY_TYPE_STYLES: Record<string, { label: string; bg: string; text: string }> = {
  feature: { label: 'Features', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  persona: { label: 'Personas', bg: 'bg-teal-50', text: 'text-teal-700' },
  vp_step: { label: 'VP Steps', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  stakeholder: { label: 'Stakeholders', bg: 'bg-teal-50', text: 'text-teal-700' },
  workflow: { label: 'Workflows', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  data_entity: { label: 'Data Entities', bg: 'bg-teal-50', text: 'text-teal-700' },
  constraint: { label: 'Constraints', bg: 'bg-gray-100', text: 'text-gray-700' },
  business_driver: { label: 'Drivers', bg: 'bg-emerald-50', text: 'text-emerald-700' },
  competitor: { label: 'Competitors', bg: 'bg-gray-100', text: 'text-gray-700' },
  insight: { label: 'Insights', bg: 'bg-teal-50', text: 'text-teal-700' },
}

function ImpactAnalysisView({
  impactData,
  loading,
  sourceData,
}: {
  impactData: SignalImpactResponse | null
  loading: boolean
  sourceData: SourceUsageItem | null
}) {
  if (loading) {
    return (
      <div className="flex items-center gap-2 py-3">
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#3FAF7A]" />
        <span className="text-xs text-[#999999]">Loading analysis...</span>
      </div>
    )
  }

  // Fallback to sourceData counts if no impact data
  if (!impactData && sourceData) {
    return <ImpactBar source={sourceData} />
  }

  if (!impactData || impactData.total_impacts === 0) {
    return <p className="text-xs text-[#999999] italic py-2">No entity extractions recorded yet.</p>
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs">
        <span className="font-medium text-[#333333]">{impactData.total_impacts} entities extracted</span>
      </div>

      {Object.entries(impactData.details).map(([entityType, entities]) => {
        if (!entities || entities.length === 0) return null
        const style = ENTITY_TYPE_STYLES[entityType] || { label: entityType, bg: 'bg-gray-100', text: 'text-gray-700' }

        return (
          <div key={entityType}>
            <span className="text-[10px] font-medium text-[#999999] uppercase tracking-wide">
              {style.label} ({entities.length})
            </span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {entities.map((entity) => {
                const displayName = entity.label || entity.name || entity.slug || entity.id.slice(0, 8)
                return (
                  <span
                    key={entity.id}
                    className={`px-2 py-0.5 text-[11px] rounded-full ${style.bg} ${style.text}`}
                  >
                    {displayName}
                  </span>
                )
              })}
            </div>
          </div>
        )
      })}
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

/** Dynamic impact bar — shows all entity types with count > 0 */
function ImpactBar({ source }: { source: SourceUsageItem }) {
  const uses = source.uses_by_entity
  const entries: { label: string; count: number }[] = [
    { label: 'features', count: uses.feature || 0 },
    { label: 'personas', count: uses.persona || 0 },
    { label: 'steps', count: uses.vp_step || 0 },
    { label: 'drivers', count: uses.business_driver || 0 },
    { label: 'stakeholders', count: uses.stakeholder || 0 },
    { label: 'workflows', count: uses.workflow || 0 },
    { label: 'data entities', count: uses.data_entity || 0 },
    { label: 'constraints', count: uses.constraint || 0 },
  ].filter((e) => e.count > 0)

  if (entries.length === 0) return null

  return (
    <div className="flex items-center gap-3 text-[11px] text-[#999999] pt-1 border-t border-gray-100 flex-wrap">
      {/* Mini usage bar */}
      <div className="w-16 h-1.5 bg-gray-100 rounded-full overflow-hidden flex-shrink-0">
        <div
          className="h-full bg-[#3FAF7A] rounded-full"
          style={{ width: `${Math.min(100, (source.total_uses / Math.max(source.total_uses * 2, 1)) * 100)}%` }}
        />
      </div>
      <span className="font-medium text-[#333333]">{source.total_uses} uses</span>
      {entries.map((e) => (
        <span key={e.label}>{e.count} {e.label}</span>
      ))}
    </div>
  )
}

/** Dynamic contributions row for documents */
function ContributionsRow({ contributed_to, usage_count }: { contributed_to: DocumentSummaryItem['contributed_to']; usage_count: number }) {
  const entries: { label: string; count: number }[] = [
    { label: 'features', count: contributed_to.features || 0 },
    { label: 'personas', count: contributed_to.personas || 0 },
    { label: 'steps', count: contributed_to.vp_steps || 0 },
    { label: 'stakeholders', count: contributed_to.stakeholders || 0 },
    { label: 'workflows', count: contributed_to.workflows || 0 },
    { label: 'data entities', count: contributed_to.data_entities || 0 },
    { label: 'constraints', count: contributed_to.constraints || 0 },
    { label: 'drivers', count: contributed_to.business_drivers || 0 },
  ].filter((e) => e.count > 0)

  return (
    <div className="flex items-center gap-3 text-[11px] text-[#999999] pt-1 border-t border-gray-100 flex-wrap">
      <span className="font-medium text-[#333333]">{usage_count}x used</span>
      {entries.map((e) => (
        <span key={e.label}>{e.count} {e.label}</span>
      ))}
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
      <h4 className="text-xs font-semibold text-[#333333] uppercase tracking-wide">{title}</h4>
      {typeof right === 'string' ? (
        <span className="text-[11px] text-[#999999]">{right}</span>
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

/**
 * Format raw transcript/signal text for better readability:
 * - Timestamps [HH:MM:SS] get line breaks before them
 * - Speaker turns "Name:" get bolded
 * - Section markers "— Section N —" become headings
 * - Excessive blank lines cleaned up
 */
function formatTranscriptContent(rawText: string): string {
  // Detect if this looks like a transcript (has timestamps or speaker patterns)
  const hasTimestamps = /\[\d{1,2}:\d{2}(:\d{2})?\]/.test(rawText)
  const hasSpeakerTurns = /^[A-Z][a-zA-Z\s]+:(?:\s)/m.test(rawText)

  if (!hasTimestamps && !hasSpeakerTurns) {
    // Not a transcript — return as-is
    return rawText
  }

  let formatted = rawText

  // Insert line breaks before timestamps
  formatted = formatted.replace(/(\[(\d{1,2}:\d{2}(:\d{2})?)?\])/g, '\n\n$1')

  // Bold speaker turns (e.g., "John Smith:" at start of line)
  formatted = formatted.replace(/^([A-Z][a-zA-Z\s]{1,40}):\s/gm, '**$1:** ')

  // Convert section markers to headings
  formatted = formatted.replace(/—\s*(Section\s+\d+[^—]*)\s*—/g, '\n### $1\n')

  // Clean up excessive blank lines (3+ → 2)
  formatted = formatted.replace(/\n{3,}/g, '\n\n')

  return formatted.trim()
}
