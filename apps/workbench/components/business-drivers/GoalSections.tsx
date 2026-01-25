'use client'

import { Target, TrendingUp, Zap, CheckCircle, Clock, Users, BarChart3, AlertTriangle } from 'lucide-react'

interface Evidence {
  chunk_id?: string
  excerpt?: string
  text?: string
  rationale?: string
}

interface BusinessDriver {
  id: string
  driver_type: 'kpi' | 'pain' | 'goal'
  description: string
  goal_timeframe?: string
  success_criteria?: string
  dependencies?: string
  owner?: string
  evidence?: Evidence[]
  baseline_value?: string
  target_value?: string
}

interface Feature {
  id: string
  name: string
  confirmation_status?: string
  category?: string
}

interface GoalDetailsSectionProps {
  driver: BusinessDriver
}

export function GoalDetailsSection({ driver }: GoalDetailsSectionProps) {
  const hasTimeframe = driver.goal_timeframe
  const hasCriteria = driver.success_criteria
  const hasDependencies = driver.dependencies
  const hasOwner = driver.owner

  if (!hasTimeframe && !hasCriteria && !hasDependencies && !hasOwner) {
    return null
  }

  // Parse success criteria into list if it contains bullet points, commas, or line breaks
  const parseCriteria = (criteria: string) => {
    if (!criteria) return []

    // Check for bullet points, numbered lists, or line breaks
    if (criteria.includes('\n') || criteria.includes('•') || criteria.match(/^\d+\./m)) {
      return criteria
        .split(/\n|•/)
        .map(c => c.trim())
        .filter(c => c && c.length > 0)
        .map(c => c.replace(/^\d+\.\s*/, '')) // Remove leading numbers
    }

    // Check for comma-separated or semicolon-separated
    if (criteria.includes(',') || criteria.includes(';')) {
      return criteria
        .split(/[,;]/)
        .map(c => c.trim())
        .filter(c => c && c.length > 0)
    }

    // Single criterion
    return [criteria]
  }

  const criteriaList = hasCriteria ? parseCriteria(driver.success_criteria!) : []

  // Parse dependencies
  const parseDependencies = (deps: string) => {
    if (!deps) return []

    if (deps.includes('\n') || deps.includes('•')) {
      return deps
        .split(/\n|•/)
        .map(d => d.trim())
        .filter(d => d && d.length > 0)
    }

    if (deps.includes(',') || deps.includes(';')) {
      return deps
        .split(/[,;]/)
        .map(d => d.trim())
        .filter(d => d && d.length > 0)
    }

    return [deps]
  }

  const dependenciesList = hasDependencies ? parseDependencies(driver.dependencies!) : []

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <Target className="h-3.5 w-3.5" />
        Achievement Criteria
      </h4>

      <div className="space-y-3">
        {/* Timeframe */}
        {hasTimeframe && (
          <div className="bg-emerald-50 rounded-lg p-3 border border-emerald-200">
            <div className="text-xs font-medium text-emerald-700 mb-1 flex items-center gap-1">
              <Clock className="h-3 w-3" />
              Target Timeframe
            </div>
            <div className="text-sm font-semibold text-emerald-900">{driver.goal_timeframe}</div>
          </div>
        )}

        {/* Success Criteria */}
        {hasCriteria && criteriaList.length > 0 && (
          <div>
            <div className="text-xs font-medium text-gray-700 mb-2 flex items-center gap-1">
              <CheckCircle className="h-3 w-3 text-green-600" />
              Success Criteria ({criteriaList.length})
            </div>
            <div className="space-y-1.5">
              {criteriaList.map((criterion, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 bg-green-50 rounded p-2.5 border border-green-100"
                >
                  <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{criterion}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Dependencies */}
        {hasDependencies && dependenciesList.length > 0 && (
          <div>
            <div className="text-xs font-medium text-gray-700 mb-2 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 text-amber-600" />
              Dependencies ({dependenciesList.length})
            </div>
            <div className="space-y-1.5">
              {dependenciesList.map((dependency, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 bg-amber-50 rounded p-2.5 border border-amber-100"
                >
                  <div className="w-2 h-2 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
                  <span className="text-sm text-gray-700">{dependency}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Owner */}
        {hasOwner && (
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1.5">Goal Owner</div>
            <div className="flex items-center gap-2 bg-gray-50 rounded p-2.5 border border-gray-200">
              <Users className="h-4 w-4 text-emerald-600" />
              <span className="text-sm font-medium text-gray-700">{driver.owner}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface ProgressSectionProps {
  driver: BusinessDriver
  supportingFeatures?: Feature[]
}

export function ProgressSection({ driver, supportingFeatures = [] }: ProgressSectionProps) {
  if (supportingFeatures.length === 0) {
    return null
  }

  const confirmedFeatures = supportingFeatures.filter(
    f => f.confirmation_status === 'confirmed_client' || f.confirmation_status === 'confirmed_consultant'
  )
  const totalFeatures = supportingFeatures.length
  const completionPercentage = totalFeatures > 0 ? Math.round((confirmedFeatures.length / totalFeatures) * 100) : 0

  const getProgressColor = (percentage: number) => {
    if (percentage >= 80) return 'bg-green-500'
    if (percentage >= 50) return 'bg-blue-500'
    if (percentage >= 25) return 'bg-yellow-500'
    return 'bg-gray-300'
  }

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <TrendingUp className="h-3.5 w-3.5" />
        Progress Toward This Goal
      </h4>

      <div className="bg-emerald-50 rounded-lg p-4 border border-emerald-200">
        {/* Progress Bar */}
        <div className="mb-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-emerald-700">Feature Completion</span>
            <span className="text-sm font-bold text-emerald-900">{completionPercentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className={`h-full ${getProgressColor(completionPercentage)} transition-all duration-300`}
              style={{ width: `${completionPercentage}%` }}
            />
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-2 text-center">
          <div>
            <div className="text-xs text-gray-600">Total Features</div>
            <div className="text-lg font-bold text-gray-900">{totalFeatures}</div>
          </div>
          <div>
            <div className="text-xs text-green-600">Confirmed</div>
            <div className="text-lg font-bold text-green-700">{confirmedFeatures.length}</div>
          </div>
          <div>
            <div className="text-xs text-blue-600">In Progress</div>
            <div className="text-lg font-bold text-blue-700">{totalFeatures - confirmedFeatures.length}</div>
          </div>
        </div>
      </div>
    </div>
  )
}

interface SupportingFeaturesSectionProps {
  driver: BusinessDriver
  supportingFeatures?: Feature[]
}

export function SupportingFeaturesSection({ driver, supportingFeatures = [] }: SupportingFeaturesSectionProps) {
  if (supportingFeatures.length === 0) {
    return null
  }

  const confirmedFeatures = supportingFeatures.filter(
    f => f.confirmation_status === 'confirmed_client' || f.confirmation_status === 'confirmed_consultant'
  )
  const draftFeatures = supportingFeatures.filter(
    f => !f.confirmation_status || f.confirmation_status === 'ai_generated' || f.confirmation_status === 'needs_client'
  )

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <Zap className="h-3.5 w-3.5" />
        Features Driving This Goal ({supportingFeatures.length})
      </h4>

      <div className="space-y-3">
        {/* Confirmed Features */}
        {confirmedFeatures.length > 0 && (
          <div>
            <div className="text-xs font-medium text-green-700 mb-2">
              ✅ Confirmed ({confirmedFeatures.length})
            </div>
            <div className="space-y-1.5">
              {confirmedFeatures.map((feature) => (
                <div
                  key={feature.id}
                  className="flex items-start gap-2 bg-green-50 rounded p-2.5 border border-green-200"
                >
                  <CheckCircle className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-green-900">{feature.name}</div>
                    {feature.category && (
                      <div className="text-xs text-green-700 mt-0.5">{feature.category}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Draft Features */}
        {draftFeatures.length > 0 && (
          <div>
            <div className="text-xs font-medium text-blue-700 mb-2">
              💡 Proposed ({draftFeatures.length})
            </div>
            <div className="space-y-1.5">
              {draftFeatures.map((feature) => (
                <div
                  key={feature.id}
                  className="flex items-start gap-2 bg-blue-50 rounded p-2.5 border border-blue-200"
                >
                  <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-blue-900">{feature.name}</div>
                    {feature.category && (
                      <div className="text-xs text-blue-700 mt-0.5">{feature.category}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface RelatedMetricsSectionProps {
  driver: BusinessDriver
  relatedKPIs?: BusinessDriver[]
}

export function RelatedMetricsSection({ driver, relatedKPIs = [] }: RelatedMetricsSectionProps) {
  if (relatedKPIs.length === 0) {
    return null
  }

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <BarChart3 className="h-3.5 w-3.5" />
        Success Indicators ({relatedKPIs.length})
      </h4>

      <div className="space-y-2">
        {relatedKPIs.map((kpi) => (
          <div
            key={kpi.id}
            className="bg-green-50 rounded-lg p-3 border border-green-200"
          >
            <div className="flex items-start gap-2">
              <Target className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <div className="text-sm font-medium text-green-900">{kpi.description}</div>
                {(kpi.baseline_value || kpi.target_value) && (
                  <div className="flex items-center gap-2 mt-1.5 text-xs">
                    {kpi.baseline_value && (
                      <span className="text-gray-600">Current: {kpi.baseline_value}</span>
                    )}
                    {kpi.baseline_value && kpi.target_value && (
                      <span className="text-gray-400">→</span>
                    )}
                    {kpi.target_value && (
                      <span className="text-green-700 font-medium">Target: {kpi.target_value}</span>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
