'use client'

import { Users, Zap, AlertTriangle } from 'lucide-react'
import type { PersonaBRDSummary } from '@/types/workspace'

interface CanvasActorsRowProps {
  actors: (PersonaBRDSummary & { canvas_role: 'primary' | 'secondary' })[]
  onSynthesize: () => void
  isSynthesizing: boolean
  synthesisStale: boolean
  hasValuePath: boolean
  onActorClick: (actorId: string | null) => void
  selectedActorId: string | null
}

export function CanvasActorsRow({
  actors,
  onSynthesize,
  isSynthesizing,
  synthesisStale,
  hasValuePath,
  onActorClick,
  selectedActorId,
}: CanvasActorsRowProps) {
  const primaryActors = actors.filter((a) => a.canvas_role === 'primary')
  const secondaryActors = actors.filter((a) => a.canvas_role === 'secondary')

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-[#3FAF7A]" />
          <h2 className="text-[16px] font-semibold text-[#333333]">Canvas Actors</h2>
          <span className="text-[12px] text-[#999999]">({actors.length})</span>
        </div>

        <div className="flex items-center gap-2">
          {synthesisStale && hasValuePath && (
            <span className="inline-flex items-center gap-1 px-2 py-1 text-[11px] font-medium text-amber-700 bg-amber-50 rounded-lg">
              <AlertTriangle className="w-3 h-3" />
              Path outdated
            </span>
          )}
          <button
            onClick={onSynthesize}
            disabled={isSynthesizing || actors.length === 0}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-[12px] font-semibold text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSynthesizing ? (
              <>
                <div className="animate-spin rounded-full h-3.5 w-3.5 border-b-2 border-white" />
                Synthesizing...
              </>
            ) : (
              <>
                <Zap className="w-3.5 h-3.5" />
                {hasValuePath ? 'Regenerate Path' : 'Synthesize Value Path'}
              </>
            )}
          </button>
        </div>
      </div>

      <div className="flex gap-4 flex-wrap">
        {primaryActors.map((actor) => (
          <ActorCard
            key={actor.id}
            actor={actor}
            isPrimary
            isSelected={selectedActorId === actor.id}
            onClick={() => onActorClick(selectedActorId === actor.id ? null : actor.id)}
          />
        ))}
        {secondaryActors.map((actor) => (
          <ActorCard
            key={actor.id}
            actor={actor}
            isPrimary={false}
            isSelected={selectedActorId === actor.id}
            onClick={() => onActorClick(selectedActorId === actor.id ? null : actor.id)}
          />
        ))}
      </div>
    </section>
  )
}

function ActorCard({
  actor,
  isPrimary,
  isSelected,
  onClick,
}: {
  actor: PersonaBRDSummary
  isPrimary: boolean
  isSelected: boolean
  onClick: () => void
}) {
  const goals = actor.goals || []
  const painPoints = actor.pain_points || []

  return (
    <button
      onClick={onClick}
      className={`flex-1 min-w-[220px] max-w-[340px] text-left bg-white rounded-2xl shadow-md border px-5 py-4 transition-all ${
        isSelected
          ? 'border-[#3FAF7A] ring-2 ring-[#3FAF7A]/20'
          : 'border-[#E5E5E5] hover:border-[#3FAF7A]/40'
      } ${isPrimary ? 'border-l-4 border-l-[#3FAF7A]' : 'border-l-4 border-l-[#0A1E2F]'}`}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-full bg-[#F4F4F4] flex items-center justify-center shrink-0">
          <Users className="w-4 h-4 text-[#666666]" />
        </div>
        <div className="min-w-0">
          <p className="text-[14px] font-semibold text-[#333333] truncate">{actor.name}</p>
          {actor.role && (
            <p className="text-[11px] text-[#999999] truncate">{actor.role}</p>
          )}
        </div>
        <span className={`ml-auto shrink-0 px-2 py-0.5 text-[10px] font-medium rounded-full ${
          isPrimary
            ? 'bg-[#E8F5E9] text-[#25785A]'
            : 'bg-[#F0F0F0] text-[#666666]'
        }`}>
          {isPrimary ? 'Primary' : 'Secondary'}
        </span>
      </div>

      {/* Pain/goal highlights */}
      {painPoints.length > 0 && (
        <p className="text-[11px] text-[#999999] mt-2 line-clamp-1 italic">
          Pain: {painPoints[0]}
        </p>
      )}
      {goals.length > 0 && (
        <p className="text-[11px] text-[#25785A] mt-1 line-clamp-1 italic">
          Goal: {goals[0]}
        </p>
      )}
    </button>
  )
}
