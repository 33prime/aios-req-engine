'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronUp, Send, SkipForward, ArrowUpCircle } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import { listInfoRequests, answerInfoRequest, updateInfoRequestStatus } from '@/lib/api/portal'
import { usePortal } from '../PortalShell'
import type { InfoRequest, InfoRequestStatus, InfoRequestWithDelta } from '@/types/portal'

type FilterTab = 'all' | 'pending' | 'answered' | 'skipped'

const PRIORITY_STYLES: Record<string, string> = {
  high: 'bg-red-50 text-red-700',
  medium: 'bg-amber-50 text-amber-700',
  low: 'bg-blue-50 text-blue-700',
}

const STATUS_DOT: Record<string, string> = {
  not_started: 'bg-gray-300',
  in_progress: 'bg-amber-400',
  complete: 'bg-green-500',
  skipped: 'bg-gray-400',
}

export default function QuestionsPage() {
  const { projectId, refreshDashboard } = usePortal()
  const [requests, setRequests] = useState<InfoRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<FilterTab>('all')
  const [expandedGuidance, setExpandedGuidance] = useState<Set<string>>(new Set())
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [submittingIds, setSubmittingIds] = useState<Set<string>>(new Set())
  const [deltas, setDeltas] = useState<Record<string, InfoRequestWithDelta['readiness_delta']>>({})

  useEffect(() => {
    setLoading(true)
    listInfoRequests(projectId)
      .then(data => {
        setRequests(data.sort((a, b) => a.display_order - b.display_order))
      })
      .catch(err => setError(err.message || 'Failed to load questions'))
      .finally(() => setLoading(false))
  }, [projectId])

  const filtered = useMemo(() => {
    switch (filter) {
      case 'pending':
        return requests.filter(r => r.status === 'not_started' || r.status === 'in_progress')
      case 'answered':
        return requests.filter(r => r.status === 'complete')
      case 'skipped':
        return requests.filter(r => r.status === 'skipped')
      default:
        return requests
    }
  }, [requests, filter])

  const answeredCount = requests.filter(r => r.status === 'complete').length
  const totalCount = requests.length
  const progressPct = totalCount > 0 ? Math.round((answeredCount / totalCount) * 100) : 0

  const toggleGuidance = useCallback((id: string) => {
    setExpandedGuidance(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }, [])

  const handleSubmit = useCallback(async (request: InfoRequest) => {
    const text = answers[request.id]?.trim()
    if (!text) return

    setSubmittingIds(prev => new Set(prev).add(request.id))
    try {
      const result = await answerInfoRequest(request.id, { text }, 'complete')
      // Update local state
      setRequests(prev => prev.map(r => r.id === request.id ? { ...r, status: 'complete' as InfoRequestStatus, answer_data: { text } } : r))
      if (result.readiness_delta) {
        setDeltas(prev => ({ ...prev, [request.id]: result.readiness_delta }))
      }
      await refreshDashboard()
    } catch (err) {
      console.error('Failed to submit answer:', err)
    } finally {
      setSubmittingIds(prev => {
        const next = new Set(prev)
        next.delete(request.id)
        return next
      })
    }
  }, [answers, refreshDashboard])

  const handleSkip = useCallback(async (requestId: string) => {
    setSubmittingIds(prev => new Set(prev).add(requestId))
    try {
      await updateInfoRequestStatus(requestId, 'skipped')
      setRequests(prev => prev.map(r => r.id === requestId ? { ...r, status: 'skipped' as InfoRequestStatus } : r))
      await refreshDashboard()
    } catch (err) {
      console.error('Failed to skip:', err)
    } finally {
      setSubmittingIds(prev => {
        const next = new Set(prev)
        next.delete(requestId)
        return next
      })
    }
  }, [refreshDashboard])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" label="Loading questions..." />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-red-600 mb-2">{error}</p>
          <button onClick={() => window.location.reload()} className="text-sm text-brand-primary hover:underline">
            Retry
          </button>
        </div>
      </div>
    )
  }

  const filterTabs: { key: FilterTab; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: requests.length },
    { key: 'pending', label: 'Pending', count: requests.filter(r => r.status === 'not_started' || r.status === 'in_progress').length },
    { key: 'answered', label: 'Answered', count: requests.filter(r => r.status === 'complete').length },
    { key: 'skipped', label: 'Skipped', count: requests.filter(r => r.status === 'skipped').length },
  ]

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header + progress */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Questions</h1>
        <p className="text-text-muted mt-1">
          Help us understand your needs by answering these questions.
        </p>
        {totalCount > 0 && (
          <div className="mt-4">
            <div className="flex items-center justify-between text-sm mb-1.5">
              <span className="text-text-secondary">{answeredCount} of {totalCount} answered</span>
              <span className="font-medium text-brand-primary">{progressPct}%</span>
            </div>
            <div className="w-full h-2 bg-surface-subtle rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-primary rounded-full transition-all duration-500"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1">
        {filterTabs.map(tab => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              filter === tab.key
                ? 'bg-brand-primary text-white font-medium'
                : 'bg-surface-subtle text-text-secondary hover:bg-surface-card'
            }`}
          >
            {tab.label}
            <span className="ml-1.5 text-xs opacity-70">{tab.count}</span>
          </button>
        ))}
      </div>

      {/* Question cards */}
      {filtered.length === 0 ? (
        <div className="text-center py-12 text-text-muted">
          {filter === 'all' ? 'No questions yet.' : `No ${filter} questions.`}
        </div>
      ) : (
        <div className="space-y-4">
          {filtered.map(request => {
            const isSubmitting = submittingIds.has(request.id)
            const isAnswered = request.status === 'complete'
            const isSkipped = request.status === 'skipped'
            const isDone = isAnswered || isSkipped
            const hasGuidance = request.why_asking || request.example_answer || request.pro_tip
            const guidanceOpen = expandedGuidance.has(request.id)
            const delta = deltas[request.id]
            const existingAnswer = request.answer_data && typeof request.answer_data === 'object'
              ? (request.answer_data as Record<string, unknown>).text as string | undefined
              : undefined

            return (
              <div
                key={request.id}
                className={`rounded-lg border bg-surface-card shadow-sm transition-all ${
                  isDone ? 'opacity-75 border-border' : 'border-border'
                }`}
              >
                {/* Title row */}
                <div className="px-5 py-4 flex items-start gap-3">
                  <span className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOT[request.status]}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="text-sm font-semibold text-text-primary">{request.title}</h3>
                      {request.priority && request.priority !== 'none' && (
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${PRIORITY_STYLES[request.priority] || ''}`}>
                          {request.priority}
                        </span>
                      )}
                    </div>
                    {request.description && (
                      <p className="text-sm text-text-secondary mt-1 leading-relaxed">{request.description}</p>
                    )}
                  </div>
                </div>

                {/* Guidance toggle */}
                {hasGuidance && (
                  <div className="border-t border-border/50">
                    <button
                      onClick={() => toggleGuidance(request.id)}
                      className="w-full px-5 py-2.5 flex items-center justify-between text-xs text-text-muted hover:text-text-secondary transition-colors"
                    >
                      <span>Guidance</span>
                      {guidanceOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>
                    {guidanceOpen && (
                      <div className="px-5 pb-3 space-y-2">
                        {request.why_asking && (
                          <div>
                            <span className="text-[10px] font-medium text-text-muted uppercase tracking-wide">Why we're asking</span>
                            <p className="text-xs text-text-secondary mt-0.5">{request.why_asking}</p>
                          </div>
                        )}
                        {request.example_answer && (
                          <div>
                            <span className="text-[10px] font-medium text-text-muted uppercase tracking-wide">Example answer</span>
                            <p className="text-xs text-text-secondary mt-0.5 italic">{request.example_answer}</p>
                          </div>
                        )}
                        {request.pro_tip && (
                          <div>
                            <span className="text-[10px] font-medium text-text-muted uppercase tracking-wide">Tip</span>
                            <p className="text-xs text-text-secondary mt-0.5">{request.pro_tip}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Answer area */}
                {!isDone ? (
                  <div className="border-t border-border/50 px-5 py-4">
                    {(request.input_type === 'text' || request.input_type === 'multi_text') && (
                      <div className="space-y-3">
                        <textarea
                          value={answers[request.id] || ''}
                          onChange={e => setAnswers(prev => ({ ...prev, [request.id]: e.target.value }))}
                          rows={3}
                          placeholder="Type your answer..."
                          className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
                        />
                        <div className="flex items-center justify-between">
                          <button
                            onClick={() => handleSkip(request.id)}
                            disabled={isSubmitting}
                            className="flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors disabled:opacity-50"
                          >
                            <SkipForward className="w-3.5 h-3.5" />
                            Skip
                          </button>
                          <button
                            onClick={() => handleSubmit(request)}
                            disabled={isSubmitting || !answers[request.id]?.trim()}
                            className="flex items-center gap-1.5 px-4 py-2 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-brand-primary-hover transition-colors disabled:opacity-50"
                          >
                            {isSubmitting ? (
                              <Spinner size="sm" />
                            ) : (
                              <Send className="w-3.5 h-3.5" />
                            )}
                            Submit
                          </button>
                        </div>
                      </div>
                    )}
                    {request.input_type === 'file' && (
                      <div className="space-y-3">
                        <p className="text-xs text-text-muted">File upload for this question type. Use the Materials page to upload files, then reference them here.</p>
                        <div className="flex items-center justify-between">
                          <button
                            onClick={() => handleSkip(request.id)}
                            disabled={isSubmitting}
                            className="flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors disabled:opacity-50"
                          >
                            <SkipForward className="w-3.5 h-3.5" />
                            Skip
                          </button>
                        </div>
                      </div>
                    )}
                    {request.input_type === 'text_and_file' && (
                      <div className="space-y-3">
                        <textarea
                          value={answers[request.id] || ''}
                          onChange={e => setAnswers(prev => ({ ...prev, [request.id]: e.target.value }))}
                          rows={3}
                          placeholder="Type your answer..."
                          className="w-full px-3 py-2 text-sm border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
                        />
                        <div className="flex items-center justify-between">
                          <button
                            onClick={() => handleSkip(request.id)}
                            disabled={isSubmitting}
                            className="flex items-center gap-1 text-xs text-text-muted hover:text-text-secondary transition-colors disabled:opacity-50"
                          >
                            <SkipForward className="w-3.5 h-3.5" />
                            Skip
                          </button>
                          <button
                            onClick={() => handleSubmit(request)}
                            disabled={isSubmitting || !answers[request.id]?.trim()}
                            className="flex items-center gap-1.5 px-4 py-2 bg-brand-primary text-white text-sm font-medium rounded-lg hover:bg-brand-primary-hover transition-colors disabled:opacity-50"
                          >
                            {isSubmitting ? (
                              <Spinner size="sm" />
                            ) : (
                              <Send className="w-3.5 h-3.5" />
                            )}
                            Submit
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="border-t border-border/50 px-5 py-3">
                    {isAnswered && existingAnswer && (
                      <p className="text-sm text-text-secondary italic">&ldquo;{existingAnswer}&rdquo;</p>
                    )}
                    {isSkipped && (
                      <p className="text-xs text-text-muted">Skipped</p>
                    )}
                  </div>
                )}

                {/* Readiness delta callout */}
                {delta && (
                  <div className="border-t border-border/50 px-5 py-3 bg-[#E8F5E9]/50">
                    <div className="flex items-center gap-2 text-sm">
                      <ArrowUpCircle className="w-4 h-4 text-brand-primary" />
                      <span className="text-text-secondary">
                        Readiness: {Math.round(delta.before)}% &rarr; {Math.round(delta.after)}%
                      </span>
                      <span className="font-semibold text-brand-primary">+{Math.round(delta.change)}%</span>
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
