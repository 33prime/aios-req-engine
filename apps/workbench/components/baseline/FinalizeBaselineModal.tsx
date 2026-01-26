/**
 * FinalizeBaselineModal Component
 *
 * Modal for finalizing baseline and switching to maintenance mode.
 * Phase 1: Surgical Updates for Features
 */

'use client'

import React, { useState } from 'react'
import { X, AlertTriangle, CheckCircle, Info, Lock } from 'lucide-react'

interface BaselineCompleteness {
  score: number
  breakdown: {
    features: number
    personas: number
    vp_steps: number
    constraints: number
  }
  counts: {
    features: number
    personas: number
    vp_steps: number
  }
  ready: boolean
  missing: string[]
}

interface FinalizeBaselineModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  completeness: BaselineCompleteness
  onFinalize: () => Promise<void>
}

export default function FinalizeBaselineModal({
  isOpen,
  onClose,
  projectId,
  completeness,
  onFinalize,
}: FinalizeBaselineModalProps) {
  const [finalizing, setFinalizing] = useState(false)
  const [confirmed, setConfirmed] = useState(false)

  if (!isOpen) return null

  const percentage = Math.round(completeness.score * 100)
  const isReady = completeness.ready

  const handleFinalize = async () => {
    if (!confirmed || finalizing) return

    try {
      setFinalizing(true)

      // If onFinalize callback is provided, use it
      if (onFinalize) {
        await onFinalize()
      } else {
        // Otherwise, call the API directly
        const apiBase = process.env.NEXT_PUBLIC_API_BASE || ''
        const response = await fetch(`${apiBase}/v1/projects/${projectId}/baseline/finalize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            confirmed_by: null, // TODO: Get from auth context
          }),
        })

        if (!response.ok) {
          throw new Error('Failed to finalize baseline')
        }
      }

      onClose()
    } catch (error) {
      console.error('Failed to finalize baseline:', error)
      alert('Failed to finalize baseline. Please try again.')
    } finally {
      setFinalizing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto" onClick={onClose}>
      <div className="flex min-h-screen items-center justify-center p-4">
        {/* Overlay */}
        <div className="fixed inset-0 bg-black bg-opacity-50 transition-opacity" />

        {/* Modal */}
        <div
          className="relative bg-white rounded-lg shadow-xl max-w-2xl w-full"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Lock className="h-6 w-6 text-blue-600" />
              <h2 className="text-xl font-bold text-gray-900">Finalize Baseline</h2>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {/* Completeness Score */}
            <div className={`rounded-lg border-2 p-4 mb-6 ${
              isReady ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'
            }`}>
              <div className="flex items-center gap-3 mb-3">
                {isReady ? (
                  <CheckCircle className="h-8 w-8 text-green-600" />
                ) : (
                  <AlertTriangle className="h-8 w-8 text-yellow-600" />
                )}
                <div>
                  <div className="text-3xl font-bold text-gray-900">{percentage}%</div>
                  <div className="text-sm text-gray-600">Baseline Completeness</div>
                </div>
              </div>

              {isReady ? (
                <p className="text-sm text-green-700">
                  ✅ Baseline is ready to finalize (≥ 75%)
                </p>
              ) : (
                <p className="text-sm text-yellow-700">
                  ⚠️ Baseline is below recommended threshold. You can still finalize, but consider
                  adding more content first.
                </p>
              )}
            </div>

            {/* What This Does */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">What This Does:</h3>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold mt-0.5">
                    1
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900">Switches to Maintenance Mode</div>
                    <div className="text-xs text-gray-600">
                      Project mode changes from "Initial" → "Maintenance"
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold mt-0.5">
                    2
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900">Enables Surgical Updates</div>
                    <div className="text-xs text-gray-600">
                      Future signals will apply precise, scoped patches instead of regenerating the entire PRD
                    </div>
                  </div>
                </div>

                <div className="flex items-start gap-2">
                  <div className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center text-xs font-bold mt-0.5">
                    3
                  </div>
                  <div>
                    <div className="text-sm font-medium text-gray-900">Locks Baseline</div>
                    <div className="text-xs text-gray-600">
                      The current PRD state becomes the foundation for future updates
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Component Breakdown */}
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Component Status:</h3>
              <div className="space-y-2">
                <ComponentStatusBar
                  label="Features"
                  score={completeness.breakdown.features}
                  count={completeness.counts.features}
                />
                <ComponentStatusBar
                  label="Personas"
                  score={completeness.breakdown.personas}
                  count={completeness.counts.personas}
                />
                <ComponentStatusBar
                  label="Value Path"
                  score={completeness.breakdown.vp_steps}
                  count={completeness.counts.vp_steps}
                />
              </div>
            </div>

            {/* Missing Components Warning */}
            {completeness.missing.length > 0 && (
              <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <Info className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-yellow-900 mb-1">Missing Components:</h4>
                    <ul className="text-xs text-yellow-800 space-y-1">
                      {completeness.missing.slice(0, 5).map((item, idx) => (
                        <li key={idx}>• {item}</li>
                      ))}
                      {completeness.missing.length > 5 && (
                        <li className="font-semibold">+ {completeness.missing.length - 5} more</li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* Confirmation Checkbox */}
            <label className="flex items-start gap-3 mb-6 cursor-pointer">
              <input
                type="checkbox"
                checked={confirmed}
                onChange={(e) => setConfirmed(e.target.checked)}
                className="mt-1 h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
              />
              <span className="text-sm text-gray-700">
                I understand that finalizing the baseline will switch the project to maintenance mode.
                Future signals will apply surgical updates instead of regenerating the PRD.
                {!isReady && ' I understand the baseline is below the recommended threshold but want to proceed anyway.'}
              </span>
            </label>

            {/* Actions */}
            <div className="flex gap-3">
              <button
                onClick={handleFinalize}
                disabled={!confirmed || finalizing}
                className="flex-1 px-4 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {finalizing ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                    Finalizing...
                  </>
                ) : (
                  <>
                    <Lock className="h-5 w-5" />
                    Finalize Baseline
                  </>
                )}
              </button>
              <button
                onClick={onClose}
                disabled={finalizing}
                className="px-4 py-3 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * ComponentStatusBar
 *
 * Progress bar for individual component score
 */
interface ComponentStatusBarProps {
  label: string
  score: number
  count?: number
}

function ComponentStatusBar({ label, score, count }: ComponentStatusBarProps) {
  const percentage = Math.round(score * 100)
  const barColor = percentage === 100 ? 'bg-green-500' : percentage >= 75 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-gray-700">{label}</span>
        <span className="font-semibold text-gray-900">
          {percentage}% {count !== undefined && `(${count})`}
        </span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
