/**
 * SignalList Component
 *
 * Left column of Sources tab - shows list of signals with metadata
 */

'use client'

import React, { useMemo } from 'react'
import { Mail, FileText, Mic, Upload, Database, UserCheck, Search } from 'lucide-react'
import type { SignalWithCounts } from '@/types/api'

interface SignalListProps {
  signals: SignalWithCounts[]
  selectedId: string | null
  onSelect: (signal: SignalWithCounts) => void
}

const getSignalIcon = (signalType: string, sourceType?: string) => {
  // Check source_type first for portal responses
  if (sourceType === 'portal_response' || signalType === 'portal_response') {
    return UserCheck
  }
  switch (signalType) {
    case 'email':
      return Mail
    case 'transcript':
      return Mic
    case 'note':
      return FileText
    case 'file_text':
    case 'file':
      return Upload
    case 'research':
      return Search
    default:
      return Database
  }
}

const getSignalTypeLabel = (signalType: string, sourceType?: string) => {
  // Check source_type first for portal responses
  if (sourceType === 'portal_response' || signalType === 'portal_response') {
    return 'Portal Response'
  }
  const labels: Record<string, string> = {
    email: 'Email',
    transcript: 'Transcript',
    note: 'Note',
    file_text: 'Document',
    file: 'File',
    research: 'Research',
  }
  return labels[signalType] || signalType
}

const isPortalResponse = (signal: SignalWithCounts) => {
  return signal.source_type === 'portal_response' || signal.signal_type === 'portal_response'
}

const formatTimestamp = (timestamp: string) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return 'Just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`

  return date.toLocaleDateString()
}

export function SignalList({ signals, selectedId, onSelect }: SignalListProps) {
  // Group signals: portal responses at top, others below
  const { portalResponses, otherSignals } = useMemo(() => {
    const portal: SignalWithCounts[] = []
    const other: SignalWithCounts[] = []

    signals.forEach(signal => {
      if (isPortalResponse(signal)) {
        portal.push(signal)
      } else {
        other.push(signal)
      }
    })

    return { portalResponses: portal, otherSignals: other }
  }, [signals])

  const renderSignalItem = (signal: SignalWithCounts, isPortal = false) => {
    const Icon = getSignalIcon(signal.signal_type, signal.source_type)
    const isActive = selectedId === signal.id

    return (
      <button
        key={signal.id}
        onClick={() => onSelect(signal)}
        className={`
          w-full text-left p-4 rounded-lg border transition-all
          ${
            isActive
              ? isPortal
                ? 'bg-green-50 border-green-500'
                : 'bg-brand-primary/5 border-brand-primary'
              : isPortal
                ? 'bg-white border-green-200 hover:border-green-400'
                : 'bg-white border-ui-cardBorder hover:border-brand-primary/50'
          }
        `}
      >
        <div className="flex items-start gap-3">
          <div className={`
            flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
            ${isActive
              ? isPortal
                ? 'bg-green-600 text-white'
                : 'bg-brand-primary text-white'
              : isPortal
                ? 'bg-green-100 text-green-600'
                : 'bg-ui-background text-ui-supportText'
            }
          `}>
            <Icon className="w-4 h-4" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-sm font-medium truncate ${
                isActive
                  ? isPortal ? 'text-green-700' : 'text-brand-primary'
                  : 'text-ui-bodyText'
              }`}>
                {signal.source_label || signal.source}
              </span>
              <span className={`flex-shrink-0 px-2 py-0.5 text-xs rounded-full ${
                isPortal
                  ? 'bg-green-100 text-green-700'
                  : 'bg-ui-buttonGray text-ui-supportText'
              }`}>
                {getSignalTypeLabel(signal.signal_type, signal.source_type)}
              </span>
            </div>

            <div className="flex items-center gap-3 text-xs text-ui-supportText">
              <span>{formatTimestamp(signal.created_at)}</span>
              {signal.chunk_count > 0 && <span>{signal.chunk_count} chunks</span>}
              <span
                className={`font-medium ${signal.impact_count > 0 ? 'text-brand-primary' : 'text-ui-supportText'}`}
              >
                {signal.impact_count} impacts
              </span>
            </div>
          </div>
        </div>
      </button>
    )
  }

  return (
    <div className="space-y-4">
      <div className="mb-4">
        <h3 className="text-sm font-medium text-ui-bodyText mb-1">
          Signals ({signals.length})
        </h3>
        <p className="text-xs text-ui-supportText">
          All signals ingested for this project
        </p>
      </div>

      {/* Portal Responses Section */}
      {portalResponses.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-1">
            <UserCheck className="w-4 h-4 text-green-600" />
            <h4 className="text-xs font-medium text-green-700 uppercase tracking-wide">
              Client Portal Responses ({portalResponses.length})
            </h4>
          </div>
          <div className="space-y-2">
            {portalResponses.map(signal => renderSignalItem(signal, true))}
          </div>
        </div>
      )}

      {/* Other Signals Section */}
      {otherSignals.length > 0 && (
        <div className="space-y-2">
          {portalResponses.length > 0 && (
            <div className="px-1 pt-2">
              <h4 className="text-xs font-medium text-ui-supportText uppercase tracking-wide">
                Other Signals ({otherSignals.length})
              </h4>
            </div>
          )}
          <div className="space-y-2">
            {otherSignals.map(signal => renderSignalItem(signal, false))}
          </div>
        </div>
      )}
    </div>
  )
}
