/**
 * EvidenceChip Component
 *
 * Displays evidence references with rich metadata (source type, label, timestamp/page).
 * Shows excerpt and rationale on hover.
 *
 * Phase 0 - Foundation: Evidence chain of custody
 */

'use client'

import React, { useState } from 'react'

interface EvidenceChipProps {
  // Core evidence
  chunkId?: string
  signalId?: string
  excerpt: string
  rationale?: string

  // Display metadata (Phase 0)
  sourceType?: 'transcript' | 'email' | 'doc' | 'note' | 'research'
  sourceLabel?: string
  timestamp?: string  // For transcripts (e.g., "14:32")
  page?: number  // For documents

  // Optional
  confidence?: number
  onClick?: () => void
  className?: string
}

// Icon mapping for source types
const SOURCE_ICONS: Record<string, string> = {
  transcript: '📞',
  email: '📧',
  doc: '📄',
  note: '📝',
  research: '🔬',
}

// Color mapping for source types
const SOURCE_COLORS: Record<string, string> = {
  transcript: 'bg-blue-100 text-blue-800 border-blue-300',
  email: 'bg-purple-100 text-purple-800 border-purple-300',
  doc: 'bg-gray-100 text-gray-800 border-gray-300',
  note: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  research: 'bg-green-100 text-green-800 border-green-300',
}

export function EvidenceChip({
  chunkId,
  signalId,
  excerpt,
  rationale,
  sourceType = 'note',
  sourceLabel,
  timestamp,
  page,
  confidence,
  onClick,
  className = '',
}: EvidenceChipProps) {
  const [showTooltip, setShowTooltip] = useState(false)

  // Format display label
  const formatLabel = (): string => {
    if (sourceLabel) {
      if (sourceType === 'transcript' && timestamp) {
        return `${sourceLabel} @ ${timestamp}`
      }
      if (sourceType === 'doc' && page) {
        return `${sourceLabel} p${page}`
      }
      return sourceLabel
    }

    // Fallback labels
    if (sourceType === 'transcript' && timestamp) {
      return `Call @ ${timestamp}`
    }
    if (sourceType === 'doc' && page) {
      return `Document p${page}`
    }
    return sourceType.charAt(0).toUpperCase() + sourceType.slice(1)
  }

  const icon = SOURCE_ICONS[sourceType] || '📄'
  const colorClass = SOURCE_COLORS[sourceType] || SOURCE_COLORS.note
  const label = formatLabel()
  const isClickable = !!onClick

  return (
    <div className="relative inline-block">
      <button
        type="button"
        onClick={onClick}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        disabled={!isClickable}
        className={`
          inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium border
          ${colorClass}
          ${isClickable ? 'cursor-pointer hover:shadow-sm' : 'cursor-default'}
          transition-all duration-150
          ${className}
        `}
        title={excerpt}
      >
        <span>{icon}</span>
        <span>{label}</span>
        {confidence !== undefined && (
          <span className="ml-1 opacity-60">{Math.round(confidence * 100)}%</span>
        )}
      </button>

      {/* Tooltip with excerpt and rationale */}
      {showTooltip && (excerpt || rationale) && (
        <div
          className="absolute z-50 bottom-full left-0 mb-2 w-80 p-3 rounded-lg shadow-lg border border-gray-200 bg-white"
          onMouseEnter={() => setShowTooltip(true)}
          onMouseLeave={() => setShowTooltip(false)}
        >
          {/* Arrow */}
          <div className="absolute top-full left-4 -mt-1 w-2 h-2 bg-white border-r border-b border-gray-200 transform rotate-45" />

          {/* Content */}
          <div className="space-y-2">
            {excerpt && (
              <div>
                <div className="text-xs font-semibold text-gray-700 mb-1">Excerpt:</div>
                <div className="text-xs text-gray-600 italic leading-relaxed">
                  "{excerpt}"
                </div>
              </div>
            )}

            {rationale && (
              <div>
                <div className="text-xs font-semibold text-gray-700 mb-1">Why this matters:</div>
                <div className="text-xs text-gray-600 leading-relaxed">
                  {rationale}
                </div>
              </div>
            )}

            {/* Metadata footer */}
            <div className="pt-2 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
              <span>{sourceType.toUpperCase()}</span>
              {chunkId && (
                <span className="font-mono text-xs">ID: {chunkId.slice(0, 8)}</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * EvidenceGroup Component
 *
 * Groups multiple evidence chips together with a count badge
 */
interface EvidenceGroupProps {
  evidence: Array<{
    chunkId?: string
    signalId?: string
    excerpt: string
    rationale?: string
    sourceType?: 'transcript' | 'email' | 'doc' | 'note' | 'research'
    sourceLabel?: string
    timestamp?: string
    page?: number
    confidence?: number
  }>
  maxDisplay?: number
  onViewAll?: () => void
  className?: string
}

export function EvidenceGroup({
  evidence,
  maxDisplay = 3,
  onViewAll,
  className = '',
}: EvidenceGroupProps) {
  if (!evidence || evidence.length === 0) {
    return null
  }

  const displayEvidence = evidence.slice(0, maxDisplay)
  const remaining = Math.max(0, evidence.length - maxDisplay)

  return (
    <div className={`flex flex-wrap items-center gap-2 ${className}`}>
      {displayEvidence.map((ev, index) => (
        <EvidenceChip
          key={ev.chunkId || index}
          {...ev}
        />
      ))}

      {remaining > 0 && (
        <button
          type="button"
          onClick={onViewAll}
          className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-gray-100 text-gray-700 border border-gray-300 hover:bg-gray-200 transition-colors"
        >
          +{remaining} more
        </button>
      )}
    </div>
  )
}
