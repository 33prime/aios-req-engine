'use client'

import { useMemo } from 'react'
import { Users } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { CollapsibleCard } from '../components/CollapsibleCard'
import type { PersonaBRDSummary, VpStepBRDSummary } from '@/types/workspace'

interface ActorsSectionProps {
  actors: PersonaBRDSummary[]
  workflows?: VpStepBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
}

export function ActorsSection({ actors, workflows = [], onConfirm, onNeedsReview, onConfirmAll, onRefreshEntity, onStatusClick }: ActorsSectionProps) {
  const confirmedCount = actors.filter(
    (a) => a.confirmation_status === 'confirmed_consultant' || a.confirmation_status === 'confirmed_client'
  ).length

  // Derive primary actors = those referenced as actor_persona_id in any workflow step
  const { primaryActors, secondaryActors } = useMemo(() => {
    const activeActorIds = new Set(
      workflows
        .map((w) => w.actor_persona_id)
        .filter((id): id is string => !!id)
    )
    const primary = actors.filter((a) => activeActorIds.has(a.id))
    const secondary = actors.filter((a) => !activeActorIds.has(a.id))
    return { primaryActors: primary, secondaryActors: secondary }
  }, [actors, workflows])

  const renderActorCard = (actor: PersonaBRDSummary) => (
    <CollapsibleCard
      key={actor.id}
      title={actor.name}
      subtitle={actor.role || actor.persona_type || undefined}
      icon={<Users className="w-4 h-4 text-indigo-400" />}
      status={actor.confirmation_status}
      isStale={actor.is_stale}
      staleReason={actor.stale_reason}
      onRefresh={onRefreshEntity ? () => onRefreshEntity('persona', actor.id) : undefined}
      onConfirm={() => onConfirm('persona', actor.id)}
      onNeedsReview={() => onNeedsReview('persona', actor.id)}
      onStatusClick={onStatusClick ? () => onStatusClick('persona', actor.id, actor.name, actor.confirmation_status) : undefined}
    >
      <div className="space-y-3 text-[13px] text-[rgba(55,53,47,0.65)]">
        {actor.description && (
          <p className="leading-relaxed">{actor.description}</p>
        )}
        {actor.goals && actor.goals.length > 0 && (
          <div>
            <span className="font-medium text-[#37352f] text-[12px] uppercase tracking-wide">Goals</span>
            <ul className="mt-1 space-y-1">
              {actor.goals.map((goal, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-teal-500 mt-0.5">&#8226;</span>
                  <span>{goal}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {actor.pain_points && actor.pain_points.length > 0 && (
          <div>
            <span className="font-medium text-[#37352f] text-[12px] uppercase tracking-wide">Pain Points</span>
            <ul className="mt-1 space-y-1">
              {actor.pain_points.map((pain, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-red-400 mt-0.5">&#8226;</span>
                  <span>{pain}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </CollapsibleCard>
  )

  // If no workflows data or all actors are primary, render flat list
  const hasSplit = workflows.length > 0 && secondaryActors.length > 0

  return (
    <section>
      <SectionHeader
        title="Actors & Personas"
        count={actors.length}
        confirmedCount={confirmedCount}
        onConfirmAll={() => onConfirmAll('persona', actors.map((a) => a.id))}
      />
      {actors.length === 0 ? (
        <p className="text-[13px] text-[rgba(55,53,47,0.45)] italic">No personas identified yet</p>
      ) : hasSplit ? (
        <div className="space-y-6">
          {/* Primary Actors */}
          <div>
            <h3 className="text-[12px] font-medium text-gray-400 uppercase tracking-wide mb-2">
              Primary Actors ({primaryActors.length})
            </h3>
            <div className="space-y-2">
              {primaryActors.map(renderActorCard)}
            </div>
          </div>

          {/* Supporting Actors */}
          <div>
            <h3 className="text-[12px] font-medium text-gray-400 uppercase tracking-wide mb-2">
              Supporting Actors ({secondaryActors.length})
            </h3>
            <div className="space-y-2">
              {secondaryActors.map(renderActorCard)}
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {actors.map(renderActorCard)}
        </div>
      )}
    </section>
  )
}
