'use client'

import { useCallback } from 'react'
import { Loader2, Sparkles } from 'lucide-react'
import { useIntelligenceBriefing } from '@/lib/hooks/use-api'
import { PHASE_DESCRIPTIONS } from '@/lib/action-constants'

import { BriefingHeader } from './BriefingHeader'
import { SituationSummary } from './SituationSummary'
import { WhatChangedSection } from './WhatChangedSection'
import { ActiveTensionsSection } from './ActiveTensionsSection'
import { HypothesesSection } from './HypothesesSection'
import { TopActionsSection } from './TopActionsSection'
import { ProjectHeartbeatSection } from './ProjectHeartbeatSection'

interface IntelligenceBriefingPanelProps {
  projectId: string
  onNavigate?: (entityType: string, entityId: string | null) => void
  onCascade?: () => void
  onDiscussInChat?: (action: import('@/lib/api').TerseAction) => void
}

export function IntelligenceBriefingPanel({
  projectId,
  onNavigate,
  onCascade,
  onDiscussInChat,
}: IntelligenceBriefingPanelProps) {
  const {
    data: briefing,
    error: swrError,
    isLoading: loading,
    mutate: revalidate,
  } = useIntelligenceBriefing(projectId)

  const handleRefresh = useCallback(() => {
    revalidate()
  }, [revalidate])

  // Loading state
  if (loading && briefing === undefined) {
    return (
      <div className="flex flex-col h-full">
        <BriefingHeader phase={null} progress={0} />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="flex items-center gap-2 text-[12px] text-[#999999]">
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
      <div className="flex flex-col h-full">
        <BriefingHeader phase={null} progress={0} />
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center">
            <p className="text-[12px] text-[#999999]">Failed to load briefing</p>
            <button
              onClick={handleRefresh}
              className="mt-2 text-[11px] font-medium text-[#3FAF7A] hover:underline"
            >
              Try again
            </button>
          </div>
        </div>
      </div>
    )
  }

  const phase = briefing?.phase ?? 'empty'
  const progress = briefing?.situation?.phase_progress ?? 0
  const hasContent = briefing && (
    briefing.situation.narrative ||
    briefing.what_changed.changes.length > 0 ||
    briefing.tensions.length > 0 ||
    briefing.hypotheses.length > 0 ||
    briefing.actions.length > 0
  )

  return (
    <div className="flex flex-col h-full bg-white border-r border-[#E5E5E5]">
      <BriefingHeader
        phase={phase}
        progress={progress}
        narrativeCached={briefing?.narrative_cached}
        onRefresh={handleRefresh}
        loading={loading}
      />

      {/* Scrollable sections */}
      <div className="flex-1 overflow-y-auto">
        {!hasContent ? (
          <PhaseEmptyState phase={phase} />
        ) : (
          <>
            {/* Situation + What You Should Know */}
            {briefing && (
              <SituationSummary
                situation={briefing.situation}
                whatYouShouldKnow={briefing.what_you_should_know}
              />
            )}

            {/* What Changed */}
            {briefing && (
              <WhatChangedSection whatChanged={briefing.what_changed} />
            )}

            {/* Active Tensions */}
            {briefing && briefing.tensions.length > 0 && (
              <ActiveTensionsSection tensions={briefing.tensions} />
            )}

            {/* Hypotheses */}
            {briefing && briefing.hypotheses.length > 0 && (
              <HypothesesSection
                hypotheses={briefing.hypotheses}
                projectId={projectId}
              />
            )}

            {/* Next Actions */}
            {briefing && briefing.actions.length > 0 && (
              <TopActionsSection
                projectId={projectId}
                actions={briefing.actions}
                onNavigate={onNavigate}
                onCascade={onCascade}
                onRefresh={handleRefresh}
                onDiscussInChat={onDiscussInChat}
              />
            )}

            {/* Heartbeat */}
            {briefing && (
              <ProjectHeartbeatSection heartbeat={briefing.heartbeat} />
            )}
          </>
        )}
      </div>
    </div>
  )
}

function PhaseEmptyState({ phase }: { phase: string }) {
  const description = PHASE_DESCRIPTIONS[phase] || 'No intelligence available yet'

  return (
    <div className="p-6 text-center">
      <Sparkles className="w-8 h-8 text-[#3FAF7A] mx-auto mb-3 opacity-50" />
      <p className="text-[13px] font-medium text-[#333333]">
        {phase === 'refining' ? 'Looking good' : 'Ready when you are'}
      </p>
      <p className="text-[12px] text-[#999999] mt-1">{description}</p>
    </div>
  )
}
