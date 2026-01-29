/**
 * OnboardingModal Component
 *
 * Shows during new project setup when description is being processed.
 * Displays:
 * - "Ready to Go AI Engine" with animated pipeline visualization
 * - Progress indicators for extract_facts → build_state
 * - Final entity counts when complete
 */

'use client'

import { useState, useEffect } from 'react'
import {
  Sparkles,
  Loader2,
  Check,
  Circle,
  AlertCircle,
  FileText,
  Users,
  Target,
  Zap,
  Brain,
  Rocket,
  RefreshCw,
  Code,
  ArrowRight,
} from 'lucide-react'
import { getJobStatus } from '@/lib/api'

interface OnboardingModalProps {
  isOpen: boolean
  projectId: string
  projectName: string
  jobId: string
  onComplete: () => void
}

interface OnboardingResult {
  facts_extracted: number
  vp_steps: number
  features: number
  personas: number
}

type OnboardingStatus = 'analyzing' | 'building' | 'complete' | 'error'

// Animation keyframes CSS
const animationStyles = `
  @keyframes pulse-glow {
    0%, 100% { opacity: 0.4; transform: scale(1); }
    50% { opacity: 1; transform: scale(1.1); }
  }
  @keyframes flow-right {
    0% { transform: translateX(-100%); opacity: 0; }
    20% { opacity: 1; }
    80% { opacity: 1; }
    100% { transform: translateX(400%); opacity: 0; }
  }
  @keyframes float {
    0%, 100% { transform: translateY(0px); }
    50% { transform: translateY(-8px); }
  }
  @keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }
  @keyframes check-pop {
    0% { transform: scale(0); opacity: 0; }
    50% { transform: scale(1.2); }
    100% { transform: scale(1); opacity: 1; }
  }
  @keyframes particle {
    0% { transform: translateY(0) rotate(0deg); opacity: 1; }
    100% { transform: translateY(-100px) rotate(720deg); opacity: 0; }
  }
`

// Pipeline step component
function PipelineStep({
  icon: Icon,
  label,
  description,
  isActive,
  isComplete,
  delay,
}: {
  icon: React.ElementType
  label: string
  description: string
  isActive: boolean
  isComplete: boolean
  delay: number
}) {
  return (
    <div
      className={`flex items-start gap-3 transition-all duration-500`}
      style={{
        animationDelay: `${delay}ms`,
        opacity: isActive || isComplete ? 1 : 0.4,
      }}
    >
      <div
        className={`
          w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-500
          ${isComplete
            ? 'bg-[#044159] text-white'
            : isActive
              ? 'bg-[#88BABF]/30 text-[#044159] animate-[pulse-glow_2s_ease-in-out_infinite]'
              : 'bg-gray-100 text-gray-400'}
        `}
      >
        {isComplete ? (
          <Check className="w-5 h-5 animate-[check-pop_0.3s_ease-out]" />
        ) : (
          <Icon className={`w-5 h-5 ${isActive ? 'animate-pulse' : ''}`} />
        )}
      </div>
      <div className="flex-1 pt-1">
        <span className={`font-medium text-sm ${isActive || isComplete ? 'text-[#011F26]' : 'text-gray-400'}`}>
          {label}
        </span>
        <p className={`text-xs mt-0.5 ${isActive || isComplete ? 'text-gray-500' : 'text-gray-300'}`}>
          {description}
        </p>
      </div>
    </div>
  )
}

// Animated particles for celebration
function ConfettiParticle({ color, left, delay }: { color: string; left: number; delay: number }) {
  return (
    <div
      className="absolute w-2 h-2 rounded-full"
      style={{
        backgroundColor: color,
        left: `${left}%`,
        bottom: 0,
        animation: `particle 1.5s ease-out ${delay}s forwards`,
      }}
    />
  )
}

export function OnboardingModal({
  isOpen,
  projectId,
  projectName,
  jobId,
  onComplete,
}: OnboardingModalProps) {
  const [status, setStatus] = useState<OnboardingStatus>('analyzing')
  const [progress, setProgress] = useState(10)
  const [result, setResult] = useState<OnboardingResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showConfetti, setShowConfetti] = useState(false)

  // Poll job status
  useEffect(() => {
    if (!jobId || !isOpen) return

    let pollCount = 0
    const maxPolls = 60 // 2 minutes max

    const pollInterval = setInterval(async () => {
      pollCount++

      try {
        const job = await getJobStatus(jobId)

        if (job.status === 'processing') {
          // Estimate progress based on poll count
          const estimated = Math.min(10 + pollCount * 5, 85)
          setProgress(estimated)

          // Switch to "building" phase after a bit
          if (pollCount > 3) {
            setStatus('building')
          }
        } else if (job.status === 'completed') {
          setStatus('complete')
          setProgress(100)
          setResult(job.output)
          setShowConfetti(true)
          clearInterval(pollInterval)
        } else if (job.status === 'failed') {
          setStatus('error')
          setError(job.error || 'An error occurred during setup')
          clearInterval(pollInterval)
        }

        // Timeout after max polls
        if (pollCount >= maxPolls) {
          setStatus('error')
          setError('Setup is taking longer than expected. You can continue and check back later.')
          clearInterval(pollInterval)
        }
      } catch (err) {
        console.error('Failed to poll job status:', err)
      }
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [jobId, isOpen])

  if (!isOpen) return null

  const steps = [
    { icon: FileText, label: 'Signals', description: 'Emails, notes, documents' },
    { icon: Brain, label: 'AI Analysis', description: 'Extract insights & structure' },
    { icon: RefreshCw, label: 'Review & Refine', description: 'Confirm or edit suggestions' },
    { icon: Rocket, label: 'Build Prototype', description: 'Generate initial prototype' },
    { icon: Target, label: 'Refine', description: 'Iterate based on feedback' },
    { icon: Code, label: 'Build MVP', description: 'Production-ready product' },
  ]

  const confettiColors = ['#044159', '#88BABF', '#F2E4BB', '#011F26']

  return (
    <>
      <style>{animationStyles}</style>

      {/* Backdrop with brand gradient */}
      <div className="fixed inset-0 bg-gradient-to-br from-[#011F26]/60 via-[#044159]/50 to-[#88BABF]/40 z-40 backdrop-blur-sm" />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto border border-[#88BABF]/20">
          <div className="p-6">
            {/* Header with animated gradient */}
            <div className="text-center mb-6">
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 relative overflow-hidden"
                style={{
                  background: 'linear-gradient(135deg, #044159, #88BABF, #044159)',
                  backgroundSize: '200% 200%',
                  animation: 'gradient-shift 3s ease infinite',
                }}
              >
                <Sparkles className="w-8 h-8 text-white animate-[float_3s_ease-in-out_infinite]" />
              </div>
              <h2 className="text-xl font-semibold text-[#011F26]">
                Setting Up {projectName}
              </h2>
              <p className="text-gray-500 mt-2 text-sm">
                Your AI engine is analyzing your project to create the initial structure.
              </p>
            </div>

            {/* Ready to Go AI Engine Section */}
            <div className="bg-gradient-to-br from-[#044159]/5 to-[#88BABF]/10 rounded-xl p-5 mb-6 border border-[#88BABF]/20">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-[#011F26] text-sm flex items-center gap-2">
                  <Zap className="w-4 h-4 text-[#044159]" />
                  Ready to Go AI Engine
                </h3>
                <span className="text-xs font-medium text-[#044159] bg-[#88BABF]/20 px-2 py-1 rounded-full">
                  In hours, not months
                </span>
              </div>

              {/* Animated Pipeline */}
              <div className="relative">
                {/* Flow line */}
                <div className="absolute left-5 top-5 bottom-5 w-0.5 bg-gradient-to-b from-[#044159] via-[#88BABF] to-[#044159]/20" />

                {/* Animated dot flowing through */}
                {(status === 'analyzing' || status === 'building') && (
                  <div
                    className="absolute left-4 w-3 h-3 bg-[#044159] rounded-full shadow-lg shadow-[#044159]/50"
                    style={{
                      animation: 'flow-right 3s ease-in-out infinite',
                      top: status === 'analyzing' ? '20%' : '60%',
                    }}
                  />
                )}

                <div className="space-y-4 relative">
                  {steps.map((step, index) => (
                    <PipelineStep
                      key={step.label}
                      {...step}
                      isActive={
                        (status === 'analyzing' && index <= 1) ||
                        (status === 'building' && index <= 2) ||
                        (status === 'complete')
                      }
                      isComplete={status === 'complete'}
                      delay={index * 100}
                    />
                  ))}
                </div>
              </div>
            </div>

            {/* Progress Section */}
            <div className="space-y-3 mb-6">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500 font-medium">Progress</span>
                <span className="font-semibold text-[#044159]">{progress}%</span>
              </div>
              <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700 ease-out relative overflow-hidden"
                  style={{
                    width: `${progress}%`,
                    background: 'linear-gradient(90deg, #044159, #88BABF)',
                  }}
                >
                  {/* Shimmer effect */}
                  <div
                    className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent"
                    style={{ animation: 'flow-right 2s linear infinite' }}
                  />
                </div>
              </div>

              {/* Phase indicators */}
              <div className="flex justify-between text-xs pt-1">
                <div className={`flex items-center gap-1.5 ${
                  status === 'analyzing' ? 'text-[#044159]' : 'text-[#044159]'
                }`}>
                  {status === 'analyzing' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <Check className="w-3.5 h-3.5" />
                  )}
                  <span className="font-medium">Analyzing</span>
                </div>
                <div className={`flex items-center gap-1.5 ${
                  status === 'building' ? 'text-[#044159]' :
                  status === 'complete' ? 'text-[#044159]' : 'text-gray-300'
                }`}>
                  {status === 'building' ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : status === 'complete' ? (
                    <Check className="w-3.5 h-3.5" />
                  ) : (
                    <Circle className="w-3.5 h-3.5" />
                  )}
                  <span className="font-medium">Building</span>
                </div>
                <div className={`flex items-center gap-1.5 ${
                  status === 'complete' ? 'text-[#044159]' : 'text-gray-300'
                }`}>
                  {status === 'complete' ? (
                    <Check className="w-3.5 h-3.5" />
                  ) : (
                    <Circle className="w-3.5 h-3.5" />
                  )}
                  <span className="font-medium">Ready</span>
                </div>
              </div>
            </div>

            {/* Results Section - Celebration State */}
            {status === 'complete' && result && (
              <div className="space-y-4 relative overflow-hidden">
                {/* Confetti particles */}
                {showConfetti && (
                  <div className="absolute inset-0 pointer-events-none">
                    {[...Array(12)].map((_, i) => (
                      <ConfettiParticle
                        key={i}
                        color={confettiColors[i % confettiColors.length]}
                        left={10 + (i * 7)}
                        delay={i * 0.1}
                      />
                    ))}
                  </div>
                )}

                <div
                  className="rounded-xl p-5 border-2"
                  style={{
                    background: 'linear-gradient(135deg, rgba(4, 65, 89, 0.05), rgba(136, 186, 191, 0.1))',
                    borderColor: '#044159',
                  }}
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 bg-[#044159] rounded-xl flex items-center justify-center">
                      <Rocket className="w-5 h-5 text-white animate-[float_2s_ease-in-out_infinite]" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-[#011F26]">
                        Your Project is Ready!
                      </h4>
                      <p className="text-xs text-gray-500">
                        AI engine has created your initial structure
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-white rounded-lg p-3 text-center shadow-sm border border-[#88BABF]/20">
                      <div className="text-2xl font-bold text-[#044159]">{result.features}</div>
                      <div className="text-xs text-gray-500 font-medium">Features</div>
                    </div>
                    <div className="bg-white rounded-lg p-3 text-center shadow-sm border border-[#88BABF]/20">
                      <div className="text-2xl font-bold text-[#044159]">{result.personas}</div>
                      <div className="text-xs text-gray-500 font-medium">Personas</div>
                    </div>
                    <div className="bg-white rounded-lg p-3 text-center shadow-sm border border-[#88BABF]/20">
                      <div className="text-2xl font-bold text-[#044159]">{result.vp_steps}</div>
                      <div className="text-xs text-gray-500 font-medium">VP Steps</div>
                    </div>
                  </div>
                </div>

                <button
                  onClick={onComplete}
                  className="w-full py-3.5 rounded-xl font-semibold text-white transition-all duration-300 flex items-center justify-center gap-2 group"
                  style={{
                    background: 'linear-gradient(135deg, #044159, #033344)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, #033344, #022233)'
                    e.currentTarget.style.transform = 'translateY(-1px)'
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(4, 65, 89, 0.3)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'linear-gradient(135deg, #044159, #033344)'
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                >
                  Explore Your Project
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            )}

            {/* Error Section */}
            {status === 'error' && (
              <div className="space-y-4">
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <div className="flex items-start gap-3">
                    <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="font-medium text-red-800 mb-1">Setup Issue</h4>
                      <p className="text-sm text-red-700">{error}</p>
                    </div>
                  </div>
                </div>
                <button
                  onClick={onComplete}
                  className="w-full py-3 bg-gray-600 text-white rounded-xl hover:bg-gray-700 transition-colors font-medium"
                >
                  Continue Anyway
                </button>
              </div>
            )}

            {/* Processing message */}
            {(status === 'analyzing' || status === 'building') && (
              <p className="text-center text-sm text-gray-400 flex items-center justify-center gap-2">
                <span className="inline-block w-1.5 h-1.5 bg-[#88BABF] rounded-full animate-pulse" />
                Your AI engine is working...
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export default OnboardingModal
