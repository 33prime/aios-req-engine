'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams, useSearchParams } from 'next/navigation'
import PrototypeFrame from '@/components/prototype/PrototypeFrame'
import { getPrototypeClientData, submitFeatureVerdict } from '@/lib/api'
import type { FeatureVerdict } from '@/types/prototype'

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
    button: 'border-[#E5E5E5] hover:border-[#3FAF7A] hover:bg-[#E8F5E9]',
    active: 'border-[#3FAF7A] bg-[#E8F5E9] text-[#25785A]',
  },
  needs_adjustment: {
    button: 'border-[#E5E5E5] hover:border-amber-400 hover:bg-amber-50',
    active: 'border-amber-400 bg-amber-50 text-amber-800',
  },
  off_track: {
    button: 'border-[#E5E5E5] hover:border-red-400 hover:bg-red-50',
    active: 'border-red-400 bg-red-50 text-red-800',
  },
}

/**
 * Client prototype review page — per-feature verdict cards with consultant context.
 *
 * Layout:
 * - Top 55%: PrototypeFrame (iframe)
 * - Bottom 45%: Per-feature review cards
 */
export default function PortalPrototypePage() {
  const params = useParams()
  const searchParams = useSearchParams()
  const projectId = params.projectId as string
  const token = searchParams.get('token') || ''
  const sessionId = searchParams.get('session') || ''

  const [deployUrl, setDeployUrl] = useState<string | null>(null)
  const [prototypeId, setPrototypeId] = useState<string | null>(null)
  const [featureReviews, setFeatureReviews] = useState<FeatureReview[]>([])
  const [clientVerdicts, setClientVerdicts] = useState<Record<string, FeatureVerdict>>({})
  const [clientNotes, setClientNotes] = useState<Record<string, string>>({})
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Load client data
  useEffect(() => {
    async function load() {
      if (!sessionId || !token) {
        setError('Missing session or token parameter.')
        setLoading(false)
        return
      }
      try {
        const data = await getPrototypeClientData(sessionId, token)
        setDeployUrl(data.deploy_url)
        setFeatureReviews(data.feature_reviews || [])
        setLoading(false)
      } catch {
        setError('Unable to load prototype review. The link may have expired.')
        setLoading(false)
      }
    }
    load()
  }, [sessionId, token])

  // Sort: off_track first, then needs_adjustment, then aligned, then unreviewed
  const sortedReviews = [...featureReviews].sort((a, b) => {
    const order: Record<string, number> = { off_track: 0, needs_adjustment: 1, aligned: 2 }
    const aScore = a.consultant_verdict ? (order[a.consultant_verdict] ?? 3) : 3
    const bScore = b.consultant_verdict ? (order[b.consultant_verdict] ?? 3) : 3
    return aScore - bScore
  })

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

  const handleCompleteReview = () => {
    setSubmitted(true)
  }

  const reviewedCount = Object.keys(clientVerdicts).length

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#F4F4F4]">
        <p className="text-[#999999]">Loading prototype review...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#F4F4F4]">
        <div className="text-center max-w-md">
          <h2 className="text-lg font-semibold text-[#333333] mb-2">Review Unavailable</h2>
          <p className="text-sm text-[#666666]">{error}</p>
        </div>
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#F4F4F4]">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[#E8F5E9] flex items-center justify-center">
            <span className="text-2xl text-[#3FAF7A]">{'\u2713'}</span>
          </div>
          <h2 className="text-lg font-semibold text-[#333333] mb-2">Thank You!</h2>
          <p className="text-sm text-[#666666]">
            Your review has been submitted. The team will incorporate your feedback into the next iteration.
          </p>
          <p className="text-xs text-[#999999] mt-3">
            {reviewedCount} of {featureReviews.length} features reviewed
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen bg-[#F4F4F4]">
      {/* Header */}
      <div className="bg-[#0A1E2F] px-6 py-4">
        <h1 className="text-lg font-semibold text-white">Prototype Review</h1>
        <p className="text-sm text-white/60 mt-0.5">
          Review each feature below and share your verdict.
        </p>
      </div>

      {/* Prototype iframe — top 55% */}
      <div className="flex-[55] min-h-0">
        {deployUrl ? (
          <PrototypeFrame
            deployUrl={deployUrl}
            onFeatureClick={() => {}}
            onPageChange={() => {}}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-[#999999]">
            Prototype preview unavailable
          </div>
        )}
      </div>

      {/* Per-feature review cards — bottom 45% */}
      <div className="flex-[45] border-t border-[#E5E5E5] bg-[#F4F4F4] overflow-y-auto">
        <div className="max-w-3xl mx-auto p-6 space-y-4">
          {/* Progress bar */}
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-[#666666]">
              {reviewedCount}/{featureReviews.length} features reviewed
            </span>
          </div>

          {sortedReviews.map((review) => {
            const selectedVerdict = clientVerdicts[review.overlay_id] || null
            const notes = clientNotes[review.overlay_id] || ''

            return (
              <div
                key={review.overlay_id}
                className="rounded-2xl border border-[#E5E5E5] bg-white shadow-md"
              >
                {/* Feature header */}
                <div className="px-5 py-4 border-b border-[#E5E5E5]">
                  <div className="flex items-start justify-between">
                    <h3 className="text-sm font-semibold text-[#333333]">
                      {review.feature_name}
                    </h3>
                    <span className="text-[10px] text-[#999999]">
                      {Math.round(review.confidence * 100)}% confidence
                    </span>
                  </div>
                </div>

                {/* Consultant context */}
                {review.consultant_verdict && (
                  <div className="px-5 py-3 border-b border-[#E5E5E5] bg-[#F4F4F4]">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[11px] font-medium text-[#666666] uppercase tracking-wide">
                        Consultant says:
                      </span>
                      <span className={`text-[11px] font-semibold ${
                        review.consultant_verdict === 'aligned' ? 'text-[#25785A]' :
                        review.consultant_verdict === 'needs_adjustment' ? 'text-amber-700' :
                        'text-red-700'
                      }`}>
                        {review.consultant_verdict === 'aligned' ? '\u2713 Aligned' :
                         review.consultant_verdict === 'needs_adjustment' ? '\u26A0 Needs Adjustment' :
                         '\u2717 Off Track'}
                      </span>
                    </div>
                    {review.consultant_notes && (
                      <p className="text-xs text-[#666666] leading-relaxed">
                        &ldquo;{review.consultant_notes}&rdquo;
                      </p>
                    )}
                  </div>
                )}

                {/* Validation question */}
                {review.validation_question && (
                  <div className="px-5 py-3 border-b border-[#E5E5E5]">
                    <p className="text-[11px] font-medium text-[#666666] uppercase tracking-wide mb-1">
                      Key Question
                    </p>
                    <p className="text-sm text-[#333333] leading-relaxed">
                      &ldquo;{review.validation_question}&rdquo;
                    </p>
                    {review.validation_area && (
                      <span className="text-[10px] mt-1 inline-block px-1.5 py-0.5 rounded bg-[#F0F0F0] text-[#666666]">
                        {review.validation_area.replace('_', ' ')}
                      </span>
                    )}
                  </div>
                )}

                {/* Client verdict buttons */}
                <div className="px-5 py-3 border-b border-[#E5E5E5]">
                  <p className="text-[11px] font-medium text-[#666666] uppercase tracking-wide mb-2">
                    Your Verdict
                  </p>
                  <div className="flex gap-2">
                    {VERDICT_OPTIONS.map(({ value, label, icon }) => {
                      const isActive = selectedVerdict === value
                      const styles = VERDICT_STYLES[value]
                      return (
                        <button
                          key={value}
                          onClick={() => handleVerdictClick(review.overlay_id, value)}
                          className={`flex-1 px-3 py-2 rounded-xl border text-xs font-medium transition-all duration-200 ${
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

                {/* Client notes */}
                <div className="px-5 py-3">
                  <textarea
                    value={notes}
                    onChange={(e) => setClientNotes((prev) => ({ ...prev, [review.overlay_id]: e.target.value }))}
                    onBlur={() => handleNotesBlur(review.overlay_id)}
                    rows={2}
                    placeholder="Your feedback (optional)..."
                    className="w-full px-3 py-2 text-sm border border-[#E5E5E5] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#3FAF7A]/20 focus:border-[#3FAF7A] resize-none text-[#333333] placeholder:text-[#999999]"
                  />
                </div>
              </div>
            )
          })}

          {/* Complete Review button */}
          <div className="pt-4 pb-8">
            <button
              onClick={handleCompleteReview}
              className="w-full px-6 py-3 bg-[#3FAF7A] text-white font-medium rounded-xl hover:bg-[#25785A] transition-all duration-200 shadow-md"
            >
              Complete Review
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
