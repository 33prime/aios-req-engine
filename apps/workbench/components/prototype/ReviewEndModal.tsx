'use client'

import { useState } from 'react'
import { X, Copy, Check, Loader2, Radio } from 'lucide-react'
import type { FeatureOverlay } from '@/types/prototype'

interface ReviewEndModalProps {
  isOpen: boolean
  overlays: FeatureOverlay[]
  clientShareData: { token: string; url: string }
  onShareWithClient: () => void
  onFixFirst: () => void
  onKeepWorking: () => void
}

export default function ReviewEndModal({
  isOpen,
  overlays,
  clientShareData,
  onShareWithClient,
  onFixFirst,
  onKeepWorking,
}: ReviewEndModalProps) {
  const [copied, setCopied] = useState(false)
  const [isSharing, setIsSharing] = useState(false)

  if (!isOpen) return null

  const fullUrl =
    typeof window !== 'undefined'
      ? `${window.location.origin}${clientShareData.url}`
      : clientShareData.url

  const verdictCounts = overlays.reduce(
    (acc, o) => {
      const v = o.consultant_verdict
      if (v === 'aligned') acc.aligned++
      else if (v === 'needs_adjustment') acc.needs_adjustment++
      else if (v === 'off_track') acc.off_track++
      return acc
    },
    { aligned: 0, needs_adjustment: 0, off_track: 0 }
  )

  const total = overlays.length
  const alignedPct = total > 0 ? (verdictCounts.aligned / total) * 100 : 0
  const adjustPct = total > 0 ? (verdictCounts.needs_adjustment / total) * 100 : 0
  const offPct = total > 0 ? (verdictCounts.off_track / total) * 100 : 0
  const overallScore = total > 0 ? Math.round(alignedPct) : 0

  const handleCopy = () => {
    navigator.clipboard.writeText(fullUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleShare = async () => {
    setIsSharing(true)
    try {
      await onShareWithClient()
    } finally {
      setIsSharing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="relative w-full max-w-md bg-white rounded-2xl shadow-xl overflow-hidden">
        {/* Close button */}
        <button
          onClick={onKeepWorking}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[#999999] hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors z-10"
        >
          <X className="w-4 h-4" />
        </button>

        <div className="p-6">
          <h2 className="text-lg font-semibold text-[#333333] mb-1">
            Review Complete
          </h2>
          <p className="text-sm text-[#666666] mb-5">
            All features reviewed. Ready to share with client.
          </p>

          {/* Verdict summary card */}
          <div className="rounded-2xl border border-[#E5E5E5] bg-white p-5 shadow-md mb-5">
            <p className="text-[11px] font-medium text-[#666666] uppercase tracking-wide mb-3">
              Verdict Summary
            </p>
            <div className="flex gap-4 mb-4">
              <div className="flex-1 text-center">
                <div className="text-xl font-bold text-[#25785A]">
                  {verdictCounts.aligned}
                </div>
                <div className="text-[10px] text-[#666666]">Aligned</div>
              </div>
              <div className="flex-1 text-center">
                <div className="text-xl font-bold text-amber-700">
                  {verdictCounts.needs_adjustment}
                </div>
                <div className="text-[10px] text-[#666666]">Adjust</div>
              </div>
              <div className="flex-1 text-center">
                <div className="text-xl font-bold text-red-700">
                  {verdictCounts.off_track}
                </div>
                <div className="text-[10px] text-[#666666]">Off Track</div>
              </div>
            </div>

            {/* Tri-color progress bar */}
            <div className="h-2 rounded-full bg-[#E5E5E5] overflow-hidden flex">
              {alignedPct > 0 && (
                <div
                  className="h-full bg-[#3FAF7A] transition-all"
                  style={{ width: `${alignedPct}%` }}
                />
              )}
              {adjustPct > 0 && (
                <div
                  className="h-full bg-amber-500 transition-all"
                  style={{ width: `${adjustPct}%` }}
                />
              )}
              {offPct > 0 && (
                <div
                  className="h-full bg-red-500 transition-all"
                  style={{ width: `${offPct}%` }}
                />
              )}
            </div>
            <div className="text-right mt-1.5">
              <span className="text-xs font-medium text-[#333333]">
                {overallScore}% aligned
              </span>
            </div>
          </div>

          {/* Client review link */}
          <div className="rounded-2xl border border-[#E5E5E5] bg-white p-5 shadow-md mb-5">
            <p className="text-[11px] font-medium text-[#666666] uppercase tracking-wide mb-2">
              Client Review Link
            </p>
            <div className="flex items-center gap-2">
              <input
                readOnly
                value={fullUrl}
                className="flex-1 text-xs px-3 py-2 border border-[#E5E5E5] rounded-lg bg-[#F4F4F4] text-[#333333] truncate"
              />
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-3 py-2 text-xs font-medium border border-[#E5E5E5] rounded-lg hover:bg-[#F4F4F4] transition-colors text-[#333333]"
              >
                {copied ? (
                  <>
                    <Check className="w-3 h-3 text-[#3FAF7A]" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    Copy
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Action buttons */}
          <div className="space-y-3">
            <button
              onClick={handleShare}
              disabled={isSharing}
              className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-[#3FAF7A] text-white font-medium rounded-xl hover:bg-[#25785A] transition-all duration-200 shadow-md disabled:opacity-60"
            >
              {isSharing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : null}
              Share with Client — All Good
            </button>
            <button
              onClick={onFixFirst}
              className="w-full px-6 py-3 bg-white border border-[#E5E5E5] text-[#333333] font-medium rounded-xl hover:bg-[#F4F4F4] transition-all duration-200 shadow-md"
            >
              Fix First, Then Share
            </button>
            <button
              onClick={onKeepWorking}
              className="w-full px-4 py-2 text-sm text-[#666666] hover:text-[#333333] transition-colors"
            >
              Not Ready — Keep Working
            </button>
          </div>

          {/* Polling indicator */}
          <div className="flex items-center justify-center gap-2 mt-5">
            <Radio className="w-3 h-3 text-[#3FAF7A] animate-pulse" />
            <span className="text-[10px] text-[#999999]">
              Listening for client feedback...
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
