'use client'

import React, { useEffect, useState } from 'react'

interface CreationAnimationProps {
  projectName: string
  onComplete?: () => void
}

const phases = [
  { text: 'Initializing project...', progress: 30 },
  { text: 'Setting up workspace...', progress: 60 },
  { text: 'Launching research agents...', progress: 90 },
  { text: 'Almost ready...', progress: 100 },
]

export function CreationAnimation({ projectName, onComplete }: CreationAnimationProps) {
  const [currentPhase, setCurrentPhase] = useState(0)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    // Animate progress smoothly
    const progressInterval = setInterval(() => {
      setProgress((prev) => {
        const target = phases[currentPhase].progress
        if (prev >= target) return target
        return Math.min(prev + 2, target)
      })
    }, 30)

    return () => clearInterval(progressInterval)
  }, [currentPhase])

  useEffect(() => {
    // Advance phases
    const phaseIntervals = [800, 700, 700, 500] // Time for each phase
    let totalDelay = 0

    const timeouts = phases.map((_, index) => {
      if (index === 0) return null
      totalDelay += phaseIntervals[index - 1]
      return setTimeout(() => {
        setCurrentPhase(index)
      }, totalDelay)
    })

    // Trigger complete callback
    totalDelay += phaseIntervals[phaseIntervals.length - 1]
    const completeTimeout = setTimeout(() => {
      onComplete?.()
    }, totalDelay)

    return () => {
      timeouts.forEach((t) => t && clearTimeout(t))
      clearTimeout(completeTimeout)
    }
  }, [onComplete])

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md text-center">
        {/* Animated Logo/Spinner */}
        <div className="mb-6 flex justify-center">
          <div className="relative w-20 h-20">
            {/* Outer rotating ring */}
            <div className="absolute inset-0 rounded-full border-4 border-gray-200"></div>
            <div
              className="absolute inset-0 rounded-full border-4 border-transparent border-t-[#009b87] animate-spin"
              style={{ animationDuration: '1s' }}
            ></div>
            {/* Inner pulsing circle */}
            <div className="absolute inset-3 rounded-full bg-gradient-to-br from-[#009b87] to-emerald-400 animate-pulse"></div>
            {/* Center dot */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-4 h-4 rounded-full bg-white"></div>
            </div>
          </div>
        </div>

        {/* Project name */}
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Creating &ldquo;{projectName}&rdquo;
        </h2>

        {/* Current phase text */}
        <p className="text-gray-500 mb-6 h-6 transition-all duration-300">
          {phases[currentPhase].text}
        </p>

        {/* Progress bar */}
        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden mb-4">
          <div
            className="h-full bg-gradient-to-r from-[#009b87] to-emerald-400 rounded-full transition-all duration-300 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Progress percentage */}
        <p className="text-sm text-gray-400">
          {progress}%
        </p>
      </div>
    </div>
  )
}
