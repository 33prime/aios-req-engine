'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import PrototypeFrame from '@/components/prototype/PrototypeFrame'
import { getPrototypeClientData, submitFeatureVerdict, completeClientReview } from '@/lib/api'
import { getStakeholderReview, submitStakeholderEpicVerdict } from '@/lib/api/portal'
import type { FeatureVerdict } from '@/types/prototype'
import type { StakeholderReviewData, VerdictType } from '@/types/portal'

interface FeatureReview {
  feature_name: string
  overlay_id: string
  consultant_verdict: FeatureVerdict | null
  consultant_notes: string | null
  suggested_verdict: FeatureVerdict | null
  validation_question: string | null
  validation_why: string | null
  validation_area: string | null
  spec_summary: string | null
  implementation_status: string | null
  confidence: number
  status: string
}

const VERDICT_OPTIONS: { value: FeatureVerdict; label: string; icon: string }[] = [
  { value: 'aligned', label: 'Aligned', icon: '\u2713' },
  { value: 'needs_adjustment', label: 'Needs Adjustment', icon: '\u26A0' },
  { value: 'off_track', label: 'Off Track', icon: '\u2717' },
]

const VERDICT_STYLES: Record<FeatureVerdict, { button: string; active: string }> = {
  aligned: {
    button: 'border-border hover:border-brand-primary hover:bg-[#E8F5E9]',
    active: 'border-brand-primary bg-[#E8F5E9] text-[#25785A]',
  },
  needs_adjustment: {
    button: 'border-border hover:border-amber-400 hover:bg-amber-50',
    active: 'border-amber-400 bg-amber-50 text-amber-800',
  },
  off_track: {
    button: 'border-border hover:border-red-400 hover:bg-red-50',
    active: 'border-red-400 bg-red-50 text-red-800',
  },
}

const EPIC_VERDICT_STYLES: Record<VerdictType, { button: string; active: string }> = {
  confirmed: {
    button: 'border-gray-200 hover:border-green-400 hover:bg-green-50',
    active: 'border-green-400 bg-green-50 text-green-800',
  },
  refine: {
    button: 'border-gray-200 hover:border-amber-400 hover:bg-amber-50',
    active: 'border-amber-400 bg-amber-50 text-amber-800',
  },
  flag: {
    button: 'border-gray-200 hover:border-red-400 hover:bg-red-50',
    active: 'border-red-400 bg-red-50 text-red-800',
  },
}

/**
 * Client prototype review page.
 *
 * Two modes:
 * 1. Token-based (legacy) — feature-level verdicts via magic link
 * 2. Stakeholder-aware — epic-level verdicts from portal nav, with assignment highlighting
 */
export default function PortalPrototypePage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const projectId = params.projectId as string
  const token = searchParams.get('token') || ''
  const sessionId = searchParams.get('session') || ''

  // Legacy feature mode
  const [deployUrl, setDeployUrl] = useState<string | null>(null)
  const [prototypeId, setPrototypeId] = useState<string | null>(null)
  const [featureReviews, setFeatureReviews] = useState<FeatureReview[]>([])
  const [clientVerdicts, setClientVerdicts] = useState<Record<string, FeatureVerdict>>({})
  const [clientNotes, setClientNotes] = useState<Record<string, string>>({})

  // Stakeholder epic mode
  const [stakeholderData, setStakeholderData] = useState<StakeholderReviewData | null>(null)
  const [epicVerdicts, setEpicVerdicts] = useState<Record<number, VerdictType>>({})
  const [epicNotes, setEpicNotes] = useState<Record<number, string>>({})

  const [submitted, setSubmitted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const isTokenMode = !!token && !!sessionId

  useEffect(() => {
    async function load() {
      try {
        if (isTokenMode) {
          // Legacy feature-level review via token
          const data = await getPrototypeClientData(sessionId, token)
          setPrototypeId(data.prototype_id)
          setDeployUrl(data.deploy_url)
          setFeatureReviews(data.feature_reviews || [])
        } else if (sessionId) {
          // Stakeholder epic review from portal
          const data = await getStakeholderReview(sessionId)
          setStakeholderData(data)
          setDeployUrl(data.deploy_url || null)
          // Pre-fill existing verdicts
          const existing: Record<number, VerdictType> = {}
          for (const e of data.epics) {
            if (e.verdict) existing[e.index] = e.verdict as VerdictType
          }
          setEpicVerdicts(existing)
        } else {
          // No session — try to find latest session for project
          setError('No prototype session available. Check back when your consultant shares one.')
        }
      } catch {
        setError('Unable to load prototype review.')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [sessionId, token, isTokenMode])

  // Legacy feature handlers
  const handleVerdictClick = useCallback(async (overlayId: string, verdict: FeatureVerdict) => {
    setClientVerdicts((prev) => ({ ...prev, [overlayId]: verdict }))
    if (prototypeId) {
      try {
        await submitFeatureVerdict(prototypeId, overlayId, verdict, 'client', clientNotes[overlayId] || undefined)
      } catch (err) {
        console.error('Failed to save client verdict:', err)
      }
    }
  }, [prototypeId, clientNotes])

  const handleNotesBlur = useCallback(async (overlayId: string) => {
    const verdict = clientVerdicts[overlayId]
    if (!verdict || !prototypeId) return
    try {
      await submitFeatureVerdict(prototypeId, overlayId, verdict, 'client', clientNotes[overlayId] || undefined)
    } catch (err) {
      console.error('Failed to save client notes:', err)
    }
  }, [prototypeId, clientVerdicts, clientNotes])

  // Stakeholder epic handlers
  const handleEpicVerdict = useCallback(async (epicIndex: number, verdict: VerdictType) => {
    setEpicVerdicts((prev) => ({ ...prev, [epicIndex]: verdict }))
    if (sessionId) {
      try {
        await submitStakeholderEpicVerdict(sessionId, {
          card_type: 'vision',
          card_index: epicIndex,
          verdict,
          notes: epicNotes[epicIndex],
        })
      } catch (err) {
        console.error('Failed to save epic verdict:', err)
      }
    }
  }, [sessionId, epicNotes])

  const handleEpicNotesBlur = useCallback(async (epicIndex: number) => {
    const verdict = epicVerdicts[epicIndex]
    if (!verdict || !sessionId) return
    try {
      await submitStakeholderEpicVerdict(sessionId, {
        card_type: 'vision',
        card_index: epicIndex,
        verdict,
        notes: epicNotes[epicIndex],
      })
    } catch (err) {
      console.error('Failed to save epic notes:', err)
    }
  }, [sessionId, epicVerdicts, epicNotes])

  const handleCompleteReview = async () => {
    setSubmitting(true)
    try {
      if (isTokenMode) {
        await completeClientReview(sessionId, token)
      }
    } catch (err) {
      console.error('Failed to complete review:', err)
    }
    setSubmitted(true)
    setSubmitting(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-gray-500">Loading prototype review...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center max-w-md">
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Review Unavailable</h2>
          <p className="text-sm text-gray-500">{error}</p>
        </div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-green-50 flex items-center justify-center">
            <span className="text-2xl text-green-600">{'\u2713'}</span>
          </div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">Thank You!</h2>
          <p className="text-sm text-gray-500">
            Your review has been submitted. The team will incorporate your feedback.
          </p>
        </div>
      </div>
    )
  }

  // ── Stakeholder Epic Review Mode ─────────────────────────────────
  if (stakeholderData && !isTokenMode) {
    return (
      <div className="flex flex-col" style={{ height: 'calc(100vh - 160px)' }}>
        {/* Prototype iframe — top 55% */}
        <div className="flex-[55] min-h-0">
          {deployUrl ? (
            <PrototypeFrame
              deployUrl={deployUrl}
              onFeatureClick={() => {}}
              onPageChange={() => {}}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              Prototype preview unavailable
            </div>
          )}
        </div>

        {/* Epic review cards — bottom 45% */}
        <div className="flex-[45] border-t border-gray-200 bg-gray-50 overflow-y-auto">
          <div className="max-w-3xl mx-auto p-6 space-y-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-500">
                {Object.keys(epicVerdicts).length}/{stakeholderData.total_epics} epics reviewed
              </span>
            </div>

            {stakeholderData.epics.map((epic) => {
              const selectedVerdict = epicVerdicts[epic.index] || null
              const notes = epicNotes[epic.index] || ''

              return (
                <div
                  key={epic.index}
                  className={`
                    rounded-xl border bg-white shadow-sm
                    ${epic.is_assigned_to_me && !selectedVerdict
                      ? 'border-[#009b87]/40 ring-1 ring-[#009b87]/20'
                      : 'border-gray-200'}
                  `}
                >
                  {/* Epic header */}
                  <div className="px-5 py-4 border-b border-gray-100">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="text-sm font-semibold text-gray-900">{epic.title}</h3>
                        {epic.theme && (
                          <p className="text-xs text-gray-500 mt-0.5">{epic.theme}</p>
                        )}
                      </div>
                      {epic.is_assigned_to_me && !selectedVerdict && (
                        <span className="text-[10px] bg-[#009b87]/10 text-[#009b87] px-2 py-0.5 rounded-full font-medium">
                          Your review
                        </span>
                      )}
                    </div>
                    {epic.features.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {epic.features.map((f, i) => (
                          <span key={i} className="text-[10px] bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                            {f.name}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Narrative */}
                  {epic.narrative && (
                    <div className="px-5 py-3 border-b border-gray-100">
                      <p className="text-xs text-gray-600 leading-relaxed line-clamp-3">
                        {epic.narrative}
                      </p>
                    </div>
                  )}

                  {/* Verdict buttons */}
                  <div className="px-5 py-3 border-b border-gray-100">
                    <div className="flex gap-2">
                      {(['confirmed', 'refine', 'flag'] as VerdictType[]).map(v => {
                        const isActive = selectedVerdict === v
                        const styles = EPIC_VERDICT_STYLES[v]
                        const labels = { confirmed: 'Confirm', refine: 'Refine', flag: 'Flag' }
                        const icons = { confirmed: '\u2713', refine: '\u270E', flag: '\u26A0' }
                        return (
                          <button
                            key={v}
                            onClick={() => handleEpicVerdict(epic.index, v)}
                            className={`flex-1 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${
                              isActive ? styles.active : styles.button
                            }`}
                          >
                            <span className="mr-1">{icons[v]}</span>
                            {labels[v]}
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Notes */}
                  <div className="px-5 py-3">
                    <textarea
                      value={notes}
                      onChange={(e) => setEpicNotes((prev) => ({ ...prev, [epic.index]: e.target.value }))}
                      onBlur={() => handleEpicNotesBlur(epic.index)}
                      rows={2}
                      placeholder="Feedback (optional)..."
                      className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#009b87]/20 focus:border-[#009b87] resize-none"
                    />
                  </div>
                </div>
              )
            })}

            <div className="pt-4 pb-8">
              <button
                onClick={handleCompleteReview}
                disabled={submitting}
                className="w-full px-6 py-3 bg-[#009b87] text-white font-medium rounded-xl hover:bg-[#008775] transition-all shadow-md disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Complete Review'}
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Legacy Feature Review Mode (token-based) ─────────────────────
  const sortedReviews = [...featureReviews].sort((a, b) => {
    const order: Record<string, number> = { off_track: 0, needs_adjustment: 1, aligned: 2 }
    const aScore = a.consultant_verdict ? (order[a.consultant_verdict] ?? 3) : 3
    const bScore = b.consultant_verdict ? (order[b.consultant_verdict] ?? 3) : 3
    return aScore - bScore
  })

  const reviewedCount = Object.keys(clientVerdicts).length

  return (
    <div className="flex flex-col h-screen bg-[#F4F4F4]">
      <div className="bg-[#0A1E2F] px-6 py-4">
        <h1 className="text-lg font-semibold text-white">Prototype Review</h1>
        <p className="text-sm text-white/60 mt-0.5">
          Review each feature below and share your verdict.
        </p>
      </div>

      <div className="flex-[55] min-h-0">
        {deployUrl ? (
          <PrototypeFrame
            deployUrl={deployUrl}
            onFeatureClick={() => {}}
            onPageChange={() => {}}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            Prototype preview unavailable
          </div>
        )}
      </div>

      <div className="flex-[45] border-t border-gray-200 bg-[#F4F4F4] overflow-y-auto">
        <div className="max-w-3xl mx-auto p-6 space-y-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-500">
              {reviewedCount}/{featureReviews.length} features reviewed
            </span>
          </div>

          {sortedReviews.map((review) => {
            const selectedVerdict = clientVerdicts[review.overlay_id] || null
            const notes = clientNotes[review.overlay_id] || ''

            return (
              <div key={review.overlay_id} className="rounded-2xl border border-gray-200 bg-white shadow-md">
                <div className="px-5 py-4 border-b border-gray-100">
                  <div className="flex items-start justify-between">
                    <h3 className="text-sm font-semibold text-gray-900">{review.feature_name}</h3>
                    <span className="text-[10px] text-gray-400">
                      {Math.round(review.confidence * 100)}% confidence
                    </span>
                  </div>
                </div>

                {review.consultant_verdict && (
                  <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-medium text-gray-500 uppercase tracking-wide">
                        Consultant says:
                      </span>
                      <span className={`text-[11px] font-semibold ${
                        review.consultant_verdict === 'aligned' ? 'text-green-700' :
                        review.consultant_verdict === 'needs_adjustment' ? 'text-amber-700' :
                        'text-red-700'
                      }`}>
                        {review.consultant_verdict === 'aligned' ? '\u2713 Aligned' :
                         review.consultant_verdict === 'needs_adjustment' ? '\u26A0 Needs Adjustment' :
                         '\u2717 Off Track'}
                      </span>
                    </div>
                    {review.consultant_notes && (
                      <p className="text-xs text-gray-500">&ldquo;{review.consultant_notes}&rdquo;</p>
                    )}
                  </div>
                )}

                {review.validation_question && (
                  <div className="px-5 py-3 border-b border-gray-100">
                    <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wide mb-1">Key Question</p>
                    <p className="text-sm text-gray-900">&ldquo;{review.validation_question}&rdquo;</p>
                    {review.validation_area && (
                      <span className="text-[10px] mt-1 inline-block px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                        {review.validation_area.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                )}

                <div className="px-5 py-3 border-b border-gray-100">
                  <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wide mb-2">Your Verdict</p>
                  <div className="flex gap-2">
                    {VERDICT_OPTIONS.map(({ value, label, icon }) => {
                      const isActive = selectedVerdict === value
                      const styles = VERDICT_STYLES[value]
                      return (
                        <button
                          key={value}
                          onClick={() => handleVerdictClick(review.overlay_id, value)}
                          className={`flex-1 px-3 py-2 rounded-xl border text-xs font-medium transition-all ${
                            isActive ? styles.active : styles.button
                          }`}
                        >
                          <span className="mr-1">{icon}</span>
                          {label}
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div className="px-5 py-3">
                  <textarea
                    value={notes}
                    onChange={(e) => setClientNotes((prev) => ({ ...prev, [review.overlay_id]: e.target.value }))}
                    onBlur={() => handleNotesBlur(review.overlay_id)}
                    rows={2}
                    placeholder="Your feedback (optional)..."
                    className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#009b87]/20 focus:border-[#009b87] resize-none"
                  />
                </div>
              </div>
            )
          })}

          <div className="pt-4 pb-8">
            <button
              onClick={handleCompleteReview}
              disabled={submitting}
              className="w-full px-6 py-3 bg-[#009b87] text-white font-medium rounded-xl hover:bg-[#008775] transition-all shadow-md disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Complete Review'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
