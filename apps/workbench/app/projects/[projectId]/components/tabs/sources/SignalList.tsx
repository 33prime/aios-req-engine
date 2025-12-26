/**
 * SignalList Component
 *
 * Left column of Sources tab - shows list of signals with metadata
 */

'use client'

import React from 'react'
import { Mail, FileText, Mic, Upload, Database } from 'lucide-react'
import type { SignalWithCounts } from '@/types/api'

interface SignalListProps {
  signals: SignalWithCounts[]
  selectedId: string | null
  onSelect: (signal: SignalWithCounts) => void
}

const getSignalIcon = (signalType: string) => {
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
    default:
      return Database
  }
}

const getSignalTypeLabel = (signalType: string) => {
  const labels: Record<string, string> = {
    email: 'Email',
    transcript: 'Transcript',
    note: 'Note',
    file_text: 'Document',
    file: 'File',
  }
  return labels[signalType] || signalType
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
  return (
    <div className="space-y-2">
      <div className="mb-4">
        <h3 className="text-sm font-medium text-ui-bodyText mb-1">
          Signals ({signals.length})
        </h3>
        <p className="text-xs text-ui-supportText">
          All signals ingested for this project
        </p>
      </div>

      <div className="space-y-2">
        {signals.map((signal) => {
          const Icon = getSignalIcon(signal.signal_type)
          const isActive = selectedId === signal.id

          return (
            <button
              key={signal.id}
              onClick={() => onSelect(signal)}
              className={`
                w-full text-left p-4 rounded-lg border transition-all
                ${
                  isActive
                    ? 'bg-brand-primary/5 border-brand-primary'
                    : 'bg-white border-ui-cardBorder hover:border-brand-primary/50'
                }
              `}
            >
              <div className="flex items-start gap-3">
                <div className={`
                  flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center
                  ${isActive ? 'bg-brand-primary text-white' : 'bg-ui-background text-ui-supportText'}
                `}>
                  <Icon className="w-4 h-4" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-sm font-medium truncate ${isActive ? 'text-brand-primary' : 'text-ui-bodyText'}`}>
                      {signal.source_label || signal.source}
                    </span>
                    <span className="flex-shrink-0 px-2 py-0.5 text-xs rounded-full bg-ui-buttonGray text-ui-supportText">
                      {getSignalTypeLabel(signal.signal_type)}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 text-xs text-ui-supportText">
                    <span>{formatTimestamp(signal.created_at)}</span>
                    <span>{signal.chunk_count} chunks</span>
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
        })}
      </div>
    </div>
  )
}
