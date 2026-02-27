'use client'

import { useState, useEffect } from 'react'
import { FileText, Mic, Mail, File, BookOpen, StickyNote, Loader2 } from 'lucide-react'
import { getClientSignals } from '@/lib/api'
import type { ClientSignalSummary, ClientDetailProject } from '@/types/workspace'

interface ClientSourcesTabProps {
  clientId: string
  projects: ClientDetailProject[]
}

const SIGNAL_TYPES = ['all', 'transcript', 'email', 'document', 'research', 'note'] as const

const TYPE_ICONS: Record<string, React.ReactNode> = {
  transcript: <Mic className="w-3.5 h-3.5" />,
  email: <Mail className="w-3.5 h-3.5" />,
  document: <File className="w-3.5 h-3.5" />,
  research: <BookOpen className="w-3.5 h-3.5" />,
  note: <StickyNote className="w-3.5 h-3.5" />,
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export function ClientSourcesTab({ clientId, projects }: ClientSourcesTabProps) {
  const [signals, setSignals] = useState<ClientSignalSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  const projectNameMap = Object.fromEntries(projects.map((p) => [p.id, p.name]))

  useEffect(() => {
    loadSignals(true)
  }, [clientId, typeFilter])

  const loadSignals = async (reset: boolean) => {
    if (reset) setLoading(true)
    else setLoadingMore(true)
    try {
      const params: { signal_type?: string; limit?: number; offset?: number } = {
        limit: 50,
        offset: reset ? 0 : signals.length,
      }
      if (typeFilter !== 'all') params.signal_type = typeFilter
      const result = await getClientSignals(clientId, params)
      if (reset) {
        setSignals(result.signals)
      } else {
        setSignals((prev) => [...prev, ...result.signals])
      }
      setTotal(result.total)
    } catch (err) {
      console.error('Failed to load signals:', err)
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  // Count by type for the current loaded set
  const typeCounts = signals.reduce<Record<string, number>>((acc, s) => {
    acc[s.signal_type] = (acc[s.signal_type] || 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-6">
      {/* Filter pills */}
      <div className="flex flex-wrap items-center gap-2">
        {SIGNAL_TYPES.map((type) => {
          const isActive = typeFilter === type
          const count = type === 'all' ? total : (typeCounts[type] || 0)
          return (
            <button
              key={type}
              onClick={() => setTypeFilter(type)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
                isActive
                  ? 'bg-brand-primary-light text-brand-primary'
                  : 'text-[#999] hover:text-[#666] hover:bg-[#F0F0F0]'
              }`}
            >
              {type === 'all' ? 'All' : type.charAt(0).toUpperCase() + type.slice(1)}
              {count > 0 && (
                <span className={`text-[10px] ${isActive ? 'text-brand-primary' : 'text-[#999]'}`}>{count}</span>
              )}
            </button>
          )
        })}
      </div>

      {/* Source stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: 'Total Signals', count: total, icon: <FileText className="w-3.5 h-3.5" /> },
          { label: 'Transcripts', count: typeCounts['transcript'] || 0, icon: <Mic className="w-3.5 h-3.5" /> },
          { label: 'Emails', count: typeCounts['email'] || 0, icon: <Mail className="w-3.5 h-3.5" /> },
          { label: 'Documents', count: typeCounts['document'] || 0, icon: <File className="w-3.5 h-3.5" /> },
        ].map((stat) => (
          <div key={stat.label} className="bg-white rounded-2xl border border-border shadow-md p-4 flex items-center gap-3">
            <div className="w-7 h-7 rounded-full bg-[#E8F5E9] flex items-center justify-center text-[#25785A] flex-shrink-0">
              {stat.icon}
            </div>
            <div>
              <p className="text-[16px] font-bold text-[#333]">{stat.count}</p>
              <p className="text-[11px] text-[#999]">{stat.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Signal list */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-5 h-5 text-brand-primary animate-spin" />
        </div>
      ) : signals.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-2xl border border-border shadow-md">
          <FileText className="w-8 h-8 text-[#CCC] mx-auto mb-2" />
          <p className="text-[13px] text-[#666] mb-1">No signals yet</p>
          <p className="text-[12px] text-[#999]">
            Sources appear as you ingest meeting transcripts, emails, and documents
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {signals.map((signal) => {
            const isExpanded = expandedId === signal.id
            return (
              <div
                key={signal.id}
                className="bg-white rounded-xl border border-border p-4 border-l-4 border-l-border hover:border-l-brand-primary transition-colors cursor-pointer"
                onClick={() => setExpandedId(isExpanded ? null : signal.id)}
              >
                <div className="flex items-start gap-3">
                  {/* Type badge */}
                  <div className="flex items-center gap-1.5 px-2 py-1 bg-[#F0F0F0] rounded-lg text-[#666] flex-shrink-0">
                    {TYPE_ICONS[signal.signal_type] || <FileText className="w-3.5 h-3.5" />}
                    <span className="text-[11px] font-medium">{signal.signal_type}</span>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-medium text-[#333]">{signal.source || 'Untitled signal'}</p>
                    {signal.raw_text && (
                      <p className={`text-[12px] text-[#666] mt-0.5 ${isExpanded ? '' : 'line-clamp-2'}`}>
                        {isExpanded ? signal.raw_text : signal.raw_text.slice(0, 150)}
                        {!isExpanded && signal.raw_text.length > 150 && '...'}
                      </p>
                    )}
                  </div>

                  {/* Meta */}
                  <div className="flex flex-col items-end gap-1 flex-shrink-0">
                    <span className="px-2 py-0.5 text-[10px] font-medium text-[#666] bg-[#F0F0F0] rounded-md">
                      {projectNameMap[signal.project_id] || 'Unknown'}
                    </span>
                    <span className="text-[11px] text-[#999]">{formatTimeAgo(signal.created_at)}</span>
                  </div>
                </div>
              </div>
            )
          })}

          {/* Load more */}
          {signals.length < total && (
            <button
              onClick={() => loadSignals(false)}
              disabled={loadingMore}
              className="w-full py-3 text-[13px] font-medium text-brand-primary bg-white rounded-xl border border-border hover:bg-[#E8F5E9] transition-colors disabled:opacity-50"
            >
              {loadingMore ? 'Loading...' : `Load more (${signals.length} of ${total})`}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
