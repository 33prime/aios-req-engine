'use client'

import { useRef, useCallback } from 'react'
import type { TranscriptSegment } from '@/types/call-intelligence'
import { formatDuration } from './constants'

export function SyncedTranscript({
  segments,
  timeline,
  activeTimestamp,
  onSegmentClick,
}: {
  segments: TranscriptSegment[]
  timeline?: Array<Record<string, unknown>>
  activeTimestamp?: number | null
  onSegmentClick?: (seconds: number) => void
}) {
  const scrollRef = useRef<HTMLDivElement>(null)

  const getSegmentEngagement = useCallback((seg: TranscriptSegment) => {
    if (!timeline || timeline.length === 0) return 0.5
    const ts = seg.start
    for (let i = timeline.length - 1; i >= 0; i--) {
      if (Number(timeline[i]?.timestamp_seconds || 0) <= ts) {
        return Number(timeline[i]?.engagement_level || 0.5)
      }
    }
    return 0.5
  }, [timeline])

  if (segments.length === 0) return null

  return (
    <div className="border border-border rounded-lg overflow-hidden">
      <div className="px-4 py-3 bg-surface-muted border-b border-border">
        <span className="text-sm font-semibold text-text-body">
          Transcript <span className="text-text-muted font-normal">({segments.length} segments)</span>
        </span>
      </div>
      <div ref={scrollRef} className="max-h-80 overflow-y-auto p-4 space-y-2">
        {segments.map((seg, i) => {
          const engagement = getSegmentEngagement(seg)
          const engColor = engagement < 0.4 ? 'border-l-red-400' : engagement < 0.7 ? 'border-l-amber-400' : 'border-l-green-400'
          const isActive = activeTimestamp != null && seg.start <= activeTimestamp && seg.end >= activeTimestamp

          return (
            <div
              key={i}
              className={`flex gap-3 text-sm border-l-3 pl-3 cursor-pointer hover:bg-surface-muted rounded-r-lg transition-colors ${engColor} ${isActive ? 'bg-brand-primary-light' : ''}`}
              onClick={() => onSegmentClick?.(seg.start)}
            >
              <span className="shrink-0 text-xs text-text-muted font-mono w-12 pt-0.5 text-right">
                {formatDuration(Math.round(seg.start))}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-xs font-semibold text-brand-accent">{seg.speaker}</span>
                <p className="text-text-body">{seg.text}</p>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
