/**
 * SignalsTab Component
 *
 * Unified timeline view of ALL sources: signals, research, and documents.
 * Shows everything in chronological order with appropriate previews.
 */

'use client'

import { useState, useMemo } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ChevronDown, ChevronUp, Sparkles, CheckCircle, AlertCircle, Info, FileText, Globe, ArrowRight } from 'lucide-react'
import { SourceTypeBadge, UsageBar } from '../shared'
import { getSignal, type SourceUsageItem, type DocumentSummaryItem } from '@/lib/api'
import { Markdown } from '@/components/ui/Markdown'

interface QualityInfo {
  score: 'excellent' | 'good' | 'basic' | 'sparse'
  message: string
  details: string[]
}

interface SignalsTabProps {
  signals: SourceUsageItem[]
  documents?: DocumentSummaryItem[]
  isLoading: boolean
  onNavigateToTab?: (tab: 'research' | 'documents') => void
}

type SignalFilter = 'all' | 'email' | 'note' | 'transcript' | 'chat' | 'research' | 'document'

// Unified timeline item type
interface TimelineItem {
  id: string
  type: 'signal' | 'research' | 'document'
  name: string
  signalType?: string | null
  date: string | null
  data: SourceUsageItem | DocumentSummaryItem
}

export function SignalsTab({ signals, documents = [], isLoading, onNavigateToTab }: SignalsTabProps) {
  const [filter, setFilter] = useState<SignalFilter>('all')

  // Build unified timeline from all sources
  const timelineItems = useMemo(() => {
    const items: TimelineItem[] = []

    // Add all signals (including research)
    signals.forEach(s => {
      items.push({
        id: s.source_id,
        type: s.signal_type === 'research' ? 'research' : 'signal',
        name: s.source_name,
        signalType: s.signal_type,
        date: s.last_used,
        data: s,
      })
    })

    // Add documents
    documents.forEach(d => {
      items.push({
        id: d.id,
        type: 'document',
        name: d.original_filename,
        signalType: 'document',
        date: d.created_at || null,
        data: d,
      })
    })

    // Sort by date (most recent first)
    items.sort((a, b) => {
      if (!a.date && !b.date) return 0
      if (!a.date) return 1
      if (!b.date) return -1
      return new Date(b.date).getTime() - new Date(a.date).getTime()
    })

    return items
  }, [signals, documents])

  // Filter timeline items
  const filteredItems = useMemo(() => {
    if (filter === 'all') return timelineItems

    if (filter === 'research') {
      return timelineItems.filter(item => item.type === 'research')
    }

    if (filter === 'document') {
      return timelineItems.filter(item => item.type === 'document')
    }

    // Signal type filter
    return timelineItems.filter(item =>
      item.type === 'signal' && item.signalType === filter
    )
  }, [timelineItems, filter])

  // Get unique types for filter chips
  const availableFilters = useMemo(() => {
    const types = new Set<string>()
    timelineItems.forEach(item => {
      if (item.type === 'research') types.add('research')
      else if (item.type === 'document') types.add('document')
      else if (item.signalType) types.add(item.signalType)
    })
    return Array.from(types)
  }, [timelineItems])

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex gap-4 animate-pulse">
            <div className="w-10 h-10 bg-gray-200 rounded-full" />
            <div className="flex-1 bg-gray-50 rounded-lg p-4">
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-2/3" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (filteredItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No sources yet</h3>
        <p className="text-sm text-gray-500 max-w-sm">
          Sources include emails, notes, transcripts, documents, and research that inform this project.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex items-center gap-2 flex-wrap">
        <FilterChip
          active={filter === 'all'}
          onClick={() => setFilter('all')}
        >
          All ({timelineItems.length})
        </FilterChip>
        {availableFilters.includes('email') && (
          <FilterChip active={filter === 'email'} onClick={() => setFilter('email')}>
            Emails
          </FilterChip>
        )}
        {availableFilters.includes('note') && (
          <FilterChip active={filter === 'note'} onClick={() => setFilter('note')}>
            Notes
          </FilterChip>
        )}
        {availableFilters.includes('transcript') && (
          <FilterChip active={filter === 'transcript'} onClick={() => setFilter('transcript')}>
            Transcripts
          </FilterChip>
        )}
        {availableFilters.includes('chat') && (
          <FilterChip active={filter === 'chat'} onClick={() => setFilter('chat')}>
            Chat
          </FilterChip>
        )}
        {availableFilters.includes('research') && (
          <FilterChip active={filter === 'research'} onClick={() => setFilter('research')}>
            Research
          </FilterChip>
        )}
        {availableFilters.includes('document') && (
          <FilterChip active={filter === 'document'} onClick={() => setFilter('document')}>
            Documents
          </FilterChip>
        )}
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200" />

        <div className="space-y-4">
          {filteredItems.map((item) => (
            <TimelineItemCard
              key={item.id}
              item={item}
              onNavigateToTab={onNavigateToTab}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

function TimelineItemCard({
  item,
  onNavigateToTab,
}: {
  item: TimelineItem
  onNavigateToTab?: (tab: 'research' | 'documents') => void
}) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [content, setContent] = useState<string | null>(null)
  const [quality, setQuality] = useState<QualityInfo | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // Get data based on item type
  const signal = item.type !== 'document' ? (item.data as SourceUsageItem) : null
  const document = item.type === 'document' ? (item.data as DocumentSummaryItem) : null

  const totalContributions = signal
    ? signal.uses_by_entity.feature + signal.uses_by_entity.persona + signal.uses_by_entity.vp_step
    : 0

  const handleExpand = async () => {
    // For research and documents, just toggle - content is already available or we link to the tab
    if (item.type === 'research') {
      // Research has content in the signal data
      if (!isExpanded && signal?.content) {
        setContent(signal.content)
      }
      setIsExpanded(!isExpanded)
      return
    }

    if (item.type === 'document') {
      // Documents show summary and link to Documents tab
      if (!isExpanded && document) {
        setContent(document.content_summary || 'Document uploaded. View in Documents tab for details.')
      }
      setIsExpanded(!isExpanded)
      return
    }

    // For regular signals, fetch content
    if (!isExpanded && content === null && signal) {
      setIsLoading(true)
      try {
        const response = await getSignal(signal.source_id)
        setContent(response.raw_text || 'No content available')

        const metadata = response.metadata || {}
        if (metadata.quality_score) {
          setQuality({
            score: metadata.quality_score,
            message: metadata.quality_message || '',
            details: metadata.quality_details || [],
          })
        }
      } catch (error) {
        console.error('Failed to load signal content:', error)
        setContent('Failed to load content')
      }
      setIsLoading(false)
    }
    setIsExpanded(!isExpanded)
  }

  // Get icon based on type
  const getIcon = () => {
    if (item.type === 'research') {
      return <Globe className="w-4 h-4 text-violet-600" />
    }
    if (item.type === 'document') {
      return <FileText className="w-4 h-4 text-blue-600" />
    }
    return <SourceTypeBadge type={item.signalType || 'note'} showLabel={false} />
  }

  // Get badge color based on type
  const getDotStyle = () => {
    if (item.type === 'research') return 'bg-violet-50 border-violet-200'
    if (item.type === 'document') return 'bg-blue-50 border-blue-200'
    return 'bg-white border-gray-200'
  }

  // Quality badge styling
  const getQualityBadge = () => {
    if (!quality) return null

    const styles = {
      excellent: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', icon: <Sparkles className="w-4 h-4 text-emerald-500" /> },
      good: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', icon: <CheckCircle className="w-4 h-4 text-blue-500" /> },
      basic: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', icon: <Info className="w-4 h-4 text-amber-500" /> },
      sparse: { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-600', icon: <AlertCircle className="w-4 h-4 text-gray-400" /> },
    }

    const style = styles[quality.score] || styles.basic

    return (
      <div className={`${style.bg} ${style.border} border rounded-lg p-3 mb-3`}>
        <div className="flex items-start gap-2">
          {style.icon}
          <div className="flex-1">
            <p className={`text-sm font-medium ${style.text}`}>{quality.message}</p>
            {quality.details.length > 0 && (
              <ul className="mt-2 space-y-1">
                {quality.details.map((detail, i) => (
                  <li key={i} className="text-xs text-gray-600">
                    <Markdown content={detail} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-4 relative">
      {/* Timeline dot */}
      <div className={`w-10 h-10 rounded-full border-2 flex items-center justify-center z-10 ${getDotStyle()}`}>
        {getIcon()}
      </div>

      {/* Content card */}
      <div className="flex-1 bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div
          className="flex items-start justify-between gap-4 cursor-pointer"
          onClick={handleExpand}
        >
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-gray-900 truncate">
              {item.name}
            </h4>
            {item.date && (
              <p className="text-xs text-gray-500 mt-0.5">
                {formatDistanceToNow(new Date(item.date), { addSuffix: true })}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            {item.type === 'research' && (
              <span className="px-2 py-0.5 text-xs font-medium bg-violet-100 text-violet-700 rounded-full">
                Research
              </span>
            )}
            {item.type === 'document' && (
              <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 rounded-full">
                Document
              </span>
            )}
            {item.type === 'signal' && (
              <SourceTypeBadge type={item.signalType || 'note'} showLabel={true} />
            )}
            <button className="p-1 text-gray-400 hover:text-gray-600">
              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Expanded content */}
        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            {isLoading ? (
              <div className="text-sm text-gray-400 italic">Loading content...</div>
            ) : (
              <>
                {getQualityBadge()}

                {/* Content preview */}
                {content ? (
                  <div className="bg-white rounded-lg border border-gray-100 p-4">
                    <div className={`prose prose-sm max-w-none ${item.type === 'research' ? 'line-clamp-10' : ''}`}>
                      <Markdown content={content} />
                    </div>

                    {/* Link to full view for research/documents */}
                    {item.type === 'research' && onNavigateToTab && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onNavigateToTab('research')
                        }}
                        className="mt-3 flex items-center gap-1 text-sm font-medium text-violet-600 hover:text-violet-700"
                      >
                        View full research <ArrowRight className="w-4 h-4" />
                      </button>
                    )}
                    {item.type === 'document' && onNavigateToTab && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          onNavigateToTab('documents')
                        }}
                        className="mt-3 flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
                      >
                        View in Documents <ArrowRight className="w-4 h-4" />
                      </button>
                    )}

                    {content.length > 500 && item.type === 'signal' && (
                      <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-400">
                        {content.length.toLocaleString()} characters
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-gray-400 italic">No content available</div>
                )}
              </>
            )}
          </div>
        )}

        {/* Impact summary for signals */}
        {signal && totalContributions > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
            <div className="flex-1 max-w-[100px]">
              <UsageBar count={signal.total_uses} size="sm" />
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500">
              {signal.uses_by_entity.feature > 0 && <span>{signal.uses_by_entity.feature} features</span>}
              {signal.uses_by_entity.persona > 0 && <span>{signal.uses_by_entity.persona} personas</span>}
              {signal.uses_by_entity.vp_step > 0 && <span>{signal.uses_by_entity.vp_step} steps</span>}
            </div>
          </div>
        )}

        {/* Document metadata */}
        {document && (
          <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-500">
            {document.file_type && <span className="uppercase">{document.file_type}</span>}
            {document.page_count && <span>{document.page_count} pages</span>}
            {document.processing_status && (
              <span className={`px-1.5 py-0.5 rounded ${
                document.processing_status === 'processed' ? 'bg-green-100 text-green-700' :
                document.processing_status === 'processing' ? 'bg-amber-100 text-amber-700' :
                'bg-gray-100 text-gray-600'
              }`}>
                {document.processing_status}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`
        px-3 py-1.5 text-xs font-medium rounded-full transition-colors
        ${active
          ? 'bg-brand-primary text-white'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
        }
      `}
    >
      {children}
    </button>
  )
}
