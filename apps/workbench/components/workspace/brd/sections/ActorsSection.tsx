'use client'

import { useState, useMemo } from 'react'
import { Users, ChevronRight, Star } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { BRDStatusBadge } from '../components/StatusBadge'
import { ConfirmActions } from '../components/ConfirmActions'
import { StaleIndicator } from '../components/StaleIndicator'
import type { PersonaBRDSummary, VpStepBRDSummary } from '@/types/workspace'

interface ActorsSectionProps {
  actors: PersonaBRDSummary[]
  workflows?: VpStepBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  onCanvasRoleUpdate?: (personaId: string, role: 'primary' | 'secondary' | null) => void
}

function CanvasRoleToggle({
  role,
  onToggle,
}: {
  role?: 'primary' | 'secondary' | null
  onToggle: () => void
}) {
  if (role === 'primary') {
    return (
      <button onClick={onToggle} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#E8F5E9] text-[#25785A] text-[10px] font-medium hover:bg-[#d0ecd6] transition-colors" title="Click to change canvas role">
        <Star className="w-3 h-3 fill-[#3FAF7A] text-[#3FAF7A]" />
        Primary
      </button>
    )
  }
  if (role === 'secondary') {
    return (
      <button onClick={onToggle} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#F0F0F0] text-[#666666] text-[10px] font-medium hover:bg-[#e5e5e5] transition-colors" title="Click to change canvas role">
        <Star className="w-3 h-3 fill-[#999999] text-[#999999]" />
        Secondary
      </button>
    )
  }
  return (
    <button onClick={onToggle} className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[#999999] text-[10px] font-medium hover:bg-[#F0F0F0] transition-colors" title="Set canvas role">
      <Star className="w-3 h-3" />
    </button>
  )
}

function ActorAccordionCard({
  actor,
  onConfirm,
  onNeedsReview,
  onRefreshEntity,
  onStatusClick,
  onCanvasRoleUpdate,
}: {
  actor: PersonaBRDSummary
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  onCanvasRoleUpdate?: (personaId: string, role: 'primary' | 'secondary' | null) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [hasBeenExpanded, setHasBeenExpanded] = useState(false)

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden">
      {/* Header row */}
      <button
        onClick={() => { const next = !expanded; setExpanded(next); if (next && !hasBeenExpanded) setHasBeenExpanded(true) }}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-[#999999] shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <Users className="w-4 h-4 text-[#3FAF7A] shrink-0" />
        <span className="text-[14px] font-semibold text-[#333333] truncate">{actor.name}</span>
        {actor.role && (
          <span className="text-[12px] text-[#999999] shrink-0">({actor.role})</span>
        )}
        {onCanvasRoleUpdate && (
          <span className="shrink-0" onClick={(e) => e.stopPropagation()}>
            <CanvasRoleToggle
              role={actor.canvas_role}
              onToggle={() => {
                const nextRole = !actor.canvas_role ? 'primary' : actor.canvas_role === 'primary' ? 'secondary' : null
                onCanvasRoleUpdate(actor.id, nextRole)
              }}
            />
          </span>
        )}
        <span className="ml-auto shrink-0" onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge
            status={actor.confirmation_status}
            onClick={onStatusClick ? () => onStatusClick('persona', actor.id, actor.name, actor.confirmation_status) : undefined}
          />
        </span>
        {actor.is_stale && (
          <span className="shrink-0">
            <StaleIndicator reason={actor.stale_reason || undefined} onRefresh={onRefreshEntity ? () => onRefreshEntity('persona', actor.id) : undefined} />
          </span>
        )}
      </button>

      {/* Expanded body */}
      {hasBeenExpanded && (
        <div className={`overflow-hidden transition-all duration-200 ${expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'}`}>
          <div className="px-5 pb-5 pt-1">
            {/* Description */}
            {actor.description && (
              <p className="text-[13px] text-[#666666] leading-relaxed mb-4">{actor.description}</p>
            )}

            {/* Two-column: What they need / Why they need it */}
            {((actor.goals && actor.goals.length > 0) || (actor.pain_points && actor.pain_points.length > 0)) && (
              <div className="flex gap-6">
                {/* What they need (goals) */}
                {actor.goals && actor.goals.length > 0 && (
                  <div className="flex-1 min-w-0">
                    <div className="px-3 py-1.5 rounded-lg mb-3 bg-[#E8F5E9] text-[#25785A]">
                      <span className="text-[11px] font-semibold uppercase tracking-wider">What They Need</span>
                    </div>
                    <ul className="space-y-2">
                      {actor.goals.map((goal, i) => (
                        <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                          <span className="text-[#3FAF7A] mt-0.5 shrink-0">&#8226;</span>
                          <span>{goal}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Why they need it (pain points) */}
                {actor.pain_points && actor.pain_points.length > 0 && (
                  <div className="flex-1 min-w-0">
                    <div className="px-3 py-1.5 rounded-lg mb-3 bg-[#F0F0F0] text-[#666666]">
                      <span className="text-[11px] font-semibold uppercase tracking-wider">Why They Need It</span>
                    </div>
                    <ul className="space-y-2">
                      {actor.pain_points.map((pain, i) => (
                        <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                          <span className="text-[#999999] mt-0.5 shrink-0">&#8226;</span>
                          <span>{pain}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Confirm / Review actions */}
            <div className="mt-4 pt-3 border-t border-[#E5E5E5]">
              <ConfirmActions
                status={actor.confirmation_status}
                onConfirm={() => onConfirm('persona', actor.id)}
                onNeedsReview={() => onNeedsReview('persona', actor.id)}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export function ActorsSection({ actors, workflows = [], onConfirm, onNeedsReview, onConfirmAll, onRefreshEntity, onStatusClick, onCanvasRoleUpdate }: ActorsSectionProps) {
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
    <ActorAccordionCard
      key={actor.id}
      actor={actor}
      onConfirm={onConfirm}
      onNeedsReview={onNeedsReview}
      onRefreshEntity={onRefreshEntity}
      onStatusClick={onStatusClick}
      onCanvasRoleUpdate={onCanvasRoleUpdate}
    />
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
        <p className="text-[13px] text-[#999999] italic">No personas identified yet</p>
      ) : hasSplit ? (
        <div className="space-y-6">
          {/* Primary Actors */}
          <div>
            <h3 className="text-[11px] font-semibold text-[#999999] uppercase tracking-wider mb-3">
              Primary Actors ({primaryActors.length})
            </h3>
            <div className="space-y-3">
              {primaryActors.map(renderActorCard)}
            </div>
          </div>

          {/* Supporting Actors */}
          <div>
            <h3 className="text-[11px] font-semibold text-[#999999] uppercase tracking-wider mb-3">
              Supporting Actors ({secondaryActors.length})
            </h3>
            <div className="space-y-3">
              {secondaryActors.map(renderActorCard)}
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          {actors.map(renderActorCard)}
        </div>
      )}
    </section>
  )
}
