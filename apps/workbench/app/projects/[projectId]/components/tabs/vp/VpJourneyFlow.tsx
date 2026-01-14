/**
 * VpJourneyFlow Component
 *
 * Horizontal connected cards showing the golden path flow.
 * Each card shows: step title, actor icons, value rating, status.
 * Cards are connected with arrows to show flow direction.
 */

'use client'

import React, { useRef, useEffect } from 'react'
import { User, Bot, Plug, ChevronLeft, ChevronRight } from 'lucide-react'
import type { VpStep } from '@/types/api'

interface VpJourneyFlowProps {
  steps: VpStep[]
  selectedId: string | null
  onSelect: (step: VpStep) => void
}

// Value rating display
function ValueStars({ step }: { step: VpStep }) {
  // Determine value level based on content
  const hasHighValue = step.value_created && step.value_created.length > 100
  const hasEvidence = step.evidence && step.evidence.length > 0
  const hasFeatures = step.features_used && step.features_used.length >= 2

  let stars = 1
  if (hasHighValue) stars++
  if (hasEvidence) stars++
  if (hasFeatures && stars < 3) stars++

  return (
    <div className="flex gap-0.5">
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          className={`text-xs ${i <= stars ? 'text-amber-400' : 'text-gray-200'}`}
        >
          ★
        </span>
      ))}
    </div>
  )
}

// Actor icons for a step
function ActorIcons({ step }: { step: VpStep }) {
  const actors: { type: 'human' | 'system'; name: string }[] = []

  // Primary persona is human
  if (step.actor_persona_name || step.actor_persona_id) {
    actors.push({ type: 'human', name: step.actor_persona_name || 'User' })
  }

  // Check for system actors in integrations or narrative
  const hasAI = step.narrative_system?.toLowerCase().includes('ai') ||
                step.narrative_system?.toLowerCase().includes('nlp') ||
                step.narrative_system?.toLowerCase().includes('engine')
  const hasAPI = step.integrations_triggered && step.integrations_triggered.length > 0

  if (hasAI) actors.push({ type: 'system', name: 'AI' })
  if (hasAPI) actors.push({ type: 'system', name: 'API' })

  // Default to user if no actors detected
  if (actors.length === 0) {
    actors.push({ type: 'human', name: 'User' })
  }

  return (
    <div className="flex items-center gap-1">
      {actors.slice(0, 3).map((actor, idx) => (
        <div
          key={idx}
          className={`w-5 h-5 rounded-full flex items-center justify-center ${
            actor.type === 'human'
              ? 'bg-blue-100 text-blue-600'
              : 'bg-slate-100 text-slate-500'
          }`}
          title={actor.name}
        >
          {actor.type === 'human' ? (
            <User className="w-3 h-3" />
          ) : actor.name === 'AI' ? (
            <Bot className="w-3 h-3" />
          ) : (
            <Plug className="w-3 h-3" />
          )}
        </div>
      ))}
    </div>
  )
}

// Individual step card
function StepCard({
  step,
  isSelected,
  isLast,
  onClick
}: {
  step: VpStep
  isSelected: boolean
  isLast: boolean
  onClick: () => void
}) {
  const status = step.confirmation_status || step.status
  const isConfirmed = status === 'confirmed_consultant' || status === 'confirmed_client'
  const statusText = isConfirmed ? '✓ Confirmed' : '○ Draft'

  return (
    <div className="flex items-center flex-shrink-0">
      {/* Card */}
      <button
        onClick={onClick}
        className={`
          w-40 p-3 rounded-lg border-2 transition-all duration-200
          hover:shadow-md hover:border-blue-300
          ${isSelected
            ? 'border-blue-500 bg-blue-50 shadow-md'
            : 'border-gray-200 bg-white'
          }
        `}
      >
        {/* Step label at top */}
        <div className="text-xs text-gray-400 font-medium mb-1">
          Step {step.step_index}
        </div>

        {/* Title */}
        <h4 className="text-sm font-medium text-gray-900 line-clamp-2 mb-1">
          {step.label}
        </h4>

        {/* Status text */}
        <div className={`text-xs mb-2 ${isConfirmed ? 'text-green-600' : 'text-gray-400'}`}>
          {statusText}
        </div>

        {/* Bottom row: actors + value */}
        <div className="flex items-center justify-between mt-auto">
          <ActorIcons step={step} />
          <ValueStars step={step} />
        </div>
      </button>

      {/* Connector arrow */}
      {!isLast && (
        <div className="flex items-center px-2 flex-shrink-0">
          <div className="w-8 h-0.5 bg-gray-300" />
          <div className="w-0 h-0 border-t-4 border-b-4 border-l-6 border-transparent border-l-gray-300" />
        </div>
      )}
    </div>
  )
}

export function VpJourneyFlow({ steps, selectedId, onSelect }: VpJourneyFlowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = React.useState(false)
  const [canScrollRight, setCanScrollRight] = React.useState(false)

  // Sort steps by index
  const sortedSteps = [...steps].sort((a, b) => a.step_index - b.step_index)

  // Check scroll state
  const checkScroll = () => {
    if (scrollRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current
      setCanScrollLeft(scrollLeft > 0)
      setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 10)
    }
  }

  useEffect(() => {
    checkScroll()
    window.addEventListener('resize', checkScroll)
    return () => window.removeEventListener('resize', checkScroll)
  }, [steps])

  // Scroll to selected card
  useEffect(() => {
    if (selectedId && scrollRef.current) {
      const selectedIndex = sortedSteps.findIndex(s => s.id === selectedId)
      if (selectedIndex >= 0) {
        const cardWidth = 144 + 48 // card width + connector
        const scrollPosition = selectedIndex * cardWidth - scrollRef.current.clientWidth / 2 + cardWidth / 2
        scrollRef.current.scrollTo({ left: Math.max(0, scrollPosition), behavior: 'smooth' })
      }
    }
  }, [selectedId])

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 300
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth'
      })
    }
  }

  if (steps.length === 0) {
    return (
      <div className="bg-gray-50 rounded-lg border-2 border-dashed border-gray-200 p-8 text-center">
        <p className="text-gray-500">No steps in the Value Path yet.</p>
        <p className="text-sm text-gray-400 mt-1">Ask the AI assistant to generate the value path.</p>
      </div>
    )
  }

  return (
    <div className="relative bg-white rounded-lg border border-gray-200 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
          Journey Flow
        </h3>
        <div className="flex items-center gap-1">
          {/* Scroll indicators */}
          {sortedSteps.length > 4 && (
            <>
              <button
                onClick={() => scroll('left')}
                disabled={!canScrollLeft}
                className={`p-1 rounded ${canScrollLeft ? 'hover:bg-gray-100 text-gray-600' : 'text-gray-300'}`}
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              <button
                onClick={() => scroll('right')}
                disabled={!canScrollRight}
                className={`p-1 rounded ${canScrollRight ? 'hover:bg-gray-100 text-gray-600' : 'text-gray-300'}`}
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </>
          )}
        </div>
      </div>

      {/* Scrollable cards container */}
      <div
        ref={scrollRef}
        onScroll={checkScroll}
        className="flex items-center overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-transparent"
        style={{ scrollbarWidth: 'thin' }}
      >
        <div className="flex items-center py-3 px-2">
          {sortedSteps.map((step, idx) => (
            <StepCard
              key={step.id}
              step={step}
              isSelected={step.id === selectedId}
              isLast={idx === sortedSteps.length - 1}
              onClick={() => onSelect(step)}
            />
          ))}
        </div>
      </div>

      {/* Selection indicator */}
      {selectedId && (
        <div className="text-center mt-2">
          <span className="text-xs text-blue-600 font-medium">
            ▲ Selected
          </span>
        </div>
      )}
    </div>
  )
}

export default VpJourneyFlow
