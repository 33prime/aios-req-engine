'use client'

import { useRef, useState, useMemo } from 'react'
import { MapPin, ChevronLeft, ChevronRight, Clock } from 'lucide-react'
import type { WorkflowPair, WorkflowStepSummary, PersonaBRDSummary, AutomationLevel } from '@/types/workspace'

interface ActorJourneySectionProps {
  workflowPairs: WorkflowPair[]
  selectedActorId: string | null
  actors: PersonaBRDSummary[]
}

// Boilerplate patterns to exclude from the journey
const BOILERPLATE_PATTERNS = [
  /sign\s*up/i,
  /sign\s*in/i,
  /log\s*in/i,
  /log\s*out/i,
  /register/i,
  /registration/i,
  /password\s*reset/i,
  /forgot\s*password/i,
  /onboarding/i,
  /welcome/i,
  /getting\s*started/i,
  /basic\s*navigation/i,
  /homepage/i,
]

function isBoilerplate(label: string): boolean {
  return BOILERPLATE_PATTERNS.some((p) => p.test(label))
}

function AutomationBadge({ level }: { level: AutomationLevel }) {
  const config: Record<AutomationLevel, { dot: string; label: string; bg: string; text: string }> = {
    manual: { dot: 'bg-gray-400', label: 'Manual', bg: 'bg-gray-100', text: 'text-gray-600' },
    semi_automated: { dot: 'bg-amber-400', label: 'Semi-auto', bg: 'bg-amber-50', text: 'text-amber-700' },
    fully_automated: { dot: 'bg-[#3FAF7A]', label: 'Automated', bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  }
  const c = config[level] || config.manual
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium ${c.bg} ${c.text} rounded`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}

export function ActorJourneySection({
  workflowPairs,
  selectedActorId,
  actors,
}: ActorJourneySectionProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const selectedActor = actors.find((a) => a.id === selectedActorId)

  // Collect future-state steps for the selected actor across all workflow pairs
  const journeySteps = useMemo(() => {
    if (!selectedActorId) return []

    const steps: WorkflowStepSummary[] = []
    for (const pair of workflowPairs) {
      for (const step of pair.future_steps) {
        if (step.actor_persona_id === selectedActorId && !isBoilerplate(step.label)) {
          steps.push(step)
        }
      }
    }

    // Sort by step_index
    steps.sort((a, b) => a.step_index - b.step_index)
    return steps
  }, [workflowPairs, selectedActorId])

  const handleScroll = () => {
    const el = scrollRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 0)
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 10)
  }

  const scroll = (dir: 'left' | 'right') => {
    const el = scrollRef.current
    if (!el) return
    el.scrollBy({ left: dir === 'left' ? -300 : 300, behavior: 'smooth' })
  }

  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <MapPin className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[16px] font-semibold text-[#333333]">Actor Journey</h2>
        {selectedActor && (
          <span className="px-2 py-0.5 text-[11px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
            {selectedActor.name}
          </span>
        )}
      </div>

      {!selectedActorId ? (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] px-6 py-8 text-center">
          <MapPin className="w-8 h-8 text-[#999999] mx-auto mb-3" />
          <p className="text-[13px] text-[#666666]">
            Select an actor above to view their future-state journey.
          </p>
        </div>
      ) : journeySteps.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] px-6 py-8 text-center">
          <p className="text-[13px] text-[#666666]">
            No future-state workflow steps found for <strong>{selectedActor?.name}</strong>.
          </p>
        </div>
      ) : (
        <div className="relative">
          {/* Scroll buttons */}
          {canScrollLeft && (
            <button
              onClick={() => scroll('left')}
              className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full bg-white shadow-md border border-[#E5E5E5] flex items-center justify-center hover:bg-gray-50 transition-colors"
            >
              <ChevronLeft className="w-4 h-4 text-[#666666]" />
            </button>
          )}
          {canScrollRight && (
            <button
              onClick={() => scroll('right')}
              className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-8 h-8 rounded-full bg-white shadow-md border border-[#E5E5E5] flex items-center justify-center hover:bg-gray-50 transition-colors"
            >
              <ChevronRight className="w-4 h-4 text-[#666666]" />
            </button>
          )}

          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="flex gap-3 overflow-x-auto scrollbar-hide pb-2"
          >
            {journeySteps.map((step, idx) => (
              <div key={step.id} className="flex items-center shrink-0">
                <JourneyStepCard step={step} index={idx + 1} />
                {idx < journeySteps.length - 1 && (
                  <div className="w-6 h-0 border-t-2 border-dashed border-[#E5E5E5] shrink-0 mx-1" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  )
}

function JourneyStepCard({ step, index }: { step: WorkflowStepSummary; index: number }) {
  return (
    <div className="w-[240px] bg-white rounded-2xl shadow-md border border-[#E5E5E5] px-4 py-3 shrink-0">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="w-6 h-6 rounded-full bg-[#0A1E2F] flex items-center justify-center shrink-0">
          <span className="text-[10px] font-bold text-white">{index}</span>
        </div>
        <span className="text-[13px] font-medium text-[#333333] line-clamp-1">{step.label}</span>
      </div>

      {/* Description */}
      {step.description && (
        <p className="text-[12px] text-[#666666] line-clamp-2 mb-2">{step.description}</p>
      )}

      {/* Metadata */}
      <div className="flex items-center gap-2 flex-wrap">
        <AutomationBadge level={step.automation_level} />
        {step.time_minutes != null && (
          <span className="inline-flex items-center gap-0.5 text-[11px] text-[#999999]">
            <Clock className="w-3 h-3" />
            {step.time_minutes}m
          </span>
        )}
      </div>

      {/* Benefit */}
      {step.benefit_description && (
        <p className="text-[11px] text-[#25785A] mt-2 italic line-clamp-2">
          {step.benefit_description}
        </p>
      )}

      {/* Feature links */}
      {step.feature_names && step.feature_names.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {step.feature_names.map((name, i) => (
            <span
              key={step.feature_ids?.[i] || i}
              className="px-1.5 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-lg"
            >
              {name}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
