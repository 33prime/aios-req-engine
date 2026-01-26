'use client'

import { TrendingUp, Users, Zap, BarChart3, Target } from 'lucide-react'

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
  baseline_value?: string
  target_value?: string
  measurement_method?: string
  tracking_frequency?: string
  data_source?: string
  responsible_team?: string
  evidence?: Evidence[]
}

interface Feature {
  id: string
  name: string
  confirmation_status?: string
}

interface Persona {
  id: string
  name: string
  role?: string
}

interface MeasurementDetailsSectionProps {
  driver: BusinessDriver
}

export function MeasurementDetailsSection({ driver }: MeasurementDetailsSectionProps) {
  const hasBaseline = driver.baseline_value
  const hasTarget = driver.target_value
  const hasMethod = driver.measurement_method
  const hasFrequency = driver.tracking_frequency
  const hasSource = driver.data_source
  const hasOwner = driver.responsible_team

  if (!hasBaseline && !hasTarget && !hasMethod && !hasFrequency && !hasSource && !hasOwner) {
    return null
  }

  // Calculate gap if both baseline and target are numeric
  const calculateGap = () => {
    if (!hasBaseline || !hasTarget) return null

    // Try to extract numbers from the strings
    const baselineNum = parseFloat(driver.baseline_value!.replace(/[^0-9.-]/g, ''))
    const targetNum = parseFloat(driver.target_value!.replace(/[^0-9.-]/g, ''))

    if (isNaN(baselineNum) || isNaN(targetNum)) return null

    const gap = targetNum - baselineNum
    const isImprovement = gap < 0 ? 'reduction' : 'increase'
    const percentage = Math.abs((gap / baselineNum) * 100).toFixed(0)

    return {
      value: gap,
      isImprovement,
      percentage,
      formattedGap: gap < 0 ? gap.toString() : `+${gap}`
    }
  }

  const gap = calculateGap()

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <BarChart3 className="h-3.5 w-3.5" />
        Measurement Details
      </h4>

      <div className="space-y-3">
        {/* Baseline and Target with Gap */}
        {(hasBaseline || hasTarget) && (
          <div className="bg-green-50 rounded-lg p-3 border border-green-100">
            <div className="grid grid-cols-2 gap-3">
              {hasBaseline && (
                <div>
                  <div className="text-xs text-gray-500 mb-1">Current (Baseline)</div>
                  <div className="text-sm font-semibold text-gray-700">{driver.baseline_value}</div>
                </div>
              )}
              {hasTarget && (
                <div>
                  <div className="text-xs text-gray-500 mb-1">Target</div>
                  <div className="text-sm font-semibold text-green-700">{driver.target_value}</div>
                </div>
              )}
            </div>

            {gap && (
              <div className="mt-2 pt-2 border-t border-green-200">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-600">Gap to target:</span>
                  <span className={`font-medium ${gap.value < 0 ? 'text-emerald-700' : 'text-[#009b87]'}`}>
                    {gap.formattedGap} ({gap.percentage}% {gap.isImprovement})
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Measurement Method */}
        {hasMethod && (
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1">Measurement Method</div>
            <div className="text-sm text-gray-700 bg-gray-50 rounded p-2 border border-gray-100">
              {driver.measurement_method}
            </div>
          </div>
        )}

        {/* Tracking Details */}
        <div className="grid grid-cols-2 gap-3">
          {hasFrequency && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-1">Tracking Frequency</div>
              <div className="text-sm text-gray-700 capitalize">{driver.tracking_frequency}</div>
            </div>
          )}
          {hasSource && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-1">Data Source</div>
              <div className="text-sm text-gray-700">{driver.data_source}</div>
            </div>
          )}
        </div>

        {/* Owner */}
        {hasOwner && (
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1">Responsible Team/Owner</div>
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-green-600" />
              <span className="text-sm text-gray-700">{driver.responsible_team}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface BusinessImpactSectionProps {
  driver: BusinessDriver
  associatedFeatures?: Feature[]
  associatedPersonas?: Persona[]
  relatedPains?: BusinessDriver[]
}

export function BusinessImpactSection({
  driver,
  associatedFeatures = [],
  associatedPersonas = [],
  relatedPains = [],
}: BusinessImpactSectionProps) {
  const hasFeatures = associatedFeatures.length > 0
  const hasPersonas = associatedPersonas.length > 0
  const hasPains = relatedPains.length > 0

  if (!hasFeatures && !hasPersonas && !hasPains) {
    return null
  }

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <Target className="h-3.5 w-3.5" />
        Business Impact & Context
      </h4>

      <div className="space-y-3">
        {/* Associated Features */}
        {hasFeatures && (
          <div>
            <div className="text-xs font-medium text-gray-700 mb-2 flex items-center gap-1">
              <Zap className="h-3 w-3" />
              Features Contributing to This KPI ({associatedFeatures.length})
            </div>
            <div className="space-y-1.5">
              {associatedFeatures.slice(0, 5).map((feature) => (
                <div
                  key={feature.id}
                  className="flex items-center gap-2 text-sm bg-emerald-50 rounded p-2 border border-emerald-100"
                >
                  <div className={`w-2 h-2 rounded-full ${
                    feature.confirmation_status === 'confirmed_client' || feature.confirmation_status === 'confirmed_consultant'
                      ? 'bg-green-500'
                      : 'bg-gray-300'
                  }`} />
                  <span className="text-gray-700 flex-1">{feature.name}</span>
                </div>
              ))}
              {associatedFeatures.length > 5 && (
                <p className="text-xs text-gray-500 italic pl-2">
                  +{associatedFeatures.length - 5} more features
                </p>
              )}
            </div>
          </div>
        )}

        {/* Associated Personas */}
        {hasPersonas && (
          <div>
            <div className="text-xs font-medium text-gray-700 mb-2 flex items-center gap-1">
              <Users className="h-3 w-3" />
              User Personas Impacted ({associatedPersonas.length})
            </div>
            <div className="flex flex-wrap gap-2">
              {associatedPersonas.map((persona) => (
                <div
                  key={persona.id}
                  className="inline-flex items-center gap-1.5 px-2 py-1 bg-purple-50 text-purple-700 text-xs rounded border border-purple-100"
                >
                  <Users className="h-3 w-3" />
                  <span>{persona.name}</span>
                  {persona.role && <span className="text-purple-600">({persona.role})</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Related Pain Points */}
        {hasPains && (
          <div>
            <div className="text-xs font-medium text-gray-700 mb-2">
              Related Pain Points Being Measured
            </div>
            <div className="space-y-1.5">
              {relatedPains.map((pain) => (
                <div
                  key={pain.id}
                  className="text-sm bg-green-50 rounded p-2 border border-green-100 text-green-700"
                >
                  {pain.description}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
