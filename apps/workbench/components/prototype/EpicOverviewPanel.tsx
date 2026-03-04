'use client'

import { useState, useCallback, useEffect, useRef, useMemo } from 'react'
import {
  Check,
  PenLine,
  Flag,
  Lock,
  CheckCircle2,
  ArrowRight,
  ExternalLink,
  ChevronDown,
} from 'lucide-react'
import type {
  Epic,
  EpicConfirmation,
  EpicVerdict,
  EpicFeature,
} from '@/types/epic-overlay'

// ---------------------------------------------------------------------------
// Narrative parser — splits the raw LLM narrative into structured sections
// ---------------------------------------------------------------------------
interface NarrativeSections {
  blockquote: string
  speaker: string
  body: string
}

function splitNarrative(
  narrative: string,
  personaNames: string[]
): NarrativeSections {
  const sentences =
    narrative.match(/[^.!?]+[.!?]+\s*/g)?.map((s) => s.trim()) || [narrative]

  let blockquote = ''
  let speaker = ''
  const body: string[] = []

  for (const s of sentences) {
    // First sentence with a name reference → blockquote
    if (!blockquote) {
      const persona = personaNames.find((p) => {
        const first = p.split(' ')[0]
        return s.includes(first) || s.includes(p)
      })
      if (
        persona ||
        /told us|shared that|mentioned that|in (?:her|his|their) (?:interview|call)/i.test(
          s
        )
      ) {
        blockquote = s
        const nameMatch = s.match(
          /^(\w+)\s+(?:told|shared|mentioned|said|explained)/i
        )
        speaker = nameMatch?.[1] || persona || ''
        continue
      }
    }

    body.push(s)
  }

  return {
    blockquote,
    speaker,
    body: body.slice(0, 2).join(' '),
  }
}

// ---------------------------------------------------------------------------
// Feature status helpers
// ---------------------------------------------------------------------------
function featureStatusColor(status: EpicFeature['implementation_status']) {
  if (status === 'functional') return 'bg-brand-primary'
  if (status === 'partial') return 'bg-yellow-500'
  return 'bg-gray-300'
}

function featureStatusLabel(status: EpicFeature['implementation_status']) {
  if (status === 'functional') return 'Functional'
  if (status === 'partial') return 'Partial'
  return 'Placeholder'
}

// ---------------------------------------------------------------------------
// FeatureCard — expandable card for a single feature
// ---------------------------------------------------------------------------
function FeatureCard({
  feature,
  isExpanded,
  isOnCurrentPage,
  painPoints,
  onToggle,
  onNavigate,
}: {
  feature: EpicFeature
  isExpanded: boolean
  isOnCurrentPage: boolean
  painPoints: string[]
  onToggle: () => void
  onNavigate?: () => void
}) {
  const cardRef = useRef<HTMLDivElement>(null)

  // Scroll expanded card into view
  useEffect(() => {
    if (isExpanded && cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [isExpanded])

  return (
    <div
      ref={cardRef}
      className={`
        rounded-lg border transition-all duration-300 overflow-hidden
        ${
          isExpanded
            ? 'border-[#044159] bg-[#044159]/[0.03] shadow-sm'
            : 'border-gray-100 hover:border-gray-200 hover:bg-gray-50/50'
        }
      `}
    >
      {/* Collapsed row — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 px-2.5 py-2 text-left"
      >
        {feature.implementation_status !== 'placeholder' && (
          <span
            className={`w-2 h-2 rounded-full shrink-0 ${featureStatusColor(
              feature.implementation_status
            )}`}
          />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-[12px] text-[#37352f] font-medium truncate">
            {feature.name}
          </p>
        </div>
        <ChevronDown
          className={`w-3 h-3 text-[#999] transition-transform duration-200 ${
            isExpanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="px-2.5 pb-2.5 space-y-2.5 animate-in fade-in slide-in-from-top-1 duration-200">
          <div className="border-t border-[#044159]/10 pt-2" />

          {/* Description */}
          {feature.description && (
            <p className="text-[11px] text-[#555] leading-snug">
              {feature.description}
            </p>
          )}

          {/* Status + Route (hide status label for placeholders — implementation noise) */}
          <div className="flex items-center gap-3">
            {feature.implementation_status !== 'placeholder' && (
              <div className="flex items-center gap-1.5">
                <span
                  className={`w-1.5 h-1.5 rounded-full ${featureStatusColor(
                    feature.implementation_status
                  )}`}
                />
                <span className="text-[10px] text-[#666]">
                  {featureStatusLabel(feature.implementation_status)}
                </span>
              </div>
            )}
            {feature.route && (
              <span className="text-[10px] text-[#999] flex items-center gap-1">
                {isOnCurrentPage ? (
                  <span className="text-brand-primary">on this page</span>
                ) : (
                  <>
                    <ExternalLink className="w-2.5 h-2.5" />
                    {feature.route}
                  </>
                )}
              </span>
            )}
          </div>

          {/* Pain point context (first one that fits) */}
          {painPoints.length > 0 && (
            <div className="flex items-start gap-1.5">
              <span className="mt-1.5 w-1 h-1 rounded-full bg-red-400 shrink-0" />
              <p className="text-[10px] text-[#666] leading-snug italic break-words">
                {painPoints[0]}
              </p>
            </div>
          )}

          {/* Navigate button for features on other pages */}
          {!isOnCurrentPage && onNavigate && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onNavigate()
              }}
              className="flex items-center gap-1.5 text-[10px] font-medium text-[#044159] hover:text-[#0a8a7b] transition-colors"
            >
              Navigate to {feature.route}
              <ArrowRight className="w-3 h-3" />
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// EpicOverviewPanel
// ---------------------------------------------------------------------------
interface EpicOverviewPanelProps {
  epic: Epic
  epicIndex: number
  sessionId: string
  confirmation?: EpicConfirmation | null
  onSubmitVerdict: (verdict: EpicVerdict, notes?: string) => Promise<void>
  /** Slug of feature highlighted by radar dot click */
  highlightedFeatureSlug?: string | null
  /** Called when user clicks a feature card to navigate to its page */
  onFeatureNavigate?: (feature: EpicFeature) => void
  /** The current route the iframe is on */
  currentRoute?: string | null
}

export default function EpicOverviewPanel({
  epic,
  epicIndex,
  confirmation,
  onSubmitVerdict,
  highlightedFeatureSlug,
  onFeatureNavigate,
  currentRoute,
}: EpicOverviewPanelProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [showRefineInput, setShowRefineInput] = useState(false)
  const [refineNotes, setRefineNotes] = useState('')
  // Track which feature is expanded (by slug)
  const [expandedSlug, setExpandedSlug] = useState<string | null>(null)

  const isLocked = !!confirmation?.verdict

  // Parse narrative into structured sections
  const sections = useMemo(
    () => splitNarrative(epic.narrative, epic.persona_names),
    [epic.narrative, epic.persona_names]
  )

  // Use provenance quotes if available, otherwise use parsed blockquote
  const heroQuote = useMemo(() => {
    if (epic.provenance_quotes?.length) {
      const q = epic.provenance_quotes[0]
      return {
        text: q.quote_text,
        speaker: q.speaker_name,
        source: q.source_label,
      }
    }
    if (sections.blockquote) {
      return { text: sections.blockquote, speaker: sections.speaker, source: null }
    }
    return null
  }, [epic.provenance_quotes, sections])

  // Use theme as the concise body, falling back to parsed sentences
  const bodyText = epic.theme || sections.body

  // When a radar dot is clicked, auto-expand that feature card
  useEffect(() => {
    if (highlightedFeatureSlug) {
      setExpandedSlug(highlightedFeatureSlug)
    }
  }, [highlightedFeatureSlug])

  // Reset expanded state when epic changes
  useEffect(() => {
    setExpandedSlug(null)
  }, [epicIndex])

  const handleVerdict = useCallback(
    async (verdict: EpicVerdict, notes?: string) => {
      setIsSubmitting(true)
      try {
        await onSubmitVerdict(verdict, notes)
        setShowRefineInput(false)
        setRefineNotes('')
      } finally {
        setIsSubmitting(false)
      }
    },
    [onSubmitVerdict]
  )

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* ── Header ── */}
      <div className="px-4 pt-4 pb-1">
        <h3 className="text-[13px] font-semibold text-[#0A1E2F] leading-snug">
          {epic.title}
        </h3>
        {epic.persona_names.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1.5">
            {epic.persona_names.map((name) => (
              <span
                key={name}
                className="inline-flex items-center text-[10px] font-medium text-[#044159] bg-[#044159]/8 rounded px-1.5 py-0.5"
              >
                @{name}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* ── Divider ── */}
      <div className="mx-4 mt-2 border-t border-gray-100" />

      {/* ── Blockquote (persona insight or provenance) ── */}
      {heroQuote && (
        <div className="px-4 pt-3">
          <blockquote className="border-l-[3px] border-[#044159]/30 pl-3 py-1">
            <p className="text-[12px] text-[#37352f] leading-relaxed italic">
              &ldquo;{heroQuote.text}&rdquo;
            </p>
            {heroQuote.speaker && (
              <p className="text-[10px] text-[#666] mt-1 flex items-center gap-1">
                <span className="font-medium text-[#044159]">
                  @{heroQuote.speaker}
                </span>
                {heroQuote.source && (
                  <span className="text-[#999]">· {heroQuote.source}</span>
                )}
              </p>
            )}
          </blockquote>
        </div>
      )}

      {/* ── Body (theme or short narrative) ── */}
      <div className="px-4 pt-2.5 pb-1">
        <p className="text-[12px] text-[#37352f] leading-relaxed">{bodyText}</p>
      </div>

      {/* ── Pain Points (compact) ── */}
      {epic.pain_points?.length > 0 && (
        <div className="px-4 pt-2">
          <div className="space-y-1">
            {epic.pain_points.map((point, i) => (
              <div key={i} className="flex items-start gap-1.5">
                <span className="mt-1.5 w-1 h-1 rounded-full bg-red-400 shrink-0" />
                <p className="text-[11px] text-[#666] leading-snug">{point}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Resolved Decisions (structured) ── */}
      {epic.resolved_decisions && epic.resolved_decisions.length > 0 && (
        <div className="px-4 pt-2.5 space-y-2">
          {epic.resolved_decisions.map((d, i) => (
            <div key={i} className="flex items-start gap-2 bg-emerald-50 rounded-lg px-3 py-2 border border-emerald-100">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
              <div>
                <p className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wider">
                  Resolved
                </p>
                <p className="text-[11px] text-emerald-800 leading-snug mt-0.5">
                  {d.decision}
                </p>
                {d.source_reference && (
                  <p className="text-[10px] text-emerald-600 mt-0.5">
                    — {d.source_reference}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Features (expandable cards) ── */}
      {epic.features.length > 0 && (
        <div className="px-4 pt-3">
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] font-semibold text-[#666] uppercase tracking-wider">
              Features
            </p>
            <span className="text-[10px] text-[#999] tabular-nums">
              {epic.features.length}
            </span>
          </div>
          <div className="space-y-1.5">
            {epic.features.map((f) => {
              const slug = f.slug || f.feature_id
              const isOnCurrentPage =
                f.route === currentRoute || !currentRoute

              return (
                <FeatureCard
                  key={f.feature_id}
                  feature={f}
                  isExpanded={expandedSlug === slug}
                  isOnCurrentPage={isOnCurrentPage}
                  painPoints={epic.pain_points || []}
                  onToggle={() => {
                    const next = expandedSlug === slug ? null : slug
                    setExpandedSlug(next)
                    // When expanding, also highlight in prototype
                    if (next) onFeatureNavigate?.(f)
                  }}
                  onNavigate={() => onFeatureNavigate?.(f)}
                />
              )
            })}
          </div>
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1 min-h-4" />

      {/* ── Verdict Actions ── */}
      <div className="px-4 py-3 border-t border-border">
        {isLocked ? (
          <div className="flex items-center gap-2 text-xs">
            <Lock className="w-3 h-3 text-[#666]" />
            <span className="text-[#666]">
              Verdict:{' '}
              <span className="font-medium text-[#37352f] capitalize">
                {confirmation?.verdict}
              </span>
            </span>
            {confirmation?.notes && (
              <span className="text-[#999] truncate ml-1">
                — {confirmation.notes}
              </span>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {showRefineInput ? (
              <div className="space-y-2">
                <textarea
                  value={refineNotes}
                  onChange={(e) => setRefineNotes(e.target.value)}
                  placeholder="What needs to change?"
                  className="w-full text-xs border border-border rounded-lg px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-brand-primary"
                  rows={3}
                  autoFocus
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => handleVerdict('refine', refineNotes)}
                    disabled={!refineNotes.trim() || isSubmitting}
                    className="flex-1 px-3 py-1.5 bg-amber-500 text-white text-xs font-medium rounded-lg hover:bg-amber-600 disabled:opacity-50 transition-colors"
                  >
                    Submit Refinement
                  </button>
                  <button
                    onClick={() => {
                      setShowRefineInput(false)
                      setRefineNotes('')
                    }}
                    className="px-3 py-1.5 text-xs text-[#666] hover:text-[#37352f] transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex gap-2">
                <button
                  onClick={() => handleVerdict('confirmed')}
                  disabled={isSubmitting}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-brand-primary text-white text-xs font-medium rounded-lg hover:bg-[#25785A] disabled:opacity-50 transition-colors"
                >
                  <Check className="w-3 h-3" />
                  Confirm
                </button>
                <button
                  onClick={() => setShowRefineInput(true)}
                  disabled={isSubmitting}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 bg-amber-50 text-amber-700 text-xs font-medium rounded-lg hover:bg-amber-100 disabled:opacity-50 transition-colors border border-amber-200"
                >
                  <PenLine className="w-3 h-3" />
                  Refine
                </button>
                <button
                  onClick={() => handleVerdict('flag_for_client')}
                  disabled={isSubmitting}
                  className="flex items-center justify-center gap-1.5 px-3 py-1.5 bg-gray-50 text-[#666] text-xs font-medium rounded-lg hover:bg-gray-100 disabled:opacity-50 transition-colors border border-gray-200"
                  title="Flag for client discussion"
                >
                  <Flag className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
