'use client'

import { useState } from 'react'
import { CheckCircle, Circle, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui'

type LifecycleStage = 'discovered' | 'refined' | 'confirmed'

interface Feature {
  id: string
  name: string
  lifecycle_stage: LifecycleStage
  confirmed_evidence?: any[]
  confirmation_date?: string
  details_updated_at?: string
}

interface FeatureLifecycleViewProps {
  feature: Feature
  onUpdateLifecycle?: (stage: LifecycleStage, evidence?: any[]) => Promise<void>
  readonly?: boolean
}

const LIFECYCLE_STAGES: { stage: LifecycleStage; label: string; color: string }[] = [
  { stage: 'discovered', label: 'Discovered', color: 'blue' },
  { stage: 'refined', label: 'Refined', color: 'purple' },
  { stage: 'confirmed', label: 'Confirmed', color: 'green' },
]

export default function FeatureLifecycleView({
  feature,
  onUpdateLifecycle,
  readonly = false,
}: FeatureLifecycleViewProps) {
  const [updating, setUpdating] = useState(false)
  const [showEvidenceInput, setShowEvidenceInput] = useState(false)
  const [evidenceText, setEvidenceText] = useState('')

  const currentStageIndex = LIFECYCLE_STAGES.findIndex((s) => s.stage === feature.lifecycle_stage)

  const handleStageClick = async (stage: LifecycleStage) => {
    if (readonly || !onUpdateLifecycle || updating) return

    // Can't go backwards in lifecycle
    const targetIndex = LIFECYCLE_STAGES.findIndex((s) => s.stage === stage)
    if (targetIndex < currentStageIndex) return

    // If confirming, show evidence input
    if (stage === 'confirmed') {
      setShowEvidenceInput(true)
      return
    }

    // Update directly for other stages
    try {
      setUpdating(true)
      await onUpdateLifecycle(stage)
    } catch (error) {
      console.error('Failed to update lifecycle:', error)
    } finally {
      setUpdating(false)
    }
  }

  const handleConfirmWithEvidence = async () => {
    if (!onUpdateLifecycle || updating) return

    try {
      setUpdating(true)
      const evidence = evidenceText.trim()
        ? [{ note: evidenceText, timestamp: new Date().toISOString() }]
        : []
      await onUpdateLifecycle('confirmed', evidence)
      setShowEvidenceInput(false)
      setEvidenceText('')
    } catch (error) {
      console.error('Failed to confirm feature:', error)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Lifecycle Progress Bar */}
      <div className="flex items-center justify-between">
        {LIFECYCLE_STAGES.map((stage, index) => {
          const isActive = index <= currentStageIndex
          const isCurrent = stage.stage === feature.lifecycle_stage
          const isClickable = !readonly && index > currentStageIndex && onUpdateLifecycle

          return (
            <div key={stage.stage} className="flex-1 flex items-center">
              {/* Stage Circle */}
              <button
                onClick={() => isClickable && handleStageClick(stage.stage)}
                disabled={!isClickable || updating}
                className={`relative flex flex-col items-center flex-1 ${
                  isClickable && !updating ? 'cursor-pointer hover:opacity-80' : 'cursor-default'
                }`}
              >
                {/* Circle Icon */}
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-colors ${
                    isActive
                      ? isCurrent
                        ? `bg-${stage.color}-600 border-${stage.color}-600 text-white`
                        : `bg-${stage.color}-100 border-${stage.color}-600 text-${stage.color}-700`
                      : 'bg-gray-100 border-gray-300 text-gray-400'
                  }`}
                >
                  {isActive ? (
                    <CheckCircle className="h-5 w-5" />
                  ) : (
                    <Circle className="h-5 w-5" />
                  )}
                </div>

                {/* Stage Label */}
                <div
                  className={`mt-2 text-xs font-medium ${
                    isActive ? `text-${stage.color}-700` : 'text-gray-500'
                  }`}
                >
                  {stage.label}
                </div>

                {/* Current Badge */}
                {isCurrent && (
                  <div className={`mt-1 text-xs px-2 py-0.5 rounded-full bg-${stage.color}-100 text-${stage.color}-700`}>
                    Current
                  </div>
                )}
              </button>

              {/* Connector Line */}
              {index < LIFECYCLE_STAGES.length - 1 && (
                <div
                  className={`h-0.5 flex-1 transition-colors ${
                    index < currentStageIndex ? `bg-${stage.color}-600` : 'bg-gray-300'
                  }`}
                  style={{ marginTop: '-20px' }}
                />
              )}
            </div>
          )
        })}
      </div>

      {/* Evidence Input Modal */}
      {showEvidenceInput && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-2 mb-3">
            <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="font-semibold text-gray-900 mb-1">Confirm Feature</h4>
              <p className="text-sm text-gray-700 mb-3">
                You are about to confirm this feature. Optionally add evidence or notes to support this confirmation.
              </p>

              <textarea
                value={evidenceText}
                onChange={(e) => setEvidenceText(e.target.value)}
                placeholder="Evidence or notes (optional)..."
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-green-500"
                rows={3}
              />

              <div className="flex gap-2 mt-3">
                <Button
                  variant="primary"
                  onClick={handleConfirmWithEvidence}
                  disabled={updating}
                  className="bg-green-600 hover:bg-green-700"
                >
                  {updating ? 'Confirming...' : 'Confirm Feature'}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    setShowEvidenceInput(false)
                    setEvidenceText('')
                  }}
                  disabled={updating}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Details */}
      {feature.lifecycle_stage === 'confirmed' && feature.confirmation_date && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h5 className="text-sm font-semibold text-green-900 mb-1">Confirmed</h5>
              <p className="text-xs text-green-700">
                Confirmed on {new Date(feature.confirmation_date).toLocaleString()}
              </p>

              {/* Show Evidence */}
              {feature.confirmed_evidence && feature.confirmed_evidence.length > 0 && (
                <div className="mt-2 space-y-1">
                  {feature.confirmed_evidence.map((evidence, idx) => (
                    <div key={idx} className="text-sm text-green-800 italic">
                      "{evidence.note || JSON.stringify(evidence)}"
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Enrichment Status */}
      {feature.details_updated_at && (
        <div className="text-xs text-gray-500">
          Last enriched: {new Date(feature.details_updated_at).toLocaleString()}
        </div>
      )}
    </div>
  )
}
