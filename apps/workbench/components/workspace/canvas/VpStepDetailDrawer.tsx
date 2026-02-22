/**
 * VpStepDetailDrawer - Right-slide drawer for VP step details
 *
 * Opens when clicking a journey step card in the canvas.
 * Single scrollable view with sections for narratives, features, enrichment.
 */

'use client'

import { useState, useEffect } from 'react'
import {
  User,
  Workflow,
  BookOpen,
  Monitor,
  Plug,
  ShieldCheck,
} from 'lucide-react'
import { getVpSteps } from '@/lib/api'
import type { CanvasData } from '@/types/workspace'
import { DrawerShell } from '@/components/ui/DrawerShell'
import { Spinner } from '@/components/ui/Spinner'
import { BRDStatusBadge } from '@/components/workspace/brd/components/StatusBadge'

interface VpStepDetailDrawerProps {
  stepId: string
  projectId: string
  canvasData: CanvasData
  onClose: () => void
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
  const enrichment = fullStep?.enrichment || {}

  return (
    <DrawerShell
      onClose={onClose}
      icon={Workflow}
      entityLabel={step?.step_index != null ? `Step ${step.step_index + 1}` : undefined}
      title={step?.title || 'Loading...'}
      headerExtra={
        step?.actor_persona_name ? (
          <div className="flex items-center gap-1 mt-0.5">
            <User className="w-3 h-3 text-[#999999]" />
            <span className="text-[13px] text-[#999999]">{step.actor_persona_name}</span>
          </div>
        ) : undefined
      }
      headerRight={
        <BRDStatusBadge status={step?.confirmation_status} />
      }
    >
      <div className="space-y-6">
        {isLoading ? (
          <Spinner size="lg" label="Loading..." />
        ) : (
          <>
            {/* Description */}
            {step?.description && (
              <Section icon={BookOpen} title="Description">
                <p className="text-[13px] text-[#666666]">{step.description}</p>
              </Section>
            )}

            {/* Narratives */}
            {(fullStep?.narrative_user || fullStep?.narrative_system) && (
              <Section icon={Workflow} title="Narratives">
                <div className="grid grid-cols-1 gap-3">
                  {fullStep.narrative_user && (
                    <div className="bg-[#E8F5E9] rounded-lg p-4 border border-[#3FAF7A]/20">
                      <h5 className="text-[11px] font-semibold text-[#25785A] uppercase tracking-wide mb-1.5">
                        User Experience
                      </h5>
                      <p className="text-[13px] text-[#666666]">{fullStep.narrative_user}</p>
                    </div>
                  )}
                  {fullStep.narrative_system && (
                    <div className="bg-[#F0F0F0] rounded-lg p-4 border border-[#E5E5E5]">
                      <h5 className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide mb-1.5">
                        System Behavior
                      </h5>
                      <p className="text-[13px] text-[#666666]">{fullStep.narrative_system}</p>
                    </div>
                  )}
                </div>
              </Section>
            )}

            {/* Features */}
            {summaryStep && summaryStep.features.length > 0 && (
              <Section icon={Workflow} title={`Features (${summaryStep.features.length})`}>
                <div className="space-y-2">
                  {summaryStep.features.map((f) => (
                    <div
                      key={f.id}
                      className="flex items-start gap-3 bg-[#F9F9F9] rounded-lg p-3 border border-[#E5E5E5]"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[13px] font-medium text-[#333333]">{f.name}</span>
                          {f.is_mvp && (
                            <span className="px-1.5 py-0.5 text-[10px] font-bold rounded bg-[#F0F0F0] text-[#666666]">
                              MVP
                            </span>
                          )}
                        </div>
                        {f.description && (
                          <p className="text-[13px] text-[#999999] mt-0.5 line-clamp-2">{f.description}</p>
                        )}
                      </div>
                      <BRDStatusBadge status={f.confirmation_status} />
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* Enrichment: UI Highlights */}
            {enrichment.ui_highlights && enrichment.ui_highlights.length > 0 && (
              <Section icon={Monitor} title="UI Highlights">
                <ul className="space-y-1.5">
                  {enrichment.ui_highlights.map((item: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                      <Monitor className="w-4 h-4 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
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
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[13px] bg-[#F0F0F0] text-[#666666] border border-[#E5E5E5]"
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
                    <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                      <ShieldCheck className="w-4 h-4 text-[#3FAF7A] flex-shrink-0 mt-0.5" />
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
                      className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-[#E8F5E9] text-[#25785A]"
                    >
                      {feat}
                    </span>
                  ))}
                </div>
              </Section>
            )}

            {/* Empty state if nothing loaded */}
            {!step?.description && !fullStep?.narrative_user && summaryStep?.features.length === 0 && (
              <p className="text-[13px] text-[#999999] text-center py-8">
                No detailed data available for this step yet.
              </p>
            )}
          </>
        )}
      </div>
    </DrawerShell>
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
        <Icon className="w-4 h-4 text-[#999999]" />
        <h4 className="text-[13px] font-semibold text-[#333333]">{title}</h4>
      </div>
      {children}
    </div>
  )
}
