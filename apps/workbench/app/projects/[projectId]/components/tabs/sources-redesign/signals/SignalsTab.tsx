/**
 * SignalsTab Component
 *
 * Timeline view of signals (emails, notes, transcripts, chat).
 */

'use client'

import { useState, useMemo } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ChevronDown, ChevronUp, Sparkles, CheckCircle, AlertCircle, Info } from 'lucide-react'
import { SourceTypeBadge, UsageBar } from '../shared'
import { getSignal, type SourceUsageItem } from '@/lib/api'
import { Markdown } from '@/components/ui/Markdown'

interface QualityInfo {
  score: 'excellent' | 'good' | 'basic' | 'sparse'
  message: string
  details: string[]
}

interface SignalsTabProps {
  signals: SourceUsageItem[]
  isLoading: boolean
}

type SignalFilter = 'all' | 'email' | 'note' | 'transcript' | 'chat'

export function SignalsTab({ signals, isLoading }: SignalsTabProps) {
  const [filter, setFilter] = useState<SignalFilter>('all')

  // Filter signals (exclude research type - that's in Research tab)
  const filteredSignals = useMemo(() => {
    let result = signals.filter(s => s.signal_type !== 'research')

    if (filter !== 'all') {
      result = result.filter(s => s.signal_type === filter)
    }

    return result
  }, [signals, filter])

  // Get unique signal types for filter chips
  const signalTypes = useMemo(() => {
    const types = new Set(signals
      .filter(s => s.signal_type !== 'research')
      .map(s => s.signal_type)
      .filter(Boolean) as string[]
    )
    return Array.from(types)
  }, [signals])

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

  if (filteredSignals.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No signals yet</h3>
        <p className="text-sm text-gray-500 max-w-sm">
          Signals include emails, notes, transcripts, and chat messages that provide project context.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filter chips */}
      <div className="flex items-center gap-2">
        <FilterChip
          active={filter === 'all'}
          onClick={() => setFilter('all')}
        >
          All
        </FilterChip>
        {signalTypes.includes('email') && (
          <FilterChip active={filter === 'email'} onClick={() => setFilter('email')}>
            Emails
          </FilterChip>
        )}
        {signalTypes.includes('note') && (
          <FilterChip active={filter === 'note'} onClick={() => setFilter('note')}>
            Notes
          </FilterChip>
        )}
        {signalTypes.includes('transcript') && (
          <FilterChip active={filter === 'transcript'} onClick={() => setFilter('transcript')}>
            Transcripts
          </FilterChip>
        )}
        {signalTypes.includes('chat') && (
          <FilterChip active={filter === 'chat'} onClick={() => setFilter('chat')}>
            Chat
          </FilterChip>
        )}
      </div>

      {/* Timeline */}
      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200" />

        <div className="space-y-4">
          {filteredSignals.map((signal) => (
            <SignalTimelineItem key={signal.source_id} signal={signal} />
          ))}
        </div>
      </div>
    </div>
  )
}

function SignalTimelineItem({ signal }: { signal: SourceUsageItem }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [content, setContent] = useState<string | null>(null)
  const [quality, setQuality] = useState<QualityInfo | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const totalContributions =
    signal.uses_by_entity.feature +
    signal.uses_by_entity.persona +
    signal.uses_by_entity.vp_step

  const handleExpand = async () => {
    if (!isExpanded && content === null) {
      setIsLoading(true)
      try {
        const response = await getSignal(signal.source_id)
        setContent(response.raw_text || 'No content available')

        // Extract quality info from metadata
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

  // Quality badge styling
  const getQualityBadge = () => {
    if (!quality) return null

    const styles = {
      excellent: {
        bg: 'bg-emerald-50',
        border: 'border-emerald-200',
        text: 'text-emerald-700',
        icon: <Sparkles className="w-4 h-4 text-emerald-500" />,
      },
      good: {
        bg: 'bg-blue-50',
        border: 'border-blue-200',
        text: 'text-blue-700',
        icon: <CheckCircle className="w-4 h-4 text-blue-500" />,
      },
      basic: {
        bg: 'bg-amber-50',
        border: 'border-amber-200',
        text: 'text-amber-700',
        icon: <Info className="w-4 h-4 text-amber-500" />,
      },
      sparse: {
        bg: 'bg-gray-50',
        border: 'border-gray-200',
        text: 'text-gray-600',
        icon: <AlertCircle className="w-4 h-4 text-gray-400" />,
      },
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
      <div className="w-10 h-10 rounded-full bg-white border-2 border-gray-200 flex items-center justify-center z-10">
        <SourceTypeBadge type={signal.signal_type || 'note'} showLabel={false} />
      </div>

      {/* Content card */}
      <div className="flex-1 bg-gray-50 border border-gray-200 rounded-lg p-4">
        <div
          className="flex items-start justify-between gap-4 cursor-pointer"
          onClick={handleExpand}
        >
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-gray-900 truncate">
              {signal.source_name}
            </h4>
            {signal.last_used && (
              <p className="text-xs text-gray-500 mt-0.5">
                {formatDistanceToNow(new Date(signal.last_used), { addSuffix: true })}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <SourceTypeBadge type={signal.signal_type || 'note'} showLabel={true} />
            <button className="p-1 text-gray-400 hover:text-gray-600">
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
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
                {/* Quality assessment banner */}
                {getQualityBadge()}

                {/* Signal content */}
                {content ? (
                  <div className="bg-white rounded-lg border border-gray-100 p-4">
                    <div className="prose prose-sm max-w-none">
                      <Markdown content={content} />
                    </div>
                    {content.length > 500 && (
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

        {/* Impact summary */}
        {totalContributions > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
            <div className="flex-1 max-w-[100px]">
              <UsageBar count={signal.total_uses} size="sm" />
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500">
              {signal.uses_by_entity.feature > 0 && (
                <span>{signal.uses_by_entity.feature} features</span>
              )}
              {signal.uses_by_entity.persona > 0 && (
                <span>{signal.uses_by_entity.persona} personas</span>
              )}
              {signal.uses_by_entity.vp_step > 0 && (
                <span>{signal.uses_by_entity.vp_step} steps</span>
              )}
            </div>
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
