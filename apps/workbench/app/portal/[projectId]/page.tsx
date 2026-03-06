/**
 * Client Portal Hub — Mission Control Dashboard
 *
 * Two-column layout:
 * Left: inline action cards (questions, validations)
 * Right: contribution station grid, prototype card, activity timeline
 */

'use client'

import { useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Monitor, Zap, ChevronDown, ChevronUp, Swords, Palette, ShieldAlert, FileText, Sparkles, BookOpen } from 'lucide-react'
import { Spinner } from '@/components/ui/Spinner'
import { usePortal } from './PortalShell'
import { ConsultantBanner } from '@/components/portal/ConsultantBanner'
import { InlineActionCard } from '@/components/portal/InlineActionCard'
import { ContributionGrid } from '@/components/portal/ContributionGrid'
import { ActivityTimeline } from '@/components/portal/ActivityTimeline'
import { StationPanel } from '@/components/portal/StationPanel'
import type { StationSlug } from '@/types/portal'

// Station metadata for StationPanel
const STATION_META: Record<StationSlug, {
  icon: React.ComponentType<{ className?: string }>
  title: string
  entityLabel: string
  greeting: string
}> = {
  competitors: {
    icon: Swords,
    title: 'Competitors & Past Tools',
    entityLabel: 'Competitive Landscape',
    greeting: "Let's talk about the tools you've used before and what else is out there. What have you tried?",
  },
  design: {
    icon: Palette,
    title: 'Design Inspiration',
    entityLabel: 'Design Preferences',
    greeting: "I'd love to hear about apps and tools you enjoy using. What stands out to you?",
  },
  constraints: {
    icon: ShieldAlert,
    title: 'Constraints & Requirements',
    entityLabel: 'Business Constraints',
    greeting: "Let's document any hard constraints — compliance, budget, technical limitations, or non-negotiables.",
  },
  documents: {
    icon: FileText,
    title: 'Supporting Documents',
    entityLabel: 'Materials',
    greeting: 'Do you have any existing documentation, screenshots, or data that would help? You can upload files above.',
  },
  ai_wishlist: {
    icon: Sparkles,
    title: 'AI & Automation Wishlist',
    entityLabel: 'AI Features',
    greeting: "What tasks would you love to automate? What would AI magic look like for your workflow?",
  },
  tribal: {
    icon: BookOpen,
    title: 'Tribal Knowledge',
    entityLabel: 'Edge Cases & Gotchas',
    greeting: "Let's capture the things only experienced people know — gotchas, edge cases, and undocumented rules.",
  },
  epic: {
    icon: Monitor,
    title: 'Epic Review',
    entityLabel: 'Prototype',
    greeting: "Let's discuss what you see in the prototype. What stands out?",
  },
}

export default function PortalHubPage() {
  const router = useRouter()
  const {
    projectId,
    dashboard,
    loaded,
    infoRequests,
    refreshInfoRequests,
    validationQueue,
    refreshValidation,
    projectContext,
    refreshContext,
  } = usePortal()

  const [activeStation, setActiveStation] = useState<StationSlug | null>(null)
  const [showCompleted, setShowCompleted] = useState(false)

  const handleDataChanged = useCallback(() => {
    refreshContext()
    refreshInfoRequests()
  }, [refreshContext, refreshInfoRequests])

  if (!loaded) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" label="Loading dashboard..." />
      </div>
    )
  }

  if (!dashboard) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-red-600 mb-2">Failed to load dashboard</p>
          <button
            onClick={() => window.location.reload()}
            className="text-sm text-brand-primary hover:underline"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // Split info requests
  const pendingQuestions = infoRequests.filter(
    (q) => q.status !== 'complete' && q.status !== 'skipped'
  )
  const completedQuestions = infoRequests.filter(
    (q) => q.status === 'complete' || q.status === 'skipped'
  )

  // Pending validations
  const pendingValidations = validationQueue?.items ?? []

  const { prototype_status, recent_activity } = dashboard
  const hasActions = pendingQuestions.length > 0 || pendingValidations.length > 0

  return (
    <div className="space-y-6">
      {/* Consultant Banner */}
      <ConsultantBanner dashboard={dashboard} projectContext={projectContext} />

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left: Actions */}
        <div className="lg:col-span-3 space-y-3">
          {/* Pending questions */}
          {pendingQuestions.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-medium text-text-muted uppercase tracking-wide">
                Questions ({pendingQuestions.length})
              </h2>
              {pendingQuestions.slice(0, 5).map((q) => (
                <InlineActionCard
                  key={q.id}
                  type="question"
                  item={q}
                  onCompleted={() => {
                    refreshInfoRequests()
                    refreshContext()
                  }}
                />
              ))}
              {pendingQuestions.length > 5 && (
                <p className="text-xs text-text-muted text-center">
                  +{pendingQuestions.length - 5} more questions
                </p>
              )}
            </div>
          )}

          {/* Pending validations */}
          {pendingValidations.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-xs font-medium text-text-muted uppercase tracking-wide">
                Validations ({pendingValidations.length})
              </h2>
              {pendingValidations.slice(0, 5).map((v) => (
                <InlineActionCard
                  key={v.id}
                  type="validation"
                  item={v}
                  projectId={projectId}
                  onCompleted={refreshValidation}
                />
              ))}
              {pendingValidations.length > 5 && (
                <p className="text-xs text-text-muted text-center">
                  +{pendingValidations.length - 5} more validations
                </p>
              )}
            </div>
          )}

          {/* Completed items (collapsed) */}
          {completedQuestions.length > 0 && (
            <div>
              <button
                onClick={() => setShowCompleted(!showCompleted)}
                className="flex items-center gap-1 text-xs text-text-muted hover:text-text-body transition-colors"
              >
                {showCompleted ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                {completedQuestions.length} completed
              </button>
              {showCompleted && (
                <div className="mt-2 space-y-1">
                  {completedQuestions.map((q) => (
                    <div key={q.id} className="text-xs text-text-muted flex items-center gap-1.5 py-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-400 flex-shrink-0" />
                      {q.title}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Empty state for actions */}
          {!hasActions && completedQuestions.length === 0 && (
            <div className="text-center py-8">
              <Zap className="w-8 h-8 text-text-placeholder mx-auto mb-2" />
              <p className="text-sm text-text-muted">
                No pending items. Contribute context using the stations on the right.
              </p>
            </div>
          )}
        </div>

        {/* Right: Contribute + Status */}
        <div className="lg:col-span-2 space-y-4">
          {/* Contribution Grid */}
          <div>
            <h2 className="text-xs font-medium text-text-muted uppercase tracking-wide mb-3">
              Contribute
            </h2>
            <ContributionGrid
              projectContext={projectContext}
              dashboard={dashboard}
              onStationOpen={setActiveStation}
            />
          </div>

          {/* Prototype Card */}
          {prototype_status && (
            <button
              onClick={() => router.push(`/portal/${projectId}/prototype`)}
              className="w-full bg-surface-card border border-border rounded-lg p-4 text-left hover:border-brand-primary hover:shadow-sm transition-all"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-[#0A1E2F] flex items-center justify-center flex-shrink-0">
                  <Monitor className="w-5 h-5 text-white" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text-primary">
                    {prototype_status.status === 'deployed' ? 'Prototype Ready' : 'Prototype'}
                  </p>
                  <p className="text-xs text-brand-primary">
                    {prototype_status.deploy_url ? 'Click to review' : prototype_status.status}
                  </p>
                </div>
              </div>
            </button>
          )}

          {/* Activity Timeline */}
          <ActivityTimeline activities={recent_activity} />
        </div>
      </div>

      {/* Station Panel */}
      {activeStation && STATION_META[activeStation] && (
        <StationPanel
          onClose={() => setActiveStation(null)}
          icon={STATION_META[activeStation].icon}
          title={STATION_META[activeStation].title}
          entityLabel={STATION_META[activeStation].entityLabel}
          progress={
            projectContext?.completion_scores?.[
              activeStation === 'ai_wishlist' || activeStation === 'constraints' || activeStation === 'epic'
                ? 'tribal'
                : (activeStation as keyof typeof projectContext.completion_scores)
            ] ?? 0
          }
          station={activeStation}
          projectId={projectId}
          chatGreeting={STATION_META[activeStation].greeting}
          onDataChanged={handleDataChanged}
        />
      )}
    </div>
  )
}
