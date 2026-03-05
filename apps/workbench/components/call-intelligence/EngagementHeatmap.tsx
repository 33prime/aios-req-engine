'use client'

import { formatDuration } from './constants'

export function EngagementHeatmap({
  timeline,
  durationSeconds,
  onSeek,
}: {
  timeline: Array<Record<string, unknown>>
  durationSeconds?: number | null
  onSeek?: (seconds: number) => void
}) {
  if (!timeline || timeline.length === 0) return null
  const duration = durationSeconds || (timeline.length > 0 ? Number(timeline[timeline.length - 1]?.timestamp_seconds || 300) + 60 : 300)

  return (
    <div className="space-y-1">
      <span className="text-xs font-medium text-text-muted">Engagement Timeline</span>
      <div className="h-6 bg-[#F0F0F0] rounded-full overflow-hidden flex cursor-pointer" title="Click to navigate">
        {timeline.map((entry, i) => {
          const ts = Number(entry.timestamp_seconds || 0)
          const nextTs = i < timeline.length - 1 ? Number(timeline[i + 1]?.timestamp_seconds || duration) : duration
          const widthPct = ((nextTs - ts) / duration) * 100
          const engagement = Number(entry.engagement_level || 0.5)
          // BRD: low = navy, mid = teal, high = green
          const bg = engagement < 0.4 ? 'bg-[#044159]' : engagement < 0.7 ? 'bg-[#88BABF]' : 'bg-[#3FAF7A]'

          return (
            <div
              key={i}
              className={`${bg} h-full relative group transition-opacity hover:opacity-80`}
              style={{ width: `${widthPct}%` }}
              onClick={() => onSeek?.(ts)}
              title={`${formatDuration(ts)} - ${String(entry.topic || 'Segment')} (${Math.round(engagement * 100)}%)`}
            />
          )
        })}
      </div>
    </div>
  )
}
