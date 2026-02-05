'use client'

import { Users } from 'lucide-react'
import { SectionHeader } from '../components/SectionHeader'
import { CollapsibleCard } from '../components/CollapsibleCard'
import type { PersonaBRDSummary } from '@/types/workspace'

interface ActorsSectionProps {
  actors: PersonaBRDSummary[]
  onConfirm: (entityType: string, entityId: string) => void
  onNeedsReview: (entityType: string, entityId: string) => void
  onConfirmAll: (entityType: string, ids: string[]) => void
}

export function ActorsSection({ actors, onConfirm, onNeedsReview, onConfirmAll }: ActorsSectionProps) {
  const confirmedCount = actors.filter(
    (a) => a.confirmation_status === 'confirmed_consultant' || a.confirmation_status === 'confirmed_client'
  ).length

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
      ) : (
        <div className="space-y-2">
          {actors.map((actor) => (
            <CollapsibleCard
              key={actor.id}
              title={actor.name}
              subtitle={actor.role || actor.persona_type || undefined}
              icon={<Users className="w-4 h-4 text-indigo-400" />}
              status={actor.confirmation_status}
              onConfirm={() => onConfirm('persona', actor.id)}
              onNeedsReview={() => onNeedsReview('persona', actor.id)}
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
          ))}
        </div>
      )}
    </section>
  )
}
