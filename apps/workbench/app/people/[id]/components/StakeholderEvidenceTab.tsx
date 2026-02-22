'use client'

import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { getStakeholderEvidence } from '@/lib/api'
import { formatDateShort } from '@/lib/date-utils'
import type { StakeholderEvidenceData, SignalReference, FieldAttribution } from '@/types/workspace'

interface StakeholderEvidenceTabProps {
  projectId: string
  stakeholderId: string
}

const SIGNAL_TYPE_STYLE: Record<string, { bg: string; text: string; label: string }> = {
  transcript: { bg: 'bg-[#3FAF7A]/10', text: 'text-[#3FAF7A]', label: 'Transcript' },
  email: { bg: 'bg-[#0A1E2F]/10', text: 'text-[#0A1E2F]', label: 'Email' },
  document: { bg: 'bg-[#3FAF7A]/10', text: 'text-[#25785A]', label: 'Document' },
  research: { bg: 'bg-[#3FAF7A]/10', text: 'text-[#25785A]', label: 'Research' },
}

export function StakeholderEvidenceTab({ projectId, stakeholderId }: StakeholderEvidenceTabProps) {
  const [data, setData] = useState<StakeholderEvidenceData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    getStakeholderEvidence(projectId, stakeholderId)
      .then((res) => {
        setData(res)
        setError(null)
      })
      .catch((err) => {
        console.error('Failed to load evidence:', err)
        setError('Failed to load evidence data')
      })
      .finally(() => setLoading(false))
  }, [projectId, stakeholderId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="w-6 h-6 text-[#3FAF7A] animate-spin" />
        <span className="ml-2 text-[13px] text-[#999]">Loading evidence...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="text-center py-16">
        <p className="text-[13px] text-[#999]">{error || 'No evidence data available'}</p>
      </div>
    )
  }

  const topicEntries = Object.entries(data.topic_mentions || {})
    .sort(([, a], [, b]) => b - a)
    .slice(0, 8)
  const maxTopicCount = topicEntries.length > 0 ? topicEntries[0][1] : 1

  const isEmpty = data.source_signals.length === 0
    && data.field_attributions.length === 0
    && data.evidence_items.length === 0
    && topicEntries.length === 0

  if (isEmpty) {
    return (
      <div className="text-center py-16">
        <p className="text-[14px] text-[#666]">No evidence data available yet.</p>
        <p className="text-[13px] text-[#999] mt-1">Evidence is collected when signals mention this stakeholder.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Source Signals */}
      {data.source_signals.length > 0 && (
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <div className="flex items-center justify-between mb-5">
            <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em]">Source Signals</h3>
            <span className="text-[12px] text-[#999]">Mentioned in {data.source_signals.length} signal{data.source_signals.length !== 1 ? 's' : ''}</span>
          </div>
          <div className="space-y-3">
            {data.source_signals.map((sig) => {
              const style = SIGNAL_TYPE_STYLE[sig.signal_type || ''] || SIGNAL_TYPE_STYLE.document
              return (
                <div
                  key={sig.id}
                  className="p-4 rounded-xl bg-white border border-[#E5E5E5] cursor-pointer hover:bg-[#FAFAFA] transition-colors"
                  style={{ borderLeft: '3px solid transparent' }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.borderLeftColor = '#3FAF7A' }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.borderLeftColor = 'transparent' }}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${style.bg} ${style.text}`}>
                        {style.label}
                      </span>
                      <span className="text-[13px] font-semibold text-[#333]">{sig.title || sig.source_label || 'Unknown Signal'}</span>
                    </div>
                    <span className="text-[11px] text-[#999] whitespace-nowrap ml-4">{formatDateShort(sig.created_at)}</span>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Topic Frequency */}
      {topicEntries.length > 0 && (
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-2">Topic Frequency</h3>
          <p className="text-[13px] text-[#999] mb-5">What this stakeholder discusses most across all signals</p>
          <div className="space-y-3">
            {topicEntries.map(([topic, count]) => {
              const pct = Math.max(15, (count / maxTopicCount) * 100)
              return (
                <div key={topic} className="flex items-center gap-4">
                  <span className="text-[13px] text-[#666] w-28 text-right flex-shrink-0 font-medium capitalize">{topic}</span>
                  <div className="flex-1 h-7 bg-[#F4F4F4] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#3FAF7A] rounded-full flex items-center justify-end pr-3 transition-all duration-600"
                      style={{ width: `${pct}%` }}
                    >
                      <span className={`text-[11px] font-semibold ${pct > 30 ? 'text-white' : 'text-[#25785A]'}`}>{count}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Field Attributions */}
      {data.field_attributions.length > 0 && (
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-2">Field Attributions</h3>
          <p className="text-[13px] text-[#999] mb-5">Where each piece of information was learned</p>
          <div className="divide-y divide-[#E5E5E5]">
            {data.field_attributions.map((fa, i) => (
              <div key={i} className="flex items-center gap-4 py-3">
                <span className="text-[13px] font-medium text-[#333] w-36 flex-shrink-0">
                  {fa.field_path.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
                <span className="text-[13px] text-[#666] flex-1">{fa.signal_label || fa.signal_source || '—'}</span>
                {fa.signal_label ? (
                  <span className="text-[12px] text-[#3FAF7A] whitespace-nowrap">{fa.signal_label}</span>
                ) : (
                  <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-[#3FAF7A]/10 text-[#25785A] font-medium">AI inferred</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Evidence Citations */}
      {data.evidence_items.length > 0 && (
        <div className="bg-white border border-[#E5E5E5] rounded-2xl shadow-sm p-6">
          <h3 className="text-[12px] font-semibold text-[#999] uppercase tracking-[0.05em] mb-5">Evidence Citations</h3>
          <div className="space-y-3">
            {data.evidence_items.map((ev, i) => {
              const excerpt = (ev.excerpt as string) || (ev.rationale as string) || JSON.stringify(ev)
              const sourceType = (ev.source_type as string) || 'signal'
              const isInferred = sourceType === 'inferred'
              return (
                <div
                  key={i}
                  className="p-4 bg-[#F4F4F4] rounded-xl"
                  style={{ borderLeft: `3px solid ${isInferred ? '#0A1E2F' : '#3FAF7A'}` }}
                >
                  <p className="text-[13px] text-[#666] leading-relaxed italic mb-2.5">&ldquo;{excerpt}&rdquo;</p>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${isInferred ? 'bg-[#3FAF7A]/10 text-[#25785A]' : 'bg-[#3FAF7A]/10 text-[#3FAF7A]'}`}>
                      {isInferred ? 'Inferred' : 'Signal'}
                    </span>
                    {ev.source_label ? (
                      <span className="text-[12px] text-[#999]">{String(ev.source_label)}</span>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
