'use client'

import { CheckCircle, Pencil, HelpCircle, Calendar, ArrowRight } from 'lucide-react'
import type { AssumptionResponseType } from '@/types/portal'

interface SummaryAssumption {
  text: string
  response: AssumptionResponseType | null
}

interface SummaryEpic {
  index: number
  title: string
  assumptions: SummaryAssumption[]
}

interface ExplorationSummaryProps {
  epics: SummaryEpic[]
  consultantName?: string
  bookingUrl?: string
  onComplete: () => void
  isSubmitting: boolean
}

export function ExplorationSummary({
  epics,
  consultantName,
  bookingUrl,
  onComplete,
  isSubmitting,
}: ExplorationSummaryProps) {
  // Categorize assumptions across all epics
  const confirmed: Array<{ epicTitle: string; text: string }> = []
  const needsDiscussion: Array<{ epicTitle: string; text: string }> = []
  const escalated: Array<{ epicTitle: string; text: string }> = []
  let skippedCount = 0

  for (const epic of epics) {
    for (const a of epic.assumptions) {
      if (a.response === 'great' || a.response === 'agree') {
        confirmed.push({ epicTitle: epic.title, text: a.text })
      } else if (a.response === 'refine') {
        needsDiscussion.push({ epicTitle: epic.title, text: a.text })
      } else if (a.response === 'question' || a.response === 'disagree') {
        escalated.push({ epicTitle: epic.title, text: a.text })
      } else {
        skippedCount++
      }
    }
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-80px)] bg-gradient-to-b from-[#0A1E2F] to-[#15314A]">
      <div className="w-full max-w-lg mx-auto px-6 py-8">
        <h1 className="text-2xl font-semibold text-white mb-2 text-center">
          Your Exploration Summary
        </h1>
        <p className="text-sm text-white/50 mb-6 text-center">
          Here&apos;s what we learned. {consultantName ? `${consultantName} will` : 'Your consultant will'} review this before your call.
        </p>

        <div className="space-y-3">
          {/* Confirmed */}
          {confirmed.length > 0 && (
            <div className="bg-white/10 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2.5">
                <CheckCircle className="w-4 h-4 text-brand-primary" />
                <span className="text-sm font-medium text-brand-primary">
                  Confirmed ({confirmed.length})
                </span>
              </div>
              <div className="space-y-2">
                {confirmed.map((item, i) => (
                  <div key={i} className="text-xs text-white/70">
                    <span className="text-white/40 text-[10px]">{item.epicTitle}:</span>{' '}
                    {item.text}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Needs Discussion */}
          {needsDiscussion.length > 0 && (
            <div className="bg-white/10 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2.5">
                <Pencil className="w-4 h-4 text-white/70" />
                <span className="text-sm font-medium text-white/70">
                  Needs Discussion ({needsDiscussion.length})
                </span>
              </div>
              <div className="space-y-2">
                {needsDiscussion.map((item, i) => (
                  <div key={i} className="text-xs text-white/70">
                    <span className="text-white/40 text-[10px]">{item.epicTitle}:</span>{' '}
                    {item.text}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Escalated */}
          {escalated.length > 0 && (
            <div className="bg-white/10 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2.5">
                <HelpCircle className="w-4 h-4 text-white/50" />
                <span className="text-sm font-medium text-white/50">
                  Questions for {consultantName || 'Consultant'} ({escalated.length})
                </span>
              </div>
              <div className="space-y-2">
                {escalated.map((item, i) => (
                  <div key={i} className="text-xs text-white/70">
                    <span className="text-white/40 text-[10px]">{item.epicTitle}:</span>{' '}
                    {item.text}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Nothing reviewed */}
          {confirmed.length === 0 && needsDiscussion.length === 0 && escalated.length === 0 && (
            <div className="bg-white/10 rounded-xl p-4 text-center">
              <p className="text-sm text-white/50">
                No assumptions reviewed yet — that&apos;s okay! Your consultant will walk through everything on the call.
              </p>
            </div>
          )}

          {skippedCount > 0 && (
            <p className="text-xs text-white/30 text-center">
              {skippedCount} assumption{skippedCount !== 1 ? 's' : ''} skipped — totally fine
            </p>
          )}
        </div>

        {/* Booking CTA */}
        <div className="mt-6 space-y-3">
          {bookingUrl && (
            <a
              href={bookingUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full px-6 py-3.5 bg-brand-primary text-white text-base font-medium rounded-xl hover:bg-brand-primary-hover transition-all shadow-lg shadow-brand-primary/25"
            >
              <Calendar className="w-5 h-5" />
              Book Discovery Call{consultantName ? ` with ${consultantName}` : ''}
              <ArrowRight className="w-4 h-4" />
            </a>
          )}

          <button
            onClick={onComplete}
            disabled={isSubmitting}
            className={`w-full px-6 py-3 text-sm font-medium rounded-xl transition-all disabled:opacity-50 ${
              bookingUrl
                ? 'bg-white/10 text-white/70 hover:bg-white/20'
                : 'bg-brand-primary text-white hover:bg-brand-primary-hover shadow-lg shadow-brand-primary/25'
            }`}
          >
            {isSubmitting ? 'Finishing...' : "I'm Done"}
          </button>
        </div>

        <p className="mt-4 text-xs text-white/30 text-center">
          Your consultant will review these results before your call
        </p>
      </div>
    </div>
  )
}
