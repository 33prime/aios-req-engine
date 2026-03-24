'use client'

import { useState, useEffect, useRef } from 'react'
import type { AgentType, ProcessingStep } from '@/types/workspace'

interface Props {
  agentType: AgentType
  agentName: string
  isRunning: boolean
  startedAt: number | null
  /** DB-backed processing steps with tool indicators. Falls back to generic steps if empty. */
  steps?: ProcessingStep[]
}

const STEPS_BY_TYPE: Record<AgentType, string[]> = {
  classifier: ['Reading input', 'Identifying entities', 'Classifying categories', 'Scoring confidence', 'Building output'],
  matcher: ['Reading input', 'Extracting candidates', 'Computing similarity', 'Ranking matches', 'Building output'],
  predictor: ['Reading input', 'Analyzing patterns', 'Generating predictions', 'Assessing risk', 'Building output'],
  watcher: ['Reading input', 'Scanning for alerts', 'Assessing severity', 'Recommending actions', 'Building output'],
  generator: ['Reading input', 'Synthesizing narrative', 'Structuring sections', 'Assessing confidence', 'Building output'],
  processor: ['Reading input', 'Extracting entities', 'Generating probes', 'Summarizing findings', 'Building output'],
  orchestrator: ['Planning approach', 'Coordinating sub-agents', 'Assembling results', 'Validating output', 'Delivering results'],
}

export function ProcessingAnimation({ agentType, agentName, isRunning, startedAt, steps: dbSteps }: Props) {
  const [activeStep, setActiveStep] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval>>()

  // Use DB steps if available, else fall back to type-based defaults
  const resolvedSteps: ProcessingStep[] = dbSteps?.length
    ? dbSteps
    : (STEPS_BY_TYPE[agentType] || STEPS_BY_TYPE.processor).map(label => ({ label }))

  useEffect(() => {
    if (isRunning) {
      setActiveStep(0)
      intervalRef.current = setInterval(() => {
        setActiveStep(prev => prev >= resolvedSteps.length - 1 ? prev : prev + 1)
      }, 350)
    } else {
      setActiveStep(resolvedSteps.length)
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [isRunning, resolvedSteps.length])

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
        {resolvedSteps.map((step, i) => {
          const isDone = i < activeStep
          const isActive = i === activeStep && isRunning
          const allDone = !isRunning && activeStep >= resolvedSteps.length

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
                className="text-[11px] flex-1"
                style={{
                  color: isDone || allDone ? '#2D3748' : isActive ? '#0A1E2F' : '#A0AEC0',
                  fontWeight: isActive ? 600 : 400,
                }}
              >
                {step.label}
              </span>
              {/* Tool indicator */}
              {step.tool_name && (isDone || allDone || isActive) && (
                <div className="flex items-center gap-1 flex-shrink-0 transition-opacity duration-300" style={{ opacity: isDone || allDone || isActive ? 1 : 0 }}>
                  {step.tool_icon && <span className="text-[10px]">{step.tool_icon}</span>}
                  <span
                    className="text-[8px] font-medium"
                    style={{ color: isActive ? '#3FAF7A' : '#A0AEC0' }}
                  >
                    {step.tool_name}
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
