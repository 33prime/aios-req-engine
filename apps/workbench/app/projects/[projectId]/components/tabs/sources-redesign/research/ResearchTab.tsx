/**
 * ResearchTab Component
 *
 * Displays research signals with markdown content and copy functionality.
 */

'use client'

import { useState, useMemo } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { ClipboardCopy, Check, Globe } from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'
import type { SourceUsageItem } from '@/lib/api'

interface ResearchTabProps {
  signals: SourceUsageItem[]
  isLoading: boolean
}

export function ResearchTab({ signals, isLoading }: ResearchTabProps) {
  // Filter to only research signals
  const researchItems = useMemo(() => {
    return signals.filter(s => s.signal_type === 'research')
  }, [signals])

  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2].map(i => (
          <div key={i} className="bg-gray-50 border border-gray-200 rounded-xl p-6 animate-pulse">
            <div className="h-5 bg-gray-200 rounded w-1/3 mb-4" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-100 rounded w-full" />
              <div className="h-3 bg-gray-100 rounded w-5/6" />
              <div className="h-3 bg-gray-100 rounded w-4/6" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (researchItems.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <Globe className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No research yet</h3>
        <p className="text-sm text-gray-500 max-w-sm">
          Research from web searches, competitor analysis, and market research will appear here.
          Use the /run-research command in chat to gather external context.
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {researchItems.map(item => (
        <ResearchCard key={item.source_id} research={item} />
      ))}
    </div>
  )
}

function ResearchCard({ research }: { research: SourceUsageItem }) {
  const [copied, setCopied] = useState(false)
  const [expanded, setExpanded] = useState(false)

  // Use content field for research signals, fallback to source_name
  const researchContent = research.content || research.source_name

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(researchContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-violet-50 rounded-lg flex items-center justify-center">
            <Globe className="w-4 h-4 text-violet-600" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-gray-900 line-clamp-1">
              {research.source_name}
            </h3>
            {research.last_used && (
              <p className="text-xs text-gray-500">
                {formatDistanceToNow(new Date(research.last_used), { addSuffix: true })}
              </p>
            )}
          </div>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 hover:text-gray-900 bg-white border border-gray-200 rounded-md hover:border-gray-300 transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-4 h-4 text-green-500" />
              Copied
            </>
          ) : (
            <>
              <ClipboardCopy className="w-4 h-4" />
              Copy
            </>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        <div className={`prose prose-sm max-w-none ${!expanded ? 'line-clamp-6' : ''}`}>
          <Markdown content={researchContent} />
        </div>

        {/* Show expand button if content is long */}
        {researchContent.length > 500 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="mt-3 text-sm font-medium text-brand-primary hover:text-brand-primaryHover"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>

      {/* Usage footer */}
      {research.total_uses > 0 && (
        <div className="px-4 py-3 border-t border-gray-100 bg-gray-25 flex items-center gap-4 text-xs text-gray-500">
          <span className="font-medium">Used {research.total_uses}x</span>
          {research.uses_by_entity.feature > 0 && (
            <span>→ {research.uses_by_entity.feature} features</span>
          )}
          {research.uses_by_entity.persona > 0 && (
            <span>→ {research.uses_by_entity.persona} personas</span>
          )}
        </div>
      )}
    </div>
  )
}
