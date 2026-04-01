'use client'

import { FileText } from 'lucide-react'
import type { BRDEvidence } from '@/types/workspace'

interface EvidenceBlockProps {
  evidence: BRDEvidence[]
  maxItems?: number
}

const SOURCE_LABELS: Record<string, string> = {
  signal: 'Signal',
  research: 'Research',
  inferred: 'Inferred',
}

/**
 * Single evidence quote with green left border, italic excerpt, and source attribution.
 */
export function EvidenceQuote({ item }: { item: BRDEvidence }) {
  const hasExcerpt = item.excerpt && item.excerpt.trim().length > 0

  return (
    <div
      className="rounded-md bg-[#F7FAFC] px-3 py-2.5"
      style={{ borderLeft: '3px solid #3FAF7A' }}
    >
      {hasExcerpt ? (
        <>
          <p className="text-[13px] italic text-[#4A5568] leading-relaxed">
            &ldquo;{item.excerpt}&rdquo;
          </p>
          {item.rationale && (
            <p className="text-[11px] text-[#718096] mt-1">
              &mdash; {item.rationale}
            </p>
          )}
        </>
      ) : (
        <p className="text-[13px] text-[#4A5568] leading-relaxed">
          {item.rationale || 'Source evidence'}
        </p>
      )}
    </div>
  )
}

export function EvidenceBlock({ evidence, maxItems = 3 }: EvidenceBlockProps) {
  if (!evidence || evidence.length === 0) return null

  const displayed = evidence.slice(0, maxItems)
  const remaining = evidence.length - maxItems

  return (
    <div className="mt-3 space-y-2">
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-gray-500 uppercase tracking-wide">
        <FileText className="w-3 h-3" />
        Evidence ({evidence.length})
      </div>
      {displayed.map((item, idx) => (
        <EvidenceQuote key={item.chunk_id || idx} item={item} />
      ))}
      {remaining > 0 && (
        <p className="text-[11px] text-gray-400 pl-3">
          +{remaining} more source{remaining > 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
