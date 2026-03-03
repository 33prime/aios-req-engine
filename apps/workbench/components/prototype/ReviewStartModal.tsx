'use client'

import { useState, useEffect, useCallback } from 'react'
import { X, Loader2, Compass, RotateCcw } from 'lucide-react'
import {
  getPrototypeForProject,
  getPrototypeOverlays,
  getEpicPlan,
  getVpSteps,
  listPrototypeSessions,
  createPrototypeSession,
  getEpicVerdicts,
} from '@/lib/api'
import type { FeatureOverlay, PrototypeSession } from '@/types/prototype'
import type { VpStep } from '@/types/api'
import type { EpicOverlayPlan } from '@/types/epic-overlay'

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

  const [overlays, setOverlays] = useState<FeatureOverlay[]>([])
  const [vpSteps, setVpSteps] = useState<VpStep[]>([])
  const [sessions, setSessions] = useState<PrototypeSession[]>([])
  const [prototypeId, setPrototypeId] = useState<string | null>(null)
  const [deployUrl, setDeployUrl] = useState<string | null>(null)
  const [epicPlan, setEpicPlan] = useState<EpicOverlayPlan | null>(null)
  const [resumeConfirmed, setResumeConfirmed] = useState(0)

  const resumableSession = sessions.find(
    (s) => s.status === 'consultant_review'
  )

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

        const [ovls, steps, sess, plan] = await Promise.all([
          getPrototypeOverlays(proto.id),
          getVpSteps(projectId),
          listPrototypeSessions(proto.id),
          getEpicPlan(proto.id).catch(() => null),
        ])
        if (cancelled) return

        setOverlays(ovls)
        setVpSteps(steps)
        setSessions(sess)
        setEpicPlan(plan)

        // Check resume progress
        const activeSession = sess.find((s: PrototypeSession) => s.status === 'consultant_review')
        if (activeSession) {
          try {
            const verdicts = await getEpicVerdicts(activeSession.id)
            setResumeConfirmed(verdicts.filter((v) => v.verdict).length)
          } catch {
            setResumeConfirmed(0)
          }
        }
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
    async (existingSession?: PrototypeSession) => {
      if (!prototypeId || !deployUrl) return
      setStarting(true)
      try {
        const session = existingSession
          ? existingSession
          : await createPrototypeSession(prototypeId)
        onStartReview(session, overlays, vpSteps, prototypeId, deployUrl, 'tour')
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

  // Phase card from epic plan — Vision only
  const epicCount = epicPlan?.vision_epics.length ?? 0
  const totalCards = epicCount

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Close */}
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
            <p className="text-sm text-[#666666] mb-3">{error}</p>
            <button onClick={onClose} className="text-sm text-[#666666] hover:text-text-body">
              Close
            </button>
          </div>
        ) : (
          <div className="p-6">
            <h2 className="text-lg font-semibold text-[#37352f] mb-1">
              Prototype Review
            </h2>
            <p className="text-[13px] text-[#666666] mb-6">
              Walk through your prototype&apos;s value story.
            </p>

            {/* Phase card — Vision epics */}
            {epicCount > 0 && (
              <div className="flex justify-center mb-6">
                <div className="rounded-xl border border-border bg-[#F8FAF8] p-4 text-center min-w-[120px]">
                  <div className="flex justify-center mb-1.5">
                    <Compass className="w-5 h-5 text-brand-primary" />
                  </div>
                  <div className="text-lg font-semibold text-[#37352f]">{epicCount}</div>
                  <div className="text-[11px] text-[#666666]">Epics</div>
                </div>
              </div>
            )}

            {/* Start Tour */}
            <button
              onClick={() => handleStart()}
              disabled={starting || totalCards === 0}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-brand-primary text-white font-medium rounded-xl hover:bg-[#25785A] transition-all shadow-sm disabled:opacity-60"
            >
              {starting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : null}
              {starting ? 'Starting...' : 'Start Tour'}
            </button>

            {/* Resume option */}
            {resumableSession && (
              <button
                onClick={() => handleStart(resumableSession)}
                disabled={starting}
                className="w-full mt-3 flex items-center justify-center gap-1.5 text-[13px] text-[#666666] hover:text-[#37352f] transition-colors disabled:opacity-50"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Resume Session #{resumableSession.session_number}
                {resumeConfirmed > 0 && (
                  <span className="text-[11px] text-text-placeholder">
                    &mdash; {resumeConfirmed}/{totalCards} confirmed
                  </span>
                )}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
