'use client'

import { useState, useEffect, useCallback } from 'react'
import { X, Play, Eye, RotateCcw, Loader2 } from 'lucide-react'
import {
  getPrototypeForProject,
  getPrototypeOverlays,
  getVpSteps,
  listPrototypeSessions,
  createPrototypeSession,
} from '@/lib/api'
import { buildTourPlan } from './TourController'
import type { FeatureOverlay, FeatureVerdict, PrototypeSession } from '@/types/prototype'
import type { VpStep } from '@/types/api'

interface ReviewStartModalProps {
  projectId: string
  isOpen: boolean
  onClose: () => void
  onStartReview: (
    session: PrototypeSession,
    overlays: FeatureOverlay[],
    vpSteps: VpStep[],
    prototypeId: string,
    deployUrl: string,
    mode: 'tour' | 'explore'
  ) => void
}

export default function ReviewStartModal({
  projectId,
  isOpen,
  onClose,
  onStartReview,
}: ReviewStartModalProps) {
  const [loading, setLoading] = useState(true)
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Loaded data
  const [overlays, setOverlays] = useState<FeatureOverlay[]>([])
  const [vpSteps, setVpSteps] = useState<VpStep[]>([])
  const [sessions, setSessions] = useState<PrototypeSession[]>([])
  const [prototypeId, setPrototypeId] = useState<string | null>(null)
  const [deployUrl, setDeployUrl] = useState<string | null>(null)

  // Tour plan breakdown
  const [primaryCount, setPrimaryCount] = useState(0)
  const [supportingCount, setSupportingCount] = useState(0)
  const [unmappedCount, setUnmappedCount] = useState(0)

  // Resumable session
  const resumableSession = sessions.find(
    (s) => s.status === 'consultant_review'
  )
  const resumeProgress = resumableSession
    ? overlays.filter((o) => o.consultant_verdict).length
    : 0
  const resumeVerdictCounts = resumableSession
    ? overlays.reduce(
        (acc, o) => {
          if (o.consultant_verdict === 'aligned') acc.aligned++
          else if (o.consultant_verdict === 'needs_adjustment') acc.adjust++
          else if (o.consultant_verdict === 'off_track') acc.off++
          return acc
        },
        { aligned: 0, adjust: 0, off: 0 }
      )
    : null

  useEffect(() => {
    if (!isOpen) return
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const proto = await getPrototypeForProject(projectId)
        if (cancelled) return
        setPrototypeId(proto.id)
        setDeployUrl(proto.deploy_url ?? null)

        const [ovls, steps, sess] = await Promise.all([
          getPrototypeOverlays(proto.id),
          getVpSteps(projectId),
          listPrototypeSessions(proto.id),
        ])
        if (cancelled) return

        setOverlays(ovls)
        setVpSteps(steps)
        setSessions(sess)

        // Build tour plan for counts
        const plan = buildTourPlan(ovls, steps, new Map())
        const primary = plan.phases.primary_flow.flatMap((g) => g.steps).length
        const secondary = plan.phases.secondary_flow.flatMap((g) => g.steps).length
        const deep = plan.phases.deep_dive.flatMap((g) => g.steps).length
        setPrimaryCount(primary)
        setSupportingCount(secondary)
        setUnmappedCount(deep)
      } catch (err) {
        if (!cancelled) setError('Failed to load prototype data')
        console.error(err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [isOpen, projectId])

  const handleStart = useCallback(
    async (mode: 'tour' | 'explore', existingSession?: PrototypeSession) => {
      if (!prototypeId || !deployUrl) return
      setStarting(true)
      try {
        let session: PrototypeSession
        if (existingSession) {
          session = existingSession
        } else {
          session = await createPrototypeSession(prototypeId)
        }
        onStartReview(session, overlays, vpSteps, prototypeId, deployUrl, mode)
      } catch (err) {
        console.error('Failed to start review:', err)
        setError('Failed to create session')
      } finally {
        setStarting(false)
      }
    },
    [prototypeId, deployUrl, overlays, vpSteps, onStartReview]
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-text-placeholder hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors z-10"
        >
          <X className="w-4 h-4" />
        </button>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 text-brand-primary animate-spin" />
          </div>
        ) : error ? (
          <div className="p-8 text-center">
            <p className="text-sm text-red-600 mb-3">{error}</p>
            <button
              onClick={onClose}
              className="text-sm text-[#666666] hover:text-text-body"
            >
              Close
            </button>
          </div>
        ) : (
          <div className="p-6">
            <h2 className="text-lg font-semibold text-text-body mb-1">
              Prototype Review
            </h2>
            <p className="text-sm text-[#666666] mb-5">
              {overlays.length} features analyzed
            </p>

            {/* Feature breakdown */}
            <div className="rounded-2xl border border-border bg-surface-page px-4 py-3 mb-5">
              <p className="text-[11px] font-medium text-[#666666] uppercase tracking-wide mb-2">Tour Breakdown</p>
              <div className="flex items-center gap-3 text-xs text-[#666666]">
                {primaryCount > 0 && (
                  <span>
                    <strong className="text-text-body">{primaryCount}</strong>{' '}
                    primary flow
                  </span>
                )}
                {supportingCount > 0 && (
                  <>
                    <span className="text-border">&middot;</span>
                    <span>
                      <strong className="text-text-body">{supportingCount}</strong>{' '}
                      supporting
                    </span>
                  </>
                )}
                {unmappedCount > 0 && (
                  <>
                    <span className="text-border">&middot;</span>
                    <span>
                      <strong className="text-text-body">{unmappedCount}</strong>{' '}
                      unmapped
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Resumable session */}
            {resumableSession && resumeVerdictCounts && (
              <div className="rounded-2xl border border-brand-primary/30 bg-[#E8F5E9]/30 px-4 py-4 mb-5">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-medium text-text-body">
                    Session #{resumableSession.session_number} &mdash;{' '}
                    {resumeProgress}/{overlays.length} reviewed
                  </span>
                  <span className="text-[10px] text-text-placeholder">
                    {Math.round((resumeProgress / Math.max(overlays.length, 1)) * 100)}%
                  </span>
                </div>

                {/* Progress bar */}
                <div className="h-1.5 rounded-full bg-border overflow-hidden mb-3">
                  <div
                    className="h-full bg-brand-primary transition-all"
                    style={{
                      width: `${(resumeProgress / Math.max(overlays.length, 1)) * 100}%`,
                    }}
                  />
                </div>

                {/* Verdict counts */}
                <div className="flex gap-3 text-[11px] text-[#666666] mb-3">
                  {resumeVerdictCounts.aligned > 0 && (
                    <span>
                      <span className="font-semibold text-[#25785A]">{resumeVerdictCounts.aligned}</span> Aligned
                    </span>
                  )}
                  {resumeVerdictCounts.adjust > 0 && (
                    <span>
                      <span className="font-semibold text-amber-700">{resumeVerdictCounts.adjust}</span> Adjust
                    </span>
                  )}
                  {resumeVerdictCounts.off > 0 && (
                    <span>
                      <span className="font-semibold text-red-700">{resumeVerdictCounts.off}</span> Off Track
                    </span>
                  )}
                </div>

                {/* Resume buttons */}
                <div className="flex gap-2">
                  <button
                    onClick={() => handleStart('tour', resumableSession)}
                    disabled={starting}
                    className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 bg-brand-primary text-white text-xs font-medium rounded-xl hover:bg-[#25785A] transition-all disabled:opacity-60"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Resume Tour
                  </button>
                  <button
                    onClick={() => handleStart('explore', resumableSession)}
                    disabled={starting}
                    className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 border border-border text-text-body text-xs font-medium rounded-xl hover:bg-[#F4F4F4] transition-all disabled:opacity-60"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Resume Free
                  </button>
                </div>
              </div>
            )}

            {/* Start buttons */}
            <div className="flex gap-3">
              <button
                onClick={() => handleStart('tour')}
                disabled={starting}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-brand-primary text-white font-medium rounded-xl hover:bg-[#25785A] transition-all shadow-md disabled:opacity-60"
              >
                {starting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Start Guided Tour
              </button>
              <button
                onClick={() => handleStart('explore')}
                disabled={starting}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 border border-border text-text-body font-medium rounded-xl hover:bg-[#F4F4F4] transition-all shadow-md disabled:opacity-60"
              >
                <Eye className="w-4 h-4" />
                Free Explore
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
