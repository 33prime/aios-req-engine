/**
 * JourneyFlow - Horizontal value path visualization
 *
 * Shows journey steps with connecting arrows.
 * Steps are droppable targets for features.
 */

'use client'

import { useRef, useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, Route } from 'lucide-react'
import { JourneyStep } from './JourneyStep'
import type { VpStepSummary } from '@/types/workspace'

interface JourneyFlowProps {
  steps: VpStepSummary[]
  isSaving: boolean
  onStepClick?: (stepId: string) => void
}

export function JourneyFlow({ steps, isSaving, onStepClick }: JourneyFlowProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

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

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      const scrollAmount = 340 // Step width + gap
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -scrollAmount : scrollAmount,
        behavior: 'smooth',
      })
    }
  }

  if (steps.length === 0) {
    return (
      <div className="bg-surface-muted rounded-lg border border-dashed border-border p-8 text-center">
        <Route className="w-10 h-10 text-gray-300 mx-auto mb-3" />
        <p className="text-sm text-text-placeholder">No journey steps defined yet</p>
        <p className="text-[12px] text-text-placeholder mt-1">
          Add signals about your value path to generate steps
        </p>
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Left Scroll Button */}
      {canScrollLeft && (
        <button
          onClick={() => scroll('left')}
          className="absolute left-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 bg-white rounded-full shadow-lg border border-border flex items-center justify-center text-text-body hover:bg-surface-muted transition-colors"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
      )}

      {/* Right Scroll Button */}
      {canScrollRight && (
        <button
          onClick={() => scroll('right')}
          className="absolute right-0 top-1/2 -translate-y-1/2 z-10 w-10 h-10 bg-white rounded-full shadow-lg border border-border flex items-center justify-center text-text-body hover:bg-surface-muted transition-colors"
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      )}

      {/* Steps Container */}
      <div
        ref={scrollRef}
        onScroll={checkScroll}
        className="flex gap-0 overflow-x-auto pb-4 scrollbar-hide px-1"
        style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
      >
        {steps.map((step, index) => (
          <JourneyStep
            key={step.id}
            step={step}
            isLast={index === steps.length - 1}
            isSaving={isSaving}
            onStepClick={onStepClick}
          />
        ))}
      </div>
    </div>
  )
}

export default JourneyFlow
