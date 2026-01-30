/**
 * VpStepDetailDrawer - Right-slide drawer for VP step details
 *
 * Opens when clicking a journey step card in the canvas.
 * Single scrollable view with sections for narratives, features, enrichment.
 */

'use client'

import { useState, useEffect } from 'react'
import {
  X,
  User,
  CheckCircle,
  AlertCircle,
  Workflow,
  BookOpen,
  Monitor,
  Plug,
  ShieldCheck,
} from 'lucide-react'
import { getVpSteps } from '@/lib/api'
import type { CanvasData } from '@/types/workspace'

interface VpStepDetailDrawerProps {
  stepId: string
  projectId: string
  canvasData: CanvasData
  onClose: () => void
}

function getStatusBadge(status?: string | null) {
  switch (status) {
    case 'confirmed_client':
      return { label: 'Client Confirmed', color: 'bg-green-100 text-green-700', icon: CheckCircle }
    case 'confirmed_consultant':
      return { label: 'Confirmed', color: 'bg-blue-100 text-blue-700', icon: CheckCircle }
    case 'needs_client':
    case 'needs_confirmation':
      return { label: 'Needs Review', color: 'bg-amber-100 text-amber-700', icon: AlertCircle }
    default:
      return { label: 'AI Generated', color: 'bg-gray-100 text-gray-600', icon: AlertCircle }
  }
}

export function VpStepDetailDrawer({
  stepId,
  projectId,
  canvasData,
  onClose,
}: VpStepDetailDrawerProps) {
  const [fullStep, setFullStep] = useState<any | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Get summary from canvas data
  const summaryStep = canvasData.vp_steps.find((s) => s.id === stepId)

  useEffect(() => {
    setIsLoading(true)
    getVpSteps(projectId)
      .then((steps) => {
        const found = steps.find((s: any) => s.id === stepId)
        setFullStep(found || null)
      })
      .catch(() => setFullStep(null))
      .finally(() => setIsLoading(false))
  }, [projectId, stepId])

  const step = fullStep || summaryStep
  const statusBadge = getStatusBadge(step?.confirmation_status)
  const StatusBadgeIcon = statusBadge.icon
  const enrichment = fullStep?.enrichment || {}

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-[560px] max-w-[calc(100vw-80px)] bg-white shadow-xl z-50 flex flex-col animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-ui-cardBorder">
          <div className="flex items-center gap-3 min-w-0">
            <span className="flex items-center justify-center w-10 h-10 rounded-full bg-brand-teal text-white text-sm font-bold flex-shrink-0">
              {step?.step_index != null ? step.step_index + 1 : '?'}
            </span>
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-ui-headingDark truncate">
                {step?.title || 'Loading...'}
              </h2>
              {step?.actor_persona_name && (
                <div className="flex items-center gap-1 mt-0.5">
                  <User className="w-3 h-3 text-ui-supportText" />
                  <span className="text-sm text-ui-supportText">{step.actor_persona_name}</span>
                </div>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${statusBadge.color}`}>
              <StatusBadgeIcon className="w-3 h-3" />
              {statusBadge.label}
            </span>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-ui-supportText hover:bg-ui-background hover:text-ui-headingDark transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-teal" />
            </div>
          ) : (
            <>
              {/* Description */}
              {step?.description && (
                <Section icon={BookOpen} title="Description">
                  <p className="text-sm text-ui-bodyText">{step.description}</p>
                </Section>
              )}

              {/* Narratives */}
              {(fullStep?.narrative_user || fullStep?.narrative_system) && (
                <Section icon={Workflow} title="Narratives">
                  <div className="grid grid-cols-1 gap-3">
                    {fullStep.narrative_user && (
                      <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-200">
                        <h5 className="text-xs font-semibold text-emerald-700 uppercase tracking-wide mb-1.5">
                          User Experience
                        </h5>
                        <p className="text-sm text-ui-bodyText">{fullStep.narrative_user}</p>
                      </div>
                    )}
                    {fullStep.narrative_system && (
                      <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                        <h5 className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-1.5">
                          System Behavior
                        </h5>
                        <p className="text-sm text-ui-bodyText">{fullStep.narrative_system}</p>
                      </div>
                    )}
                  </div>
                </Section>
              )}

              {/* Features */}
              {summaryStep && summaryStep.features.length > 0 && (
                <Section icon={Workflow} title={`Features (${summaryStep.features.length})`}>
                  <div className="space-y-2">
                    {summaryStep.features.map((f) => {
                      const badge = getStatusBadge(f.confirmation_status)
                      const BadgeIcon = badge.icon
                      return (
                        <div
                          key={f.id}
                          className="flex items-start gap-3 bg-ui-background rounded-lg p-3 border border-ui-cardBorder"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-medium text-ui-headingDark">{f.name}</span>
                              {f.is_mvp && (
                                <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-amber-100 text-amber-700">
                                  MVP
                                </span>
                              )}
                            </div>
                            {f.description && (
                              <p className="text-sm text-ui-supportText mt-0.5 line-clamp-2">{f.description}</p>
                            )}
                          </div>
                          <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium flex-shrink-0 ${badge.color}`}>
                            <BadgeIcon className="w-3 h-3" />
                          </span>
                        </div>
                      )
                    })}
                  </div>
                </Section>
              )}

              {/* Enrichment: UI Highlights */}
              {enrichment.ui_highlights && enrichment.ui_highlights.length > 0 && (
                <Section icon={Monitor} title="UI Highlights">
                  <ul className="space-y-1.5">
                    {enrichment.ui_highlights.map((item: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-ui-bodyText">
                        <Monitor className="w-4 h-4 text-brand-teal flex-shrink-0 mt-0.5" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {/* Enrichment: Integrations */}
              {enrichment.integrations && enrichment.integrations.length > 0 && (
                <Section icon={Plug} title="Integrations">
                  <div className="flex flex-wrap gap-2">
                    {enrichment.integrations.map((item: string, i: number) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-sm bg-purple-50 text-purple-700 border border-purple-200"
                      >
                        <Plug className="w-3 h-3" />
                        {item}
                      </span>
                    ))}
                  </div>
                </Section>
              )}

              {/* Enrichment: Rules Applied */}
              {enrichment.rules_applied && enrichment.rules_applied.length > 0 && (
                <Section icon={ShieldCheck} title="Rules Applied">
                  <ul className="space-y-1.5">
                    {enrichment.rules_applied.map((rule: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-ui-bodyText">
                        <ShieldCheck className="w-4 h-4 text-blue-500 flex-shrink-0 mt-0.5" />
                        {rule}
                      </li>
                    ))}
                  </ul>
                </Section>
              )}

              {/* Enrichment: Features Used (from enrichment data, not canvas) */}
              {enrichment.features_used && enrichment.features_used.length > 0 && (
                <Section icon={Workflow} title="Enrichment Features">
                  <div className="flex flex-wrap gap-1.5">
                    {enrichment.features_used.map((feat: string, i: number) => (
                      <span
                        key={i}
                        className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-brand-teal/10 text-brand-teal"
                      >
                        {feat}
                      </span>
                    ))}
                  </div>
                </Section>
              )}

              {/* Empty state if nothing loaded */}
              {!step?.description && !fullStep?.narrative_user && summaryStep?.features.length === 0 && (
                <p className="text-sm text-ui-supportText text-center py-8">
                  No detailed data available for this step yet.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof BookOpen
  title: string
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4 text-ui-supportText" />
        <h4 className="text-sm font-semibold text-ui-headingDark">{title}</h4>
      </div>
      {children}
    </div>
  )
}

export default VpStepDetailDrawer
