'use client'

import { useState, useCallback, useRef } from 'react'
import { Loader2, Paperclip, Sparkles, RefreshCw } from 'lucide-react'
import { useIntelligenceBriefing } from '@/lib/hooks/use-api'
import { getIntelligenceBriefing } from '@/lib/api'
import { PHASE_LABELS } from '@/lib/action-constants'
import type { ConversationStarter } from '@/types/workspace'

import { ConversationStarterCard } from './ConversationStarterCard'

interface IntelligenceBriefingPanelProps {
  projectId: string
  onNavigate?: (entityType: string, entityId: string | null) => void
  onCascade?: () => void
  onStartConversation?: (starter: ConversationStarter) => void
  onUploadDocument?: () => void
}

/** Render inline markdown: **bold** and *italic* */
function InlineMarkdown({ text }: { text: string }) {
  const parts: Array<{ content: string; style: 'normal' | 'bold' | 'italic' }> = []
  let remaining = text

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/)
    const italicMatch = remaining.match(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/)
    const boldIdx = boldMatch?.index ?? Infinity
    const italicIdx = italicMatch?.index ?? Infinity

    if (boldIdx === Infinity && italicIdx === Infinity) {
      parts.push({ content: remaining, style: 'normal' })
      break
    }

    if (boldIdx <= italicIdx) {
      if (boldIdx > 0) parts.push({ content: remaining.slice(0, boldIdx), style: 'normal' })
      parts.push({ content: boldMatch![1], style: 'bold' })
      remaining = remaining.slice(boldIdx + boldMatch![0].length)
    } else {
      if (italicIdx > 0) parts.push({ content: remaining.slice(0, italicIdx), style: 'normal' })
      parts.push({ content: italicMatch![1], style: 'italic' })
      remaining = remaining.slice(italicIdx + italicMatch![0].length)
    }
  }

  return (
    <>
      {parts.map((p, i) => {
        if (p.style === 'bold') return <strong key={i} className="font-semibold">{p.content}</strong>
        if (p.style === 'italic') return <em key={i} className="italic">{p.content}</em>
        return <span key={i}>{p.content}</span>
      })}
    </>
  )
}

export function IntelligenceBriefingPanel({
  projectId,
  onNavigate,
  onCascade,
  onStartConversation,
  onUploadDocument,
}: IntelligenceBriefingPanelProps) {
  const {
    data: briefing,
    error: swrError,
    isLoading: loading,
    mutate: revalidate,
  } = useIntelligenceBriefing(projectId)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [showAllStarters, setShowAllStarters] = useState(false)

  const handleRefresh = useCallback(() => {
    revalidate(getIntelligenceBriefing(projectId, 5, true), { revalidate: false })
  }, [revalidate, projectId])

  const handleUploadClick = useCallback(() => {
    if (onUploadDocument) {
      onUploadDocument()
    } else {
      fileInputRef.current?.click()
    }
  }, [onUploadDocument])

  const phase = briefing?.phase ?? 'empty'
  const phaseLabel = PHASE_LABELS[phase] || phase
  const progress = briefing?.situation?.phase_progress ?? 0
  const progressPct = Math.round(progress * 100)

  // Loading state
  if (loading && briefing === undefined) {
    return (
      <div className="flex flex-col h-full bg-white border-r border-border">
        <MicroHeader phaseLabel="..." progressPct={0} loading />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="flex items-center gap-2 text-[12px] text-text-placeholder">
            <Loader2 className="w-4 h-4 animate-spin" />
            Preparing briefing...
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (swrError) {
    return (
      <div className="flex flex-col h-full bg-white border-r border-border">
        <MicroHeader phaseLabel="..." progressPct={0} />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <p className="text-[12px] text-text-placeholder">Failed to load briefing</p>
            <button
              onClick={handleRefresh}
              className="mt-2 text-[11px] font-medium text-brand-primary hover:underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    )
  }

  const narrative = briefing?.situation?.narrative ?? ''
  const whatChanged = briefing?.what_changed
  const whatYouShouldKnow = briefing?.what_you_should_know
  const starters = briefing?.conversation_starters ?? []
  const discoveryProbes = briefing?.discovery_probes ?? []
  const hasContent = narrative || starters.length > 0

  // Compute change delta count
  const changeDelta = whatChanged
    ? (whatChanged.counts.new_signals || 0) +
      (whatChanged.counts.beliefs_changed || 0) +
      (whatChanged.counts.entities_updated || 0) +
      (whatChanged.counts.new_facts || 0) +
      (whatChanged.counts.new_insights || 0)
    : 0

  // Merge probes into starters when fewer than 3 starters
  const mergedStarters: ConversationStarter[] = [...starters]
  if (mergedStarters.length < 3 && discoveryProbes.length > 0 && onStartConversation) {
    const probesAsStarters: ConversationStarter[] = discoveryProbes
      .slice(0, 3 - mergedStarters.length)
      .map((probe) => ({
        starter_id: probe.probe_id,
        hook: probe.context,
        question: probe.question,
        action_type: 'deep_dive' as const,
        anchors: [],
        chat_context: `Discovery probe: ${probe.why}`,
        topic_domain: probe.category,
        is_fallback: false,
        generated_at: null,
      }))
    mergedStarters.push(...probesAsStarters)
  }

  const maxVisible = 5
  const visibleStarters = showAllStarters ? mergedStarters : mergedStarters.slice(0, maxVisible)
  const hasMoreStarters = mergedStarters.length > maxVisible

  return (
    <div className="flex flex-col h-full bg-white border-r border-border">
      {/* MicroHeader */}
      <MicroHeader
        phaseLabel={phaseLabel}
        progressPct={progressPct}
        changeDelta={changeDelta > 0 ? changeDelta : undefined}
        sinceLabel={whatChanged?.since_label}
        onRefresh={handleRefresh}
        loading={loading}
      />

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {!hasContent ? (
          <PhaseEmptyState phase={phase} onUpload={handleUploadClick} />
        ) : (
          <>
            {/* Condensed narrative */}
            <div className="px-4 pt-4 pb-2">
              {/* Change summary prefix if exists */}
              {whatChanged?.change_summary && (
                <p className="text-[12px] text-[#666666] leading-relaxed mb-2">
                  {whatChanged.change_summary}
                </p>
              )}

              {/* Main narrative */}
              {narrative && (
                <p className="text-[13px] text-text-body leading-[1.6]">
                  <InlineMarkdown text={narrative} />
                </p>
              )}

              {/* WYSK as indented insight block */}
              {whatYouShouldKnow && (whatYouShouldKnow.narrative || whatYouShouldKnow.bullets.length > 0) && (
                <div className="mt-3 pl-3 border-l-2 border-[#3FAF7A]">
                  {whatYouShouldKnow.narrative && (
                    <p className="text-[12px] text-text-body leading-relaxed">
                      <InlineMarkdown text={whatYouShouldKnow.narrative} />
                    </p>
                  )}
                  {whatYouShouldKnow.bullets.length > 0 && (
                    <div className="mt-1.5 space-y-1">
                      {whatYouShouldKnow.bullets.map((bullet, i) => (
                        <p key={i} className="text-[12px] text-[#444444] leading-snug">
                          <InlineMarkdown text={bullet} />
                        </p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Conversation starters + merged probes */}
            {visibleStarters.length > 0 && onStartConversation && (
              <div className="mt-1 mx-4 mb-2 rounded-xl border border-border overflow-hidden bg-white">
                {visibleStarters.map((starter) => (
                  <ConversationStarterCard
                    key={starter.starter_id}
                    starter={starter}
                    onStartConversation={onStartConversation}
                  />
                ))}
              </div>
            )}

            {/* Show more toggle */}
            {hasMoreStarters && onStartConversation && (
              <div className="px-4 mb-2">
                <button
                  onClick={() => setShowAllStarters(!showAllStarters)}
                  className="text-[11px] font-medium text-brand-primary hover:underline"
                >
                  {showAllStarters ? 'Show less' : `Show ${mergedStarters.length - maxVisible} more`}
                </button>
              </div>
            )}

            {/* Upload document row */}
            <div className="px-4 pb-4">
              <button
                onClick={handleUploadClick}
                className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-[13px] text-[#666666] hover:text-text-body hover:bg-[#F8F8F8] transition-colors"
              >
                <Paperclip className="w-4 h-4 flex-shrink-0" />
                Upload a document
              </button>
            </div>
          </>
        )}
      </div>

      {/* Hidden file input fallback */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.xlsx,.pptx,.png,.jpg,.jpeg,.webp,.gif"
        className="hidden"
      />
    </div>
  )
}

/** Compact micro header — single line, replaces BriefingHeader */
function MicroHeader({
  phaseLabel,
  progressPct,
  changeDelta,
  sinceLabel,
  onRefresh,
  loading,
}: {
  phaseLabel: string
  progressPct: number
  changeDelta?: number
  sinceLabel?: string
  onRefresh?: () => void
  loading?: boolean
}) {
  return (
    <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border flex-shrink-0">
      {/* Phase badge */}
      <span className="text-[10px] uppercase font-semibold text-[#3FAF7A] tracking-wide">
        {phaseLabel}
      </span>

      <div className="flex-1" />

      {/* Score pill */}
      <span className="text-[10px] font-medium text-text-body bg-[#F5F5F5] px-2 py-0.5 rounded-full">
        {progressPct}%
      </span>

      {/* Delta count */}
      {changeDelta !== undefined && changeDelta > 0 && (
        <span className="text-[10px] text-[#3FAF7A] font-medium">
          +{changeDelta}{sinceLabel ? ` since ${sinceLabel}` : ''}
        </span>
      )}

      {/* Refresh */}
      {onRefresh && (
        <button
          onClick={onRefresh}
          disabled={loading}
          className="p-1 rounded-md hover:bg-[#F5F5F5] transition-colors disabled:opacity-40"
          title="Refresh briefing"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 text-text-placeholder ${loading ? 'animate-spin' : ''}`}
          />
        </button>
      )}
    </div>
  )
}

function PhaseEmptyState({ phase, onUpload }: { phase: string; onUpload: () => void }) {
  const descriptions: Record<string, string> = {
    empty: 'Tell us about the project to get started',
    seeding: 'Upload documents or describe the current process',
    building: 'Fill in the details to strengthen the BRD',
    refining: 'Almost there — confirm and polish',
  }
  const description = descriptions[phase] || 'No intelligence available yet'

  return (
    <div className="p-6 text-center">
      <Sparkles className="w-8 h-8 text-brand-primary mx-auto mb-3 opacity-50" />
      <p className="text-[13px] font-medium text-text-body">
        {phase === 'refining' ? 'Looking good' : 'Ready when you are'}
      </p>
      <p className="text-[12px] text-text-placeholder mt-1 mb-4">{description}</p>
      <button
        onClick={onUpload}
        className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-[12px] font-medium text-brand-primary border border-brand-primary hover:bg-[#E8F5E9] transition-colors"
      >
        <Paperclip className="w-3.5 h-3.5" />
        Upload a document
      </button>
    </div>
  )
}
