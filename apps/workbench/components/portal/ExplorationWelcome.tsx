'use client'

import { useState } from 'react'
import { Sparkles } from 'lucide-react'

interface ExplorationWelcomeProps {
  projectName: string
  consultantName?: string | null
  epicCount: number
  onStart: () => void
  isModal?: boolean
}

export function ExplorationWelcome({
  projectName,
  consultantName,
  epicCount,
  onStart,
  isModal,
}: ExplorationWelcomeProps) {
  const [exiting, setExiting] = useState(false)

  const handleStart = () => {
    if (isModal) {
      setExiting(true)
      setTimeout(() => onStart(), 300)
    } else {
      onStart()
    }
  }

  const content = (
    <div className="max-w-md mx-auto text-center px-6">
      <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-brand-primary/20 flex items-center justify-center">
        <Sparkles className="w-8 h-8 text-brand-primary" />
      </div>

      <h1 className="text-2xl font-semibold text-white mb-3">
        Welcome to {projectName}
      </h1>

      <p className="text-base text-white/70 mb-2 leading-relaxed">
        Your prototype is ready for you to explore.
        {consultantName && ` ${consultantName} has`}
        {!consultantName && ' We have'} prepared {epicCount} key area{epicCount !== 1 ? 's' : ''} of
        your vision for you to review.
      </p>

      <p className="text-sm text-white/50 mb-8">
        For each area, you&apos;ll see what we&apos;ve built and the assumptions behind it.
        Tell us what&apos;s great, what needs refining, or ask a question.
      </p>

      <button
        onClick={handleStart}
        className="px-8 py-3.5 bg-brand-primary text-white text-base font-medium rounded-xl hover:bg-brand-primary-hover transition-all shadow-lg shadow-brand-primary/25"
      >
        Explore Your Vision
      </button>

      <p className="mt-6 text-xs text-white/30">
        Takes about 5-10 minutes
      </p>
    </div>
  )

  if (isModal) {
    return (
      <div
        className={`fixed inset-0 z-50 flex items-center justify-center backdrop-blur-lg bg-[#0A1E2F]/80 transition-opacity duration-300 ${
          exiting ? 'opacity-0' : 'opacity-100'
        }`}
      >
        {content}
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-80px)] bg-gradient-to-b from-[#0A1E2F] to-[#15314A]">
      {content}
    </div>
  )
}
