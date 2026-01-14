'use client'

import { Sparkles, Info } from 'lucide-react'

// Simple relative time formatter
function formatDistanceToNow(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'less than a minute'
  if (diffMins < 60) return `${diffMins} minute${diffMins === 1 ? '' : 's'}`
  if (diffHours < 24) return `${diffHours} hour${diffHours === 1 ? '' : 's'}`
  if (diffDays < 30) return `${diffDays} day${diffDays === 1 ? '' : 's'}`
  return date.toLocaleDateString()
}

interface EnrichmentContextProps {
  newSignalsCount?: number
  lastEnrichedAt?: string | null
  className?: string
}

export default function EnrichmentContext({
  newSignalsCount = 0,
  lastEnrichedAt,
  className = '',
}: EnrichmentContextProps) {
  // Don't show if no enrichment has occurred
  if (!lastEnrichedAt && newSignalsCount === 0) {
    return null
  }

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString)
      return formatDistanceToNow(date) + ' ago'
    } catch {
      return dateString
    }
  }

  // Build context message
  let contextMessage = ''
  if (newSignalsCount > 0 && lastEnrichedAt) {
    contextMessage = `Based on ${newSignalsCount} new signal${
      newSignalsCount !== 1 ? 's' : ''
    } since last enrichment ${formatDate(lastEnrichedAt)}`
  } else if (newSignalsCount > 0) {
    contextMessage = `Based on ${newSignalsCount} signal${newSignalsCount !== 1 ? 's' : ''}`
  } else if (lastEnrichedAt) {
    contextMessage = `Last enriched ${formatDate(lastEnrichedAt)}`
  }

  if (!contextMessage) {
    return null
  }

  return (
    <div
      className={`inline-flex items-center space-x-2 px-3 py-2 rounded-lg bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-100 ${className}`}
    >
      <Sparkles className="h-4 w-4 text-indigo-600 flex-shrink-0" />
      <span className="text-sm text-indigo-900">{contextMessage}</span>
    </div>
  )
}

// Alternative compact version for inline use
export function CompactEnrichmentContext({
  newSignalsCount = 0,
  className = '',
}: {
  newSignalsCount?: number
  className?: string
}) {
  if (newSignalsCount === 0) {
    return null
  }

  return (
    <span
      className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded-md text-xs bg-indigo-50 text-indigo-700 ${className}`}
    >
      <Sparkles className="h-3 w-3" />
      <span>
        {newSignalsCount} new signal{newSignalsCount !== 1 ? 's' : ''}
      </span>
    </span>
  )
}

// Info tooltip version for help text
export function EnrichmentContextTooltip() {
  return (
    <div className="inline-flex items-center space-x-1 text-xs text-gray-500">
      <Info className="h-3.5 w-3.5" />
      <span>Context shows new signals since last enrichment</span>
    </div>
  )
}
