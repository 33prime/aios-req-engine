/**
 * OnboardingModal Component
 *
 * Shows during new project setup when description is being processed.
 * Displays:
 * - How the Requirements Engine works (educational)
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
  prd_sections: number
  vp_steps: number
  features: number
  personas: number
}

type OnboardingStatus = 'analyzing' | 'building' | 'complete' | 'error'

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
          // extract_facts is ~30%, build_state is ~70%
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

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto">
          <div className="p-6">
            {/* Header */}
            <div className="text-center mb-6">
              <div className="w-14 h-14 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-7 h-7 text-blue-600" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900">
                Setting Up {projectName}
              </h2>
              <p className="text-gray-500 mt-2 text-sm">
                Our AI is analyzing your project description to create an initial structure.
              </p>
            </div>

            {/* How It Works Section */}
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <h3 className="font-medium text-gray-900 mb-3 text-sm">
                How the Requirements Engine Works
              </h3>
              <ul className="space-y-3 text-sm text-gray-600">
                <li className="flex items-start gap-3">
                  <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-blue-600 text-xs font-medium">1</span>
                  </div>
                  <span>
                    <strong className="text-gray-900">Signals</strong> — Add client emails, meeting notes, and documents
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-blue-600 text-xs font-medium">2</span>
                  </div>
                  <span>
                    <strong className="text-gray-900">AI Analysis</strong> — We extract facts, features, and personas
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-blue-600 text-xs font-medium">3</span>
                  </div>
                  <span>
                    <strong className="text-gray-900">Review & Refine</strong> — Confirm AI suggestions or edit them
                  </span>
                </li>
                <li className="flex items-start gap-3">
                  <div className="w-5 h-5 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-blue-600 text-xs font-medium">4</span>
                  </div>
                  <span>
                    <strong className="text-gray-900">Export</strong> — Generate PRDs, creative briefs, and more
                  </span>
                </li>
              </ul>
            </div>

            {/* Progress Section */}
            <div className="space-y-4 mb-6">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500">Progress</span>
                <span className="font-medium text-gray-900">{progress}%</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-500 to-blue-600 transition-all duration-500 ease-out"
                  style={{ width: `${progress}%` }}
                />
              </div>

              {/* Phase indicators */}
              <div className="flex justify-between text-sm pt-2">
                <div className={`flex items-center gap-1.5 ${
                  status === 'analyzing' ? 'text-blue-600' : 'text-green-600'
                }`}>
                  {status === 'analyzing' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  <span className="font-medium">Analyzing</span>
                </div>
                <div className={`flex items-center gap-1.5 ${
                  status === 'building' ? 'text-blue-600' :
                  status === 'complete' ? 'text-green-600' : 'text-gray-400'
                }`}>
                  {status === 'building' ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : status === 'complete' ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Circle className="w-4 h-4" />
                  )}
                  <span className="font-medium">Building</span>
                </div>
                <div className={`flex items-center gap-1.5 ${
                  status === 'complete' ? 'text-green-600' : 'text-gray-400'
                }`}>
                  {status === 'complete' ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Circle className="w-4 h-4" />
                  )}
                  <span className="font-medium">Ready</span>
                </div>
              </div>
            </div>

            {/* Results Section */}
            {status === 'complete' && result && (
              <div className="space-y-4">
                <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                  <h4 className="font-medium text-green-800 mb-3 flex items-center gap-2">
                    <Check className="w-5 h-5" />
                    Initial Setup Complete!
                  </h4>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="flex items-center gap-2 text-sm text-green-700">
                      <Target className="w-4 h-4" />
                      <span>{result.features} features</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-green-700">
                      <Users className="w-4 h-4" />
                      <span>{result.personas} personas</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-green-700">
                      <Zap className="w-4 h-4" />
                      <span>{result.vp_steps} value path steps</span>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-green-700">
                      <FileText className="w-4 h-4" />
                      <span>{result.prd_sections} PRD sections</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={onComplete}
                  className="w-full py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                >
                  Explore Your Project
                </button>
              </div>
            )}

            {/* Error Section */}
            {status === 'error' && (
              <div className="space-y-4">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
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
                  className="w-full py-3 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
                >
                  Continue Anyway
                </button>
              </div>
            )}

            {/* Processing message */}
            {(status === 'analyzing' || status === 'building') && (
              <p className="text-center text-sm text-gray-500">
                This usually takes 15-30 seconds...
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export default OnboardingModal
