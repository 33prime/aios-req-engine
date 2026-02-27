'use client'

import { useState, useMemo } from 'react'
import { Users, ChevronRight, Star, Workflow, AlertTriangle } from 'lucide-react'
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

// ============================================================================
// Avatar circle with initials (color from name hash)
// ============================================================================

const AVATAR_COLORS = [
  'bg-[#25785A] text-white',
  'bg-[#0A1E2F] text-white',
  'bg-[#4CC08C] text-white',
  'bg-[#6366F1] text-white',
  'bg-[#EC4899] text-white',
  'bg-[#F59E0B] text-white',
  'bg-[#8B5CF6] text-white',
  'bg-[#06B6D4] text-white',
]

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return name.slice(0, 2).toUpperCase()
}

function getAvatarColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = ((hash << 5) - hash + name.charCodeAt(i)) | 0
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

function Avatar({ name, isPrimary }: { name: string; isPrimary?: boolean }) {
  return (
    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold shrink-0 ${getAvatarColor(name)}`}>
      {getInitials(name)}
    </div>
  )
}

// ============================================================================
// Canvas Role Toggle
// ============================================================================

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
        <Star className="w-3 h-3 fill-brand-primary text-brand-primary" />
        Primary
      </button>
    )
  }
  if (role === 'secondary') {
    return (
      <button onClick={onToggle} className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#F0F0F0] text-[#666666] text-[10px] font-medium hover:bg-[#e5e5e5] transition-colors" title="Click to change canvas role">
        <Star className="w-3 h-3 fill-text-placeholder text-text-placeholder" />
        Secondary
      </button>
    )
  }
  return (
    <button onClick={onToggle} className="flex items-center gap-1 px-2 py-0.5 rounded-full text-text-placeholder text-[10px] font-medium hover:bg-[#F0F0F0] transition-colors" title="Set canvas role">
      <Star className="w-3 h-3" />
    </button>
  )
}

// ============================================================================
// Actor Accordion Card (refreshed)
// ============================================================================

function ActorAccordionCard({
  actor,
  workflowCount,
  driverCount,
  onConfirm,
  onNeedsReview,
  onRefreshEntity,
  onStatusClick,
  onCanvasRoleUpdate,
}: {
  actor: PersonaBRDSummary
  workflowCount: number
  driverCount: number
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onRefreshEntity?: (entityType: string, entityId: string) => void
  onStatusClick?: (entityType: string, entityId: string, entityName: string, status?: string | null) => void
  onCanvasRoleUpdate?: (personaId: string, role: 'primary' | 'secondary' | null) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [hasBeenExpanded, setHasBeenExpanded] = useState(false)
  const isPrimary = actor.canvas_role === 'primary'

  return (
    <div className={`bg-white rounded-2xl shadow-md border overflow-hidden ${isPrimary ? 'border-l-[3px] border-l-brand-primary border-t border-r border-b border-border' : 'border-border'}`}>
      {/* Header row */}
      <button
        onClick={() => { const next = !expanded; setExpanded(next); if (next && !hasBeenExpanded) setHasBeenExpanded(true) }}
        className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-gray-50/50 transition-colors"
      >
        <ChevronRight
          className={`w-4 h-4 text-text-placeholder shrink-0 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
        />
        <Avatar name={actor.name} isPrimary={isPrimary} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-semibold text-text-body">{actor.name}</span>
            {actor.role && (
              <span className="text-[12px] text-text-placeholder truncate">({actor.role})</span>
            )}
          </div>
          {/* Connection badges */}
          <div className="flex items-center gap-3 mt-0.5">
            {workflowCount > 0 && (
              <span className="flex items-center gap-1 text-[11px] text-[#666666]">
                <Workflow className="w-3 h-3 text-text-placeholder" />
                {workflowCount} workflow{workflowCount !== 1 ? 's' : ''}
              </span>
            )}
            {driverCount > 0 && (
              <span className="flex items-center gap-1 text-[11px] text-[#666666]">
                <AlertTriangle className="w-3 h-3 text-text-placeholder" />
                {driverCount} driver{driverCount !== 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
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
        <span className="shrink-0" onClick={(e) => e.stopPropagation()}>
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

            {/* Goals as pill tags */}
            {actor.goals && actor.goals.length > 0 && (
              <div className="mb-3">
                <span className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wider block mb-2">Goals</span>
                <div className="flex flex-wrap gap-1.5">
                  {actor.goals.map((goal, i) => (
                    <span key={i} className="px-2.5 py-1 text-[11px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                      {goal}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Pain points */}
            {actor.pain_points && actor.pain_points.length > 0 && (
              <div className="mb-3">
                <span className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wider block mb-2">Pain Points</span>
                <ul className="space-y-1.5">
                  {actor.pain_points.map((pain, i) => (
                    <li key={i} className="flex items-start gap-2 text-[13px] text-[#666666]">
                      <span className="text-text-placeholder mt-0.5 shrink-0">&#8226;</span>
                      <span>{pain}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Confirm / Review actions */}
            <div className="mt-4 pt-3 border-t border-border">
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

  // Compute per-persona workflow count from vp_steps actor_persona_id
  const workflowCountMap = useMemo(() => {
    const map: Record<string, number> = {}
    for (const w of (workflows as VpStepBRDSummary[])) {
      if (w.actor_persona_id) {
        map[w.actor_persona_id] = (map[w.actor_persona_id] || 0) + 1
      }
    }
    return map
  }, [workflows])

  // Derive primary/secondary from canvas_role
  const { primaryActors, secondaryActors } = useMemo(() => {
    const primary = actors.filter((a) => a.canvas_role === 'primary')
    const secondary = actors.filter((a) => a.canvas_role !== 'primary')
    return { primaryActors: primary, secondaryActors: secondary }
  }, [actors])

  const renderActorCard = (actor: PersonaBRDSummary) => (
    <ActorAccordionCard
      key={actor.id}
      actor={actor}
      workflowCount={workflowCountMap[actor.id] || 0}
      driverCount={(actor.pain_points?.length || 0) + (actor.goals?.length || 0)}
      onConfirm={onConfirm}
      onNeedsReview={onNeedsReview}
      onRefreshEntity={onRefreshEntity}
      onStatusClick={onStatusClick}
      onCanvasRoleUpdate={onCanvasRoleUpdate}
    />
  )

  const hasSplit = primaryActors.length > 0 && secondaryActors.length > 0

  return (
    <section id="brd-section-personas">
      <SectionHeader
        title="Actors & Personas"
        count={actors.length}
        confirmedCount={confirmedCount}
        onConfirmAll={() => onConfirmAll('persona', actors.map((a) => a.id))}
      />
      {actors.length === 0 ? (
        <p className="text-[13px] text-text-placeholder italic">No personas identified yet</p>
      ) : hasSplit ? (
        <div className="space-y-6">
          <div>
            <h3 className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wider mb-3">
              Primary Actors ({primaryActors.length})
            </h3>
            <div className="space-y-3">
              {primaryActors.map(renderActorCard)}
            </div>
          </div>
          <div>
            <h3 className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wider mb-3">
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
