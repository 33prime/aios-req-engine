'use client'

import { useState, useEffect, useRef } from 'react'
import type { AgentType } from '@/types/workspace'

interface Props {
  agentType: AgentType
  agentName: string
  isRunning: boolean
  startedAt: number | null
}

const STEPS_BY_TYPE: Record<AgentType, string[]> = {
  classifier: ['Reading input', 'Identifying entities', 'Classifying categories', 'Scoring confidence', 'Building output'],
  matcher: ['Reading input', 'Extracting candidates', 'Computing similarity', 'Ranking matches', 'Building output'],
  predictor: ['Reading input', 'Analyzing patterns', 'Generating predictions', 'Assessing risk', 'Building output'],
  watcher: ['Reading input', 'Scanning for alerts', 'Assessing severity', 'Recommending actions', 'Building output'],
  generator: ['Reading input', 'Synthesizing narrative', 'Structuring sections', 'Assessing confidence', 'Building output'],
  processor: ['Reading input', 'Extracting entities', 'Generating probes', 'Summarizing findings', 'Building output'],
}

export function ProcessingAnimation({ agentType, agentName, isRunning, startedAt }: Props) {
  const [activeStep, setActiveStep] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval>>()
  const steps = STEPS_BY_TYPE[agentType] || STEPS_BY_TYPE.processor

  useEffect(() => {
    if (isRunning) {
      setActiveStep(0)
      intervalRef.current = setInterval(() => {
        setActiveStep(prev => {
          if (prev >= steps.length - 1) {
            // Stay on last step until done
            return prev
          }
          return prev + 1
        })
      }, 350)
    } else {
      // Complete all steps instantly
      setActiveStep(steps.length)
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [isRunning, steps.length])

  const elapsed = startedAt ? Math.round((Date.now() - startedAt) / 1000) : 0

  return (
    <div className="py-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-[10px] font-medium" style={{ color: '#044159' }}>{agentName}</span>
        {isRunning && (
          <span className="text-[9px]" style={{ color: '#A0AEC0' }}>{elapsed}s</span>
        )}
      </div>
      <div className="space-y-2">
        {steps.map((label, i) => {
          const isDone = i < activeStep
          const isActive = i === activeStep && isRunning
          const isPending = i > activeStep || (i === activeStep && !isRunning && activeStep < steps.length)
          const allDone = !isRunning && activeStep >= steps.length

          return (
            <div key={i} className="flex items-center gap-2.5">
              {/* Status indicator */}
              <div className="flex-shrink-0 w-4 h-4 flex items-center justify-center">
                {isDone || allDone ? (
                  <div className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] text-white" style={{ background: '#3FAF7A' }}>
                    &#x2713;
                  </div>
                ) : isActive ? (
                  <div className="w-3 h-3 rounded-full animate-pulse" style={{ background: '#3FAF7A' }} />
                ) : (
                  <div className="w-3 h-3 rounded-full" style={{ background: '#E2E8F0' }} />
                )}
              </div>
              {/* Label */}
              <span
                className="text-[11px]"
                style={{
                  color: isDone || allDone ? '#2D3748' : isActive ? '#0A1E2F' : '#A0AEC0',
                  fontWeight: isActive ? 600 : 400,
                }}
              >
                {label}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
