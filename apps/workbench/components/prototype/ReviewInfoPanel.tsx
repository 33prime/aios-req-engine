'use client'

import { useState, useCallback } from 'react'
import { Check, RefreshCw, Users, ChevronRight, MessageCircle, HelpCircle } from 'lucide-react'
import { submitEpicVerdict } from '@/lib/api'
import { useSWRConfig } from 'swr'
import type {
  EpicOverlayPlan,
  EpicTourPhase,
  EpicCardType,
  EpicVerdict,
  EpicConfirmation,
} from '@/types/epic-overlay'

interface ReviewInfoPanelProps {
  epicPlan: EpicOverlayPlan
  epicPhase: EpicTourPhase
  epicCardIndex: number
  sessionId: string
  confirmations: EpicConfirmation[]
  onAdvance: () => void
}

/** Maps tour phase to card_type for the DB */
const PHASE_TO_CARD_TYPE: Record<EpicTourPhase, EpicCardType> = {
  vision_journey: 'vision',
  ai_deep_dive: 'ai_flow',
  horizons: 'horizon',
  discovery: 'discovery',
}

export default function ReviewInfoPanel({
  epicPlan,
  epicPhase,
  epicCardIndex,
  sessionId,
  confirmations,
  onAdvance,
}: ReviewInfoPanelProps) {
  const { mutate } = useSWRConfig()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [refineNotes, setRefineNotes] = useState('')
  const [discoveryAnswer, setDiscoveryAnswer] = useState('')
  const [selectedVerdict, setSelectedVerdict] = useState<EpicVerdict | null>(null)

  const cardType = PHASE_TO_CARD_TYPE[epicPhase]

  // Compute the index within the phase from the global epicCardIndex
  const phaseCardIndex = getPhaseLocalIndex(epicPlan, epicPhase, epicCardIndex)

  // Find existing confirmation
  const existing = confirmations.find(
    (c) => c.card_type === cardType && c.card_index === phaseCardIndex && c.source === 'consultant'
  )

  const handleSubmitVerdict = useCallback(
    async (verdict: EpicVerdict) => {
      setIsSubmitting(true)
      try {
        await submitEpicVerdict(sessionId, {
          card_type: cardType,
          card_index: phaseCardIndex,
          verdict,
          notes: verdict === 'refine' ? refineNotes || null : null,
          source: 'consultant',
        })
        await mutate(`epic-verdicts:${sessionId}`)
        setSelectedVerdict(null)
        setRefineNotes('')
        onAdvance()
      } catch (err) {
        console.error('Failed to submit verdict:', err)
      } finally {
        setIsSubmitting(false)
      }
    },
    [sessionId, cardType, phaseCardIndex, refineNotes, mutate, onAdvance]
  )

  const handleSubmitAnswer = useCallback(
    async (answerText: string | null) => {
      setIsSubmitting(true)
      try {
        await submitEpicVerdict(sessionId, {
          card_type: 'discovery',
          card_index: phaseCardIndex,
          verdict: null,
          answer: answerText,
          source: 'consultant',
        })
        await mutate(`epic-verdicts:${sessionId}`)
        setDiscoveryAnswer('')
        onAdvance()
      } catch (err) {
        console.error('Failed to submit answer:', err)
      } finally {
        setIsSubmitting(false)
      }
    },
    [sessionId, phaseCardIndex, mutate, onAdvance]
  )

  // Render per phase type
  if (epicPhase === 'vision_journey') {
    const epic = epicPlan.vision_epics[phaseCardIndex]
    if (!epic) return <EmptyState />

    return (
      <div className="p-4 space-y-3">
        <h3 className="text-base font-semibold text-[#37352f]">{epic.title}</h3>
        <p className="text-[13px] text-[#666666] leading-relaxed">
          {epic.narrative}
        </p>

        {/* Feature chips */}
        {epic.features.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {epic.features.slice(0, 4).map((f) => (
              <span
                key={f.feature_id}
                className="text-[10px] px-2 py-0.5 rounded-full border border-border text-[#666666] bg-[#F8F8F8]"
              >
                {f.name}
              </span>
            ))}
            {epic.features.length > 4 && (
              <span className="text-[10px] text-text-placeholder">
                +{epic.features.length - 4}
              </span>
            )}
          </div>
        )}

        {/* Key question */}
        {epic.open_questions.length > 0 && (
          <div className="border-t border-border pt-3">
            <div className="text-[11px] font-medium text-[#666666] mb-1 flex items-center gap-1">
              <MessageCircle className="w-3 h-3" />
              Key Question
            </div>
            <p className="text-[13px] text-[#37352f] italic">
              &ldquo;{epic.open_questions[0]}&rdquo;
            </p>
          </div>
        )}

        <VerdictButtons
          existing={existing}
          selectedVerdict={selectedVerdict}
          onSelect={setSelectedVerdict}
          onSubmit={handleSubmitVerdict}
          isSubmitting={isSubmitting}
          refineNotes={refineNotes}
          onNotesChange={setRefineNotes}
        />
      </div>
    )
  }

  if (epicPhase === 'ai_deep_dive') {
    const card = epicPlan.ai_flow_cards[phaseCardIndex]
    if (!card) return <EmptyState />

    return (
      <div className="p-4 space-y-3">
        <h3 className="text-base font-semibold text-[#37352f]">{card.title}</h3>
        <p className="text-[13px] text-[#666666] leading-relaxed">
          {card.narrative}
        </p>

        {/* Compact 4-section */}
        <div className="grid grid-cols-2 gap-2">
          <MiniSection label="Data In" items={card.data_in} />
          <MiniSection label="AI Does" items={card.behaviors} />
          <MiniSection label="Guardrails" items={card.guardrails} />
          <div className="rounded-lg bg-[#F0FAF4] p-2">
            <div className="text-[10px] font-semibold text-brand-primary uppercase tracking-wide mb-0.5">
              Output
            </div>
            <p className="text-[11px] text-[#37352f]">{card.output || 'AI result'}</p>
          </div>
        </div>

        <VerdictButtons
          existing={existing}
          selectedVerdict={selectedVerdict}
          onSelect={setSelectedVerdict}
          onSubmit={handleSubmitVerdict}
          isSubmitting={isSubmitting}
          refineNotes={refineNotes}
          onNotesChange={setRefineNotes}
        />
      </div>
    )
  }

  if (epicPhase === 'horizons') {
    const card = epicPlan.horizon_cards[phaseCardIndex]
    if (!card) return <EmptyState />

    const horizonColor =
      card.horizon === 1 ? 'text-brand-primary' : card.horizon === 2 ? 'text-[#0A1E2F]' : 'text-[#666666]'
    const badgeColor =
      card.horizon === 1 ? 'bg-brand-primary text-white' : card.horizon === 2 ? 'bg-[#0A1E2F] text-white' : 'bg-[#666666] text-white'

    return (
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${badgeColor}`}>
            H{card.horizon}
          </span>
          <span className="text-[11px] font-medium text-[#666666]">
            {card.subtitle}
          </span>
        </div>
        <h3 className={`text-base font-semibold ${horizonColor}`}>{card.title}</h3>

        {card.unlock_summaries.length > 0 && (
          <div className="space-y-1">
            <div className="text-[11px] font-medium text-[#666666]">Unlocks</div>
            <ul className="space-y-0.5">
              {card.unlock_summaries.slice(0, 5).map((u, i) => (
                <li key={i} className="text-[13px] text-[#37352f] flex items-start gap-1.5">
                  <span className="text-[#666666] mt-0.5">&bull;</span>
                  {u}
                </li>
              ))}
            </ul>
          </div>
        )}

        {card.why_now.length > 0 && (
          <div className="border-t border-border pt-3 space-y-1">
            <div className="text-[11px] font-medium text-[#666666]">Why Now</div>
            {card.why_now.slice(0, 2).map((w, i) => (
              <p key={i} className="text-[13px] text-[#666666] italic">{w}</p>
            ))}
          </div>
        )}

        {/* Horizons are educational — just a Next button */}
        <button
          onClick={onAdvance}
          className="w-full flex items-center justify-center gap-1.5 px-4 py-2 bg-[#F4F4F4] text-[#37352f] text-[13px] font-medium rounded-xl hover:bg-[#EBEBEB] transition-colors"
        >
          Next
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    )
  }

  if (epicPhase === 'discovery') {
    const threads = epicPlan.discovery_threads.slice(0, 3)
    const thread = threads[phaseCardIndex]
    if (!thread) return <EmptyState />

    const existingAnswer = existing?.answer || ''

    // Smart questions: use thread.questions if they exist and look like real questions,
    // otherwise fall back to the theme as the anchor
    const smartQuestions = thread.questions.filter(
      (q) => q.length > 10 && (q.includes('?') || q.includes('how') || q.includes('what') || q.includes('why'))
    )

    return (
      <div className="p-4 space-y-3">
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded-md bg-[#F0FAF4] flex items-center justify-center">
            <HelpCircle className="w-3 h-3 text-brand-primary" />
          </div>
          <span className="text-[11px] font-medium text-[#666666]">Knowledge Gap</span>
          {thread.knowledge_type && (
            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-[#F4F4F4] text-[#666666]">
              {thread.knowledge_type}
            </span>
          )}
        </div>

        <h3 className="text-base font-semibold text-[#37352f]">{thread.theme}</h3>

        {/* Smart questions — framed as discussion points */}
        {smartQuestions.length > 0 ? (
          <div className="space-y-2">
            {smartQuestions.slice(0, 2).map((q, i) => (
              <div key={i} className="rounded-lg bg-[#F8FAF8] border border-border p-2.5">
                <p className="text-[13px] text-[#37352f] leading-relaxed">{q}</p>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-lg bg-[#F8FAF8] border border-border p-2.5">
            <p className="text-[13px] text-[#37352f] leading-relaxed">
              What do you know about <span className="font-medium">{thread.theme.toLowerCase()}</span>?
              {thread.features.length > 0 && (
                <span className="text-[#666666]">
                  {' '}This affects {thread.features.slice(0, 2).join(', ')}
                  {thread.features.length > 2 ? ` and ${thread.features.length - 2} more` : ''}.
                </span>
              )}
            </p>
          </div>
        )}

        {/* Speaker hints — who to ask */}
        {thread.speaker_hints.length > 0 && (
          <div className="flex items-center gap-1.5 text-[11px] text-[#666666]">
            <Users className="w-3 h-3 text-[#999]" />
            <span>
              Ask: {thread.speaker_hints.map((s) => s.name).join(', ')}
            </span>
          </div>
        )}

        {/* Answer input */}
        <div>
          <textarea
            value={discoveryAnswer || existingAnswer}
            onChange={(e) => setDiscoveryAnswer(e.target.value)}
            placeholder="Share what you know..."
            className="w-full px-3 py-2 text-[13px] border border-border rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
            rows={2}
          />
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => handleSubmitAnswer(discoveryAnswer || null)}
            disabled={isSubmitting || !discoveryAnswer.trim()}
            className="flex-1 px-4 py-2 bg-brand-primary text-white text-[13px] font-medium rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Saving...' : 'Submit'}
          </button>
          <button
            onClick={() => handleSubmitAnswer(null)}
            disabled={isSubmitting}
            className="px-4 py-2 text-[#666666] text-[13px] font-medium rounded-xl border border-border hover:bg-[#F4F4F4] transition-colors disabled:opacity-50"
          >
            Skip
          </button>
        </div>
      </div>
    )
  }

  return <EmptyState />
}

// ─── Verdict Buttons ────────────────────────────────────────────────

interface VerdictButtonsProps {
  existing: EpicConfirmation | undefined
  selectedVerdict: EpicVerdict | null
  onSelect: (v: EpicVerdict | null) => void
  onSubmit: (v: EpicVerdict) => void
  isSubmitting: boolean
  refineNotes: string
  onNotesChange: (v: string) => void
}

function VerdictButtons({
  existing,
  selectedVerdict,
  onSelect,
  onSubmit,
  isSubmitting,
  refineNotes,
  onNotesChange,
}: VerdictButtonsProps) {
  if (existing?.verdict) {
    // Already submitted — show status
    return (
      <div className="border-t border-border pt-3 space-y-2">
        <div className="flex items-center gap-2">
          {existing.verdict === 'confirmed' && (
            <span className="flex items-center gap-1.5 text-[13px] font-medium text-[#25785A]">
              <Check className="w-4 h-4" />
              Confirmed
            </span>
          )}
          {existing.verdict === 'refine' && (
            <span className="flex items-center gap-1.5 text-[13px] font-medium text-[#666666]">
              <RefreshCw className="w-4 h-4" />
              Flagged for Refinement
            </span>
          )}
          {existing.verdict === 'client_review' && (
            <span className="flex items-center gap-1.5 text-[13px] font-medium text-[#0A1E2F]">
              <Users className="w-4 h-4" />
              Client Review
            </span>
          )}
        </div>
        {existing.notes && (
          <p className="text-[12px] text-[#666666] pl-6">{existing.notes}</p>
        )}
      </div>
    )
  }

  return (
    <div className="border-t border-border pt-3 space-y-3">
      <div className="flex gap-2">
        <button
          onClick={() => onSubmit('confirmed')}
          disabled={isSubmitting}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-brand-primary text-white text-[13px] font-medium rounded-xl hover:bg-[#25785A] transition-colors disabled:opacity-50"
        >
          <Check className="w-3.5 h-3.5" />
          Confirm
        </button>
        <button
          onClick={() => onSelect(selectedVerdict === 'refine' ? null : 'refine')}
          disabled={isSubmitting}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-[13px] font-medium rounded-xl border transition-colors disabled:opacity-50 ${
            selectedVerdict === 'refine'
              ? 'border-[#0A1E2F] bg-[#F4F4F4] text-[#0A1E2F]'
              : 'border-border text-[#666666] hover:bg-[#F4F4F4]'
          }`}
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refine
        </button>
        <button
          onClick={() => onSubmit('client_review')}
          disabled={isSubmitting}
          className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 border border-border text-[#666666] text-[13px] font-medium rounded-xl hover:bg-[#F4F4F4] transition-colors disabled:opacity-50"
        >
          <Users className="w-3.5 h-3.5" />
          Client
        </button>
      </div>

      {/* Refine notes */}
      {selectedVerdict === 'refine' && (
        <div className="space-y-2">
          <textarea
            value={refineNotes}
            onChange={(e) => onNotesChange(e.target.value)}
            placeholder="What needs to change?"
            className="w-full px-3 py-2 text-[13px] border border-border rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
            rows={2}
            autoFocus
          />
          <button
            onClick={() => onSubmit('refine')}
            disabled={isSubmitting || !refineNotes.trim()}
            className="w-full px-4 py-2 bg-[#0A1E2F] text-white text-[13px] font-medium rounded-xl hover:bg-[#1a2e3f] transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Saving...' : 'Submit Refinement'}
          </button>
        </div>
      )}
    </div>
  )
}

// ─── Helpers ────────────────────────────────────────────────────────

function MiniSection({ label, items }: { label: string; items: string[] }) {
  return (
    <div className="rounded-lg bg-[#F8F8F8] p-2">
      <div className="text-[10px] font-semibold text-[#666666] uppercase tracking-wide mb-0.5">
        {label}
      </div>
      <ul className="space-y-0">
        {items.slice(0, 3).map((item, i) => (
          <li key={i} className="text-[11px] text-[#37352f] truncate">{item}</li>
        ))}
      </ul>
    </div>
  )
}

function EmptyState() {
  return (
    <div className="p-6 text-center">
      <p className="text-[13px] text-[#666666]">Navigating...</p>
    </div>
  )
}

/**
 * Converts a global card index (across all phases) to the local index within
 * the current phase. The EpicTourController flattens all cards into one list;
 * we need to reverse that mapping.
 */
function getPhaseLocalIndex(
  plan: EpicOverlayPlan,
  phase: EpicTourPhase,
  globalIndex: number
): number {
  let offset = 0
  const phaseSizes: [EpicTourPhase, number][] = [
    ['vision_journey', plan.vision_epics.length],
    ['ai_deep_dive', plan.ai_flow_cards.length],
    ['horizons', plan.horizon_cards.length],
    ['discovery', Math.min(plan.discovery_threads.length, 3)],
  ]
  for (const [p, size] of phaseSizes) {
    if (p === phase) {
      return globalIndex - offset
    }
    offset += size
  }
  return 0
}
