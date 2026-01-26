'use client'

import { AlertCircle, Users, Wrench, Quote, TrendingDown, Clock } from 'lucide-react'

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
  severity?: 'critical' | 'high' | 'medium' | 'low'
  frequency?: 'constant' | 'daily' | 'weekly' | 'monthly' | 'rare'
  affected_users?: string
  business_impact?: string
  current_workaround?: string
  evidence?: Evidence[]
}

interface Feature {
  id: string
  name: string
  confirmation_status?: string
  category?: string
}

interface Persona {
  id: string
  name: string
  role?: string
  pain_points?: string[]
}

interface PainDetailsSectionProps {
  driver: BusinessDriver
}

export function PainDetailsSection({ driver }: PainDetailsSectionProps) {
  const hasSeverity = driver.severity
  const hasFrequency = driver.frequency
  const hasAffectedUsers = driver.affected_users
  const hasBusinessImpact = driver.business_impact
  const hasWorkaround = driver.current_workaround

  if (!hasSeverity && !hasFrequency && !hasAffectedUsers && !hasBusinessImpact && !hasWorkaround) {
    return null
  }

  const getSeverityConfig = (severity: string) => {
    switch (severity) {
      case 'critical':
        return { bg: 'bg-green-800', text: 'text-white', label: 'Critical - Blocking' }
      case 'high':
        return { bg: 'bg-green-700', text: 'text-white', label: 'High - Major Friction' }
      case 'medium':
        return { bg: 'bg-green-600', text: 'text-white', label: 'Medium - Inconvenience' }
      case 'low':
        return { bg: 'bg-green-500', text: 'text-white', label: 'Low - Minor Issue' }
      default:
        return { bg: 'bg-gray-400', text: 'text-white', label: severity }
    }
  }

  const getFrequencyIcon = (frequency: string) => {
    switch (frequency) {
      case 'constant':
        return '🔴 Always occurring'
      case 'daily':
        return '📅 Every day'
      case 'weekly':
        return '📆 Weekly'
      case 'monthly':
        return '📊 Monthly'
      case 'rare':
        return '⏱️ Rare (< monthly)'
      default:
        return frequency
    }
  }

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <AlertCircle className="h-3.5 w-3.5" />
        Impact Analysis
      </h4>

      <div className="space-y-3">
        {/* Severity and Frequency */}
        <div className="grid grid-cols-2 gap-3">
          {hasSeverity && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-1.5">Severity</div>
              {(() => {
                const config = getSeverityConfig(driver.severity!)
                return (
                  <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded font-medium text-sm ${config.bg} ${config.text}`}>
                    <AlertCircle className="h-4 w-4" />
                    {config.label}
                  </div>
                )
              })()}
            </div>
          )}

          {hasFrequency && (
            <div>
              <div className="text-xs font-medium text-gray-500 mb-1.5">Frequency</div>
              <div className="flex items-center gap-2 text-sm text-gray-700">
                <Clock className="h-4 w-4 text-gray-500" />
                <span>{getFrequencyIcon(driver.frequency!)}</span>
              </div>
            </div>
          )}
        </div>

        {/* Affected Users */}
        {hasAffectedUsers && (
          <div className="bg-green-50 rounded-lg p-3 border border-green-100">
            <div className="text-xs font-medium text-green-700 mb-1.5 flex items-center gap-1">
              <Users className="h-3 w-3" />
              Who Experiences This Pain
            </div>
            <div className="text-sm text-green-900">{driver.affected_users}</div>
          </div>
        )}

        {/* Business Impact */}
        {hasBusinessImpact && (
          <div className="bg-green-50 rounded-lg p-3 border border-green-200">
            <div className="text-xs font-medium text-green-700 mb-1.5 flex items-center gap-1">
              <TrendingDown className="h-3 w-3" />
              Quantified Business Impact
            </div>
            <div className="text-sm font-semibold text-green-900">{driver.business_impact}</div>
          </div>
        )}

        {/* Current Workaround */}
        {hasWorkaround && (
          <div>
            <div className="text-xs font-medium text-gray-500 mb-1.5">Current Workaround</div>
            <div className="text-sm text-gray-700 bg-gray-50 rounded p-3 border border-gray-200 italic">
              "{driver.current_workaround}"
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

interface SolutionsSectionProps {
  driver: BusinessDriver
  solutionFeatures?: Feature[]
}

export function SolutionsSection({ driver, solutionFeatures = [] }: SolutionsSectionProps) {
  if (solutionFeatures.length === 0) {
    return null
  }

  const confirmedFeatures = solutionFeatures.filter(
    f => f.confirmation_status === 'confirmed_client' || f.confirmation_status === 'confirmed_consultant'
  )
  const draftFeatures = solutionFeatures.filter(
    f => !f.confirmation_status || f.confirmation_status === 'ai_generated' || f.confirmation_status === 'needs_client'
  )

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <Wrench className="h-3.5 w-3.5" />
        Features Addressing This Pain ({solutionFeatures.length})
      </h4>

      <div className="space-y-3">
        {/* Confirmed Solutions */}
        {confirmedFeatures.length > 0 && (
          <div>
            <div className="text-xs font-medium text-green-700 mb-2">
              ✅ Confirmed Solutions ({confirmedFeatures.length})
            </div>
            <div className="space-y-2">
              {confirmedFeatures.map((feature) => (
                <div
                  key={feature.id}
                  className="flex items-start gap-2 bg-green-50 rounded-lg p-3 border border-green-200"
                >
                  <div className="w-2 h-2 rounded-full bg-green-500 mt-1.5 flex-shrink-0" />
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

        {/* Proposed Solutions */}
        {draftFeatures.length > 0 && (
          <div>
            <div className="text-xs font-medium text-gray-700 mb-2">
              💡 Proposed Solutions ({draftFeatures.length})
            </div>
            <div className="space-y-2">
              {draftFeatures.map((feature) => (
                <div
                  key={feature.id}
                  className="flex items-start gap-2 bg-gray-50 rounded-lg p-3 border border-gray-200"
                >
                  <div className="w-2 h-2 rounded-full bg-gray-400 mt-1.5 flex-shrink-0" />
                  <div className="flex-1">
                    <div className="text-sm font-medium text-gray-900">{feature.name}</div>
                    {feature.category && (
                      <div className="text-xs text-gray-700 mt-0.5">{feature.category}</div>
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

interface UserImpactSectionProps {
  driver: BusinessDriver
  affectedPersonas?: Persona[]
}

export function UserImpactSection({ driver, affectedPersonas = [] }: UserImpactSectionProps) {
  if (affectedPersonas.length === 0) {
    return null
  }

  return (
    <div>
      <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-3 flex items-center gap-1.5">
        <Users className="h-3.5 w-3.5" />
        User Personas Feeling This Pain ({affectedPersonas.length})
      </h4>

      <div className="space-y-2">
        {affectedPersonas.map((persona) => (
          <div
            key={persona.id}
            className="bg-purple-50 rounded-lg p-3 border border-purple-200"
          >
            <div className="flex items-start gap-2">
              <Users className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <div className="font-medium text-purple-900 text-sm">{persona.name}</div>
                {persona.role && (
                  <div className="text-xs text-purple-700 mt-0.5">{persona.role}</div>
                )}
                {persona.pain_points && persona.pain_points.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {persona.pain_points.slice(0, 2).map((pain, idx) => (
                      <div key={idx} className="flex items-start gap-1.5 text-xs text-purple-800">
                        <Quote className="h-3 w-3 mt-0.5 flex-shrink-0" />
                        <span className="italic">"{pain}"</span>
                      </div>
                    ))}
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
