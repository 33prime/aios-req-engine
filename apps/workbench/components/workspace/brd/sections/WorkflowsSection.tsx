'use client'

import { Workflow } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { CollapsibleCard } from '../components/CollapsibleCard'
import type { VpStepBRDSummary } from '@/types/workspace'

interface WorkflowsSectionProps {
  workflows: VpStepBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
}

export function WorkflowsSection({ workflows, onConfirm, onNeedsReview, onConfirmAll }: WorkflowsSectionProps) {
  const confirmedCount = workflows.filter(
    (w) => w.confirmation_status === 'confirmed_consultant' || w.confirmation_status === 'confirmed_client'
  ).length

  return (
    <section>
      <SectionHeader
        title="Key Workflows"
        count={workflows.length}
        confirmedCount={confirmedCount}
        onConfirmAll={() => onConfirmAll('vp_step', workflows.map((w) => w.id))}
      />
      {workflows.length === 0 ? (
        <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No workflows mapped yet</p>
      ) : (
        <div className="space-y-2">
          {workflows.map((step, idx) => (
            <CollapsibleCard
              key={step.id}
              title={`${idx + 1}. ${step.title}`}
              subtitle={step.actor_persona_name ? `Actor: ${step.actor_persona_name}` : undefined}
              icon={<Workflow className="w-4 h-4 text-blue-400" />}
              status={step.confirmation_status}
              onConfirm={() => onConfirm('vp_step', step.id)}
              onNeedsReview={() => onNeedsReview('vp_step', step.id)}
            >
              <div className="space-y-3">
                {step.description && (
                  <p className="text-[13px] text-[rgba(55,53,47,0.65)] leading-relaxed">
                    {step.description}
                  </p>
                )}

                {/* Actor persona chip */}
                {step.actor_persona_name && (
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px] text-gray-400">Actor:</span>
                    <span className="px-2 py-0.5 text-[11px] font-medium bg-indigo-50 text-indigo-700 rounded-full">
                      {step.actor_persona_name}
                    </span>
                  </div>
                )}

                {/* Feature links */}
                {step.feature_names && step.feature_names.length > 0 && (
                  <div>
                    <span className="text-[11px] text-gray-400 block mb-1">Features:</span>
                    <div className="flex flex-wrap gap-1">
                      {step.feature_names.map((name, i) => (
                        <span
                          key={step.feature_ids?.[i] || i}
                          className="px-2 py-0.5 text-[11px] font-medium bg-teal-50 text-teal-700 rounded-full"
                        >
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CollapsibleCard>
          ))}
        </div>
      )}
    </section>
  )
}
