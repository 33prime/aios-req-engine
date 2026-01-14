/**
 * ReadinessModal Component
 *
 * Unified readiness assessment combining:
 * - Baseline completeness (PRD, features, personas, VP)
 * - Prototype readiness (evidence, gaps, confirmations)
 * - Actionable blockers, warnings, and recommendations
 *
 * Triggered by clicking readiness score in Overview tab
 */

'use client'

import { useState } from 'react'
import {
  X,
  CheckCircle,
  AlertTriangle,
  XCircle,
  FileText,
  Target,
  Users,
  Zap,
  Lightbulb,
  TrendingUp,
  AlertCircle,
} from 'lucide-react'

interface ReadinessModalProps {
  projectId: string
  isOpen: boolean
  onClose: () => void
  readinessData?: {
    score: number
    readiness_level: string
    blockers: string[]
    warnings: string[]
    recommendations: string[]
    breakdown?: {
      features: { score: number; issues: string[] }
      personas: { score: number; issues: string[] }
      vp_coverage: { score: number; issues: string[] }
      evidence: { score: number; issues: string[] }
    }
  } | null
}

export function ReadinessModal({ projectId, isOpen, onClose, readinessData }: ReadinessModalProps) {
  const [activeSection, setActiveSection] = useState<'overview' | 'breakdown' | 'actions'>('overview')

  if (!isOpen || !readinessData) return null

  const getReadinessIcon = () => {
    if (readinessData.score >= 80) return <CheckCircle className="h-16 w-16 text-green-600" />
    if (readinessData.score >= 60) return <AlertCircle className="h-16 w-16 text-yellow-600" />
    return <XCircle className="h-16 w-16 text-red-600" />
  }

  const getReadinessColor = () => {
    if (readinessData.score >= 80) return 'text-green-600'
    if (readinessData.score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getReadinessMessage = () => {
    switch (readinessData.readiness_level) {
      case 'ready':
        return '✅ Ready for prototype implementation'
      case 'almost_ready':
        return '⚠️ Almost ready - address warnings'
      case 'needs_work':
        return '🔧 Significant work needed'
      case 'not_ready':
        return '❌ Not ready - address blockers'
      default:
        return 'Assessment complete'
    }
  }

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div>
              <h2 className="text-2xl font-bold text-ui-bodyText">Prototype Readiness Assessment</h2>
              <p className="text-sm text-ui-supportText mt-1">
                Comprehensive analysis of your project's implementation readiness
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              aria-label="Close"
            >
              <X className="h-5 w-5 text-ui-supportText" />
            </button>
          </div>

          {/* Section Tabs */}
          <div className="flex border-b border-gray-200">
            <TabButton
              label="Overview"
              active={activeSection === 'overview'}
              onClick={() => setActiveSection('overview')}
            />
            <TabButton
              label="Component Breakdown"
              active={activeSection === 'breakdown'}
              onClick={() => setActiveSection('breakdown')}
            />
            <TabButton
              label="Action Items"
              active={activeSection === 'actions'}
              onClick={() => setActiveSection('actions')}
              count={readinessData.blockers.length + readinessData.warnings.length}
            />
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-6">
            {activeSection === 'overview' && (
              <OverviewSection
                score={readinessData.score}
                level={readinessData.readiness_level}
                icon={getReadinessIcon()}
                color={getReadinessColor()}
                message={getReadinessMessage()}
                breakdown={readinessData.breakdown}
              />
            )}

            {activeSection === 'breakdown' && readinessData.breakdown && (
              <BreakdownSection breakdown={readinessData.breakdown} />
            )}

            {activeSection === 'actions' && (
              <ActionsSection
                blockers={readinessData.blockers}
                warnings={readinessData.warnings}
                recommendations={readinessData.recommendations}
              />
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center justify-between">
              <div className="text-sm text-ui-supportText">
                Last assessed: {new Date().toLocaleString()}
              </div>
              <button
                onClick={onClose}
                className="px-4 py-2 bg-brand-primary hover:bg-brand-primaryHover text-white rounded-lg font-medium transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

// Tab Button Component
function TabButton({
  label,
  active,
  onClick,
  count,
}: {
  label: string
  active: boolean
  onClick: () => void
  count?: number
}) {
  return (
    <button
      onClick={onClick}
      className={`px-6 py-3 font-medium text-sm border-b-2 transition-colors ${
        active
          ? 'border-brand-primary text-brand-primary'
          : 'border-transparent text-ui-supportText hover:text-ui-bodyText'
      }`}
    >
      {label}
      {count !== undefined && count > 0 && (
        <span
          className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
            active ? 'bg-brand-primary/10 text-brand-primary' : 'bg-gray-100 text-gray-600'
          }`}
        >
          {count}
        </span>
      )}
    </button>
  )
}

// Overview Section
function OverviewSection({
  score,
  level,
  icon,
  color,
  message,
  breakdown,
}: {
  score: number
  level: string
  icon: React.ReactNode
  color: string
  message: string
  breakdown?: any
}) {
  return (
    <div className="space-y-6">
      {/* Score Display */}
      <div className="text-center py-8">
        <div className="flex justify-center mb-4">{icon}</div>
        <div className="flex items-baseline justify-center gap-3 mb-2">
          <span className={`text-6xl font-bold ${color}`}>{score}</span>
          <span className="text-3xl text-ui-supportText">/100</span>
        </div>
        <p className="text-lg text-ui-bodyText">{message}</p>
      </div>

      {/* Progress Bar */}
      <div className="max-w-2xl mx-auto">
        <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-500 ${
              score >= 80 ? 'bg-green-600' : score >= 60 ? 'bg-yellow-600' : 'bg-red-600'
            }`}
            style={{ width: `${score}%` }}
          />
        </div>
        <div className="flex justify-between text-xs text-ui-supportText mt-2">
          <span>0</span>
          <span className="text-yellow-600">60 - Almost Ready</span>
          <span className="text-green-600">80 - Ready</span>
          <span>100</span>
        </div>
      </div>

      {/* Quick Stats */}
      {breakdown && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-8">
          <QuickStat
            icon={<Target className="h-5 w-5" />}
            label="Features"
            score={breakdown.features?.score ?? 0}
            color={(breakdown.features?.score ?? 0) >= 80 ? 'green' : (breakdown.features?.score ?? 0) >= 60 ? 'yellow' : 'red'}
          />
          <QuickStat
            icon={<Users className="h-5 w-5" />}
            label="Personas"
            score={breakdown.personas?.score ?? 0}
            color={(breakdown.personas?.score ?? 0) >= 80 ? 'green' : (breakdown.personas?.score ?? 0) >= 60 ? 'yellow' : 'red'}
          />
          <QuickStat
            icon={<Zap className="h-5 w-5" />}
            label="Value Path"
            score={breakdown.vp_coverage?.score ?? 0}
            color={(breakdown.vp_coverage?.score ?? 0) >= 80 ? 'green' : (breakdown.vp_coverage?.score ?? 0) >= 60 ? 'yellow' : 'red'}
          />
          <QuickStat
            icon={<Lightbulb className="h-5 w-5" />}
            label="Evidence"
            score={breakdown.evidence?.score ?? 0}
            color={(breakdown.evidence?.score ?? 0) >= 80 ? 'green' : (breakdown.evidence?.score ?? 0) >= 60 ? 'yellow' : 'red'}
          />
        </div>
      )}
    </div>
  )
}

function QuickStat({
  icon,
  label,
  score,
  color,
}: {
  icon: React.ReactNode
  label: string
  score: number
  color: 'green' | 'yellow' | 'red'
}) {
  const colorClasses = {
    green: 'bg-green-50 border-green-200 text-green-700',
    yellow: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    red: 'bg-red-50 border-red-200 text-red-700',
  }

  return (
    <div className={`p-4 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <div className="text-2xl font-bold">{score}</div>
    </div>
  )
}

// Breakdown Section
function BreakdownSection({ breakdown }: { breakdown: any }) {
  return (
    <div className="space-y-6">
      <ComponentCard
        icon={<Target className="h-6 w-6 text-blue-600" />}
        title="Features"
        score={breakdown.features?.score ?? 0}
        issues={breakdown.features?.issues ?? []}
      />
      <ComponentCard
        icon={<Users className="h-6 w-6 text-purple-600" />}
        title="Personas"
        score={breakdown.personas?.score ?? 0}
        issues={breakdown.personas?.issues ?? []}
      />
      <ComponentCard
        icon={<Zap className="h-6 w-6 text-yellow-600" />}
        title="Value Path Coverage"
        score={breakdown.vp_coverage?.score ?? 0}
        issues={breakdown.vp_coverage?.issues ?? []}
      />
      {breakdown.evidence && (
        <ComponentCard
          icon={<Lightbulb className="h-6 w-6 text-green-600" />}
          title="Evidence & Research"
          score={breakdown.evidence?.score ?? 0}
          issues={breakdown.evidence?.issues ?? []}
        />
      )}
    </div>
  )
}

function ComponentCard({
  icon,
  title,
  score,
  issues,
}: {
  icon: React.ReactNode
  title: string
  score: number
  issues: string[]
}) {
  const getScoreColor = () => {
    if (score >= 80) return 'text-green-600'
    if (score >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getBarColor = () => {
    if (score >= 80) return 'bg-green-500'
    if (score >= 60) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          {icon}
          <div>
            <h3 className="font-semibold text-ui-bodyText">{title}</h3>
            <p className={`text-2xl font-bold ${getScoreColor()}`}>{score}/100</p>
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden mb-4">
        <div className={`h-full ${getBarColor()} transition-all duration-300`} style={{ width: `${score}%` }} />
      </div>

      {/* Issues */}
      {issues && issues.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
          <h4 className="text-sm font-semibold text-yellow-900 mb-2">Issues ({issues.length})</h4>
          <ul className="space-y-1">
            {issues.map((issue, idx) => (
              <li key={idx} className="text-sm text-yellow-800 flex items-start gap-2">
                <span className="text-yellow-600 mt-0.5">•</span>
                <span>{issue}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

// Actions Section
function ActionsSection({
  blockers,
  warnings,
  recommendations,
}: {
  blockers: string[]
  warnings: string[]
  recommendations: string[]
}) {
  return (
    <div className="space-y-6">
      {/* Blockers */}
      {blockers.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-5">
          <div className="flex items-start gap-3 mb-4">
            <XCircle className="h-6 w-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-900 text-lg">Critical Blockers ({blockers.length})</h3>
              <p className="text-sm text-red-800 mt-1">Must be resolved before implementation</p>
            </div>
          </div>
          <ul className="space-y-2">
            {blockers.map((blocker, idx) => (
              <li key={idx} className="flex items-start gap-3 p-3 bg-white rounded border border-red-200">
                <span className="text-red-600 font-bold text-lg">!</span>
                <span className="text-sm text-red-900 flex-1">{blocker}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-5">
          <div className="flex items-start gap-3 mb-4">
            <AlertTriangle className="h-6 w-6 text-yellow-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-yellow-900 text-lg">Warnings ({warnings.length})</h3>
              <p className="text-sm text-yellow-800 mt-1">Should be addressed for best results</p>
            </div>
          </div>
          <ul className="space-y-2">
            {warnings.map((warning, idx) => (
              <li key={idx} className="flex items-start gap-3 p-3 bg-white rounded border border-yellow-200">
                <span className="text-yellow-600 font-bold">⚠</span>
                <span className="text-sm text-yellow-900 flex-1">{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-5">
          <div className="flex items-start gap-3 mb-4">
            <TrendingUp className="h-6 w-6 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-blue-900 text-lg">
                Recommendations ({recommendations.length})
              </h3>
              <p className="text-sm text-blue-800 mt-1">Suggested next steps to improve readiness</p>
            </div>
          </div>
          <ul className="space-y-2">
            {recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-3 p-3 bg-white rounded border border-blue-200">
                <span className="text-blue-600 font-bold">→</span>
                <span className="text-sm text-blue-900 flex-1">{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* All Clear */}
      {blockers.length === 0 && warnings.length === 0 && recommendations.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-12 text-center">
          <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-green-900 mb-2">All Clear!</h3>
          <p className="text-green-800">No blockers, warnings, or recommendations at this time.</p>
        </div>
      )}
    </div>
  )
}
