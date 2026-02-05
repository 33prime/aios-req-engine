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
        <div
          key={item.chunk_id || idx}
          className="pl-3 border-l-2 border-gray-200 text-[13px] text-gray-600"
        >
          <p className="italic leading-relaxed">&ldquo;{item.excerpt}&rdquo;</p>
          <div className="flex items-center gap-2 mt-1 text-[11px] text-gray-400">
            <span className="px-1.5 py-0.5 bg-gray-50 rounded text-gray-500">
              {SOURCE_LABELS[item.source_type] || item.source_type}
            </span>
            {item.rationale && <span>{item.rationale}</span>}
          </div>
        </div>
      ))}
      {remaining > 0 && (
        <p className="text-[11px] text-gray-400 pl-3">
          +{remaining} more source{remaining > 1 ? 's' : ''}
        </p>
      )}
    </div>
  )
}
