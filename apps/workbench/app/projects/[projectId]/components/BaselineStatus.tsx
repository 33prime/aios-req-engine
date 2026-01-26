/**
 * BaselineStatus Component
 *
 * Displays baseline completeness score and allows finalization of baseline.
 * Phase 0 - Foundation: Baseline readiness indicator
 */

'use client'

import React, { useState } from 'react'
import { CheckCircle, AlertCircle, Info, Target, Users, FileText, Zap, Lock } from 'lucide-react'

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

interface BaselineStatusProps {
  projectId: string
  completeness: BaselineCompleteness | null
  prdMode: 'initial' | 'maintenance'
  onFinalize?: () => Promise<void>
  onRefresh?: () => Promise<void>
  loading?: boolean
  className?: string
}

export default function BaselineStatus({
  projectId,
  completeness,
  prdMode,
  onFinalize,
  onRefresh,
  loading = false,
  className = '',
}: BaselineStatusProps) {
  const [finalizing, setFinalizing] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  const handleFinalize = async () => {
    if (!onFinalize || !completeness?.ready) return

    const confirmed = window.confirm(
      `Are you sure you want to finalize the baseline?\n\n` +
      `This will switch the project to Maintenance Mode, enabling surgical updates ` +
      `instead of full PRD regeneration.\n\n` +
      `You can always rebuild the baseline if needed.`
    )

    if (!confirmed) return

    try {
      setFinalizing(true)
      await onFinalize()
    } catch (error) {
      console.error('Failed to finalize baseline:', error)
      alert('Failed to finalize baseline. Please try again.')
    } finally {
      setFinalizing(false)
    }
  }

  if (loading || !completeness) {
    return (
      <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  const percentage = Math.round(completeness.score * 100)
  const isReady = completeness.ready
  const isMaintenanceMode = prdMode === 'maintenance'

  // Color coding based on score
  const getScoreColor = () => {
    if (percentage >= 75) return 'text-green-600'
    if (percentage >= 50) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getScoreBgColor = () => {
    if (percentage >= 75) return 'bg-green-50 border-green-200'
    if (percentage >= 50) return 'bg-yellow-50 border-yellow-200'
    return 'bg-red-50 border-red-200'
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <h3 className="text-lg font-semibold text-gray-900">Baseline Status</h3>
              {isMaintenanceMode && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  <Lock className="h-3 w-3" />
                  Maintenance Mode
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600">
              {isMaintenanceMode
                ? 'Baseline finalized. Receiving surgical updates.'
                : 'Track your PRD baseline completeness and finalize when ready.'}
            </p>
          </div>

          {onRefresh && !isMaintenanceMode && (
            <button
              onClick={onRefresh}
              disabled={loading}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Refresh
            </button>
          )}
        </div>
      </div>

      {/* Score Display */}
      <div className={`p-6 border-b border-gray-200 ${getScoreBgColor()}`}>
        <div className="flex items-center gap-4">
          <div className="flex-shrink-0">
            {isReady ? (
              <CheckCircle className="h-12 w-12 text-green-600" />
            ) : (
              <AlertCircle className="h-12 w-12 text-yellow-600" />
            )}
          </div>

          <div className="flex-1">
            <div className="flex items-baseline gap-2 mb-1">
              <span className={`text-4xl font-bold ${getScoreColor()}`}>{percentage}%</span>
              <span className="text-lg text-gray-600">complete</span>
            </div>

            {isReady ? (
              <p className="text-sm font-medium text-green-700">
                ✅ Ready to finalize baseline (≥ 75%)
              </p>
            ) : (
              <p className="text-sm font-medium text-gray-700">
                ⚠️ Need {75 - percentage}% more to finalize baseline
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Component Breakdown */}
      <div className="p-6 space-y-3">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-900">Component Scores</h4>
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            {showDetails ? 'Hide details' : 'Show details'}
          </button>
        </div>

        {/* Features */}
        <ScoreBar
          icon={<Target className="h-4 w-4" />}
          label="Features"
          score={completeness.breakdown.features}
          count={completeness.counts.features}
          countLabel="features"
          minCount={3}
        />

        {/* Personas */}
        <ScoreBar
          icon={<Users className="h-4 w-4" />}
          label="Personas"
          score={completeness.breakdown.personas}
          count={completeness.counts.personas}
          countLabel="personas"
          minCount={2}
        />

        {/* VP Steps */}
        <ScoreBar
          icon={<Zap className="h-4 w-4" />}
          label="Value Path"
          score={completeness.breakdown.vp_steps}
          count={completeness.counts.vp_steps}
          countLabel="steps"
          minCount={3}
        />

        {/* Constraints */}
        <ScoreBar
          icon={<Info className="h-4 w-4" />}
          label="Constraints"
          score={completeness.breakdown.constraints}
          count={null}
          countLabel=""
        />
      </div>

      {/* Missing Components */}
      {showDetails && completeness.missing.length > 0 && (
        <div className="px-6 pb-6 pt-2">
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h5 className="text-sm font-semibold text-yellow-900 mb-2">Missing Components:</h5>
            <ul className="space-y-1">
              {completeness.missing.map((item, idx) => (
                <li key={idx} className="text-sm text-yellow-800 flex items-start gap-2">
                  <span className="text-yellow-600 mt-0.5">•</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Finalize Button */}
      {!isMaintenanceMode && isReady && onFinalize && (
        <div className="p-6 bg-green-50 border-t border-green-200">
          <button
            onClick={handleFinalize}
            disabled={finalizing}
            className="w-full px-4 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {finalizing ? (
              <>
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                Finalizing...
              </>
            ) : (
              <>
                <CheckCircle className="h-5 w-5" />
                Finalize Baseline → Enable Surgical Updates
              </>
            )}
          </button>
          <p className="text-xs text-gray-600 mt-2 text-center">
            This will switch to Maintenance Mode for precise, evidence-bound updates
          </p>
        </div>
      )}

      {/* Maintenance Mode Info */}
      {isMaintenanceMode && (
        <div className="p-6 bg-blue-50 border-t border-blue-200">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h5 className="text-sm font-semibold text-blue-900 mb-1">
                Maintenance Mode Active
              </h5>
              <p className="text-sm text-blue-800 mb-2">
                The baseline is finalized. New signals will generate surgical patches instead of
                regenerating the entire PRD.
              </p>
              <p className="text-xs text-blue-700">
                Contact an admin if you need to rebuild the baseline from scratch.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * ScoreBar Component
 *
 * Individual score progress bar for a component
 */
interface ScoreBarProps {
  icon: React.ReactNode
  label: string
  score: number
  count: number | null
  countLabel: string
  minCount?: number
}

function ScoreBar({ icon, label, score, count, countLabel, minCount }: ScoreBarProps) {
  const percentage = Math.round(score * 100)

  const getBarColor = () => {
    if (percentage === 100) return 'bg-green-500'
    if (percentage >= 75) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <span className="text-gray-600">{icon}</span>
          <span className="font-medium text-gray-900">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          {count !== null && (
            <span className="text-xs text-gray-600">
              {count} {countLabel}
              {minCount && ` / ${minCount} min`}
            </span>
          )}
          <span className={`text-sm font-semibold ${percentage === 100 ? 'text-green-600' : 'text-gray-700'}`}>
            {percentage}%
          </span>
        </div>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full ${getBarColor()} transition-all duration-300`}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
