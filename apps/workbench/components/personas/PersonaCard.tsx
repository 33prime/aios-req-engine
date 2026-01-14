'use client'

import { User, Target, AlertCircle, CheckCircle, Clock, TrendingUp, Heart, AlertTriangle, Zap } from 'lucide-react'
import { Persona, getPersonaInitials, getPersonaColor, formatDemographicsOrPsychographics } from '@/lib/persona-utils'

interface PersonaCardProps {
  persona: Persona
  onClick: () => void
}

// Check if entity was recently updated (last 24 hours)
const isRecentlyUpdated = (updatedAt: string | undefined) => {
  if (!updatedAt) return false
  const diffMs = new Date().getTime() - new Date(updatedAt).getTime()
  return diffMs < 24 * 60 * 60 * 1000
}

export default function PersonaCard({ persona, onClick }: PersonaCardProps) {
  const initials = getPersonaInitials(persona)
  const colors = getPersonaColor(persona)
  const recentlyUpdated = isRecentlyUpdated((persona as any).updated_at)

  // Get preview of goals (first 2)
  const goalsPreview = persona.goals?.slice(0, 2) || []
  const hasMoreGoals = (persona.goals?.length || 0) > 2

  // Score helpers
  const coverageScore = persona.coverage_score ?? null
  const healthScore = persona.health_score ?? null

  const getCoverageColor = (score: number) => {
    if (score >= 70) return 'text-green-600 bg-green-50'
    if (score >= 40) return 'text-amber-600 bg-amber-50'
    return 'text-red-600 bg-red-50'
  }

  const getHealthColor = (score: number) => {
    if (score >= 70) return 'text-green-500'
    if (score >= 40) return 'text-amber-500'
    return 'text-red-500'
  }

  const getHealthIndicator = (score: number) => {
    if (score >= 70) return 'bg-green-500'
    if (score >= 40) return 'bg-amber-500'
    return 'bg-red-500'
  }

  // Confirmation status badge
  const getConfirmationBadge = () => {
    const status = persona.confirmation_status || 'ai_generated'

    switch (status) {
      case 'confirmed_client':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800 border border-green-200">
            <CheckCircle className="h-3 w-3" />
            Client Confirmed
          </span>
        )
      case 'confirmed_consultant':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
            <CheckCircle className="h-3 w-3" />
            Confirmed
          </span>
        )
      case 'needs_client':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800 border border-amber-200">
            <Clock className="h-3 w-3" />
            Needs Review
          </span>
        )
      case 'ai_generated':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
            AI Draft
          </span>
        )
    }
  }

  return (
    <button
      onClick={onClick}
      className={`w-full text-left bg-white border rounded-lg p-4 hover:shadow-md hover:border-blue-300 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${recentlyUpdated ? 'border-yellow-400 border-l-4' : 'border-gray-200'}`}
    >
      {/* Recently Updated Badge */}
      {recentlyUpdated && (
        <div className="mb-3">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-yellow-100 text-yellow-700 text-xs font-medium rounded" title="Updated in the last 24 hours">
            <Zap className="h-3 w-3" />
            Recently Updated
          </span>
        </div>
      )}

      {/* Header with Avatar */}
      <div className="flex items-start gap-3 mb-3">
        {/* Avatar with Health Indicator */}
        <div className="relative flex-shrink-0">
          <div
            className={`w-12 h-12 rounded-full ${colors.bg} ${colors.text} flex items-center justify-center font-semibold text-lg`}
          >
            {initials}
          </div>
          {/* Health indicator dot */}
          {healthScore !== null && (
            <div
              className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full ${getHealthIndicator(healthScore)} border-2 border-white`}
              title={`Health: ${healthScore.toFixed(0)}%`}
            />
          )}
        </div>

        {/* Name and Role */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="font-semibold text-gray-900 truncate">{persona.name}</h3>
            {getConfirmationBadge()}
          </div>
          {persona.role && (
            <p className="text-sm text-gray-600 truncate">{persona.role}</p>
          )}
        </div>
      </div>

      {/* Coverage Score Badge */}
      {coverageScore !== null && (
        <div className="mb-3">
          <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${getCoverageColor(coverageScore)}`}>
            <TrendingUp className="h-3 w-3" />
            <span>{coverageScore.toFixed(0)}% coverage</span>
          </div>
          {healthScore !== null && healthScore < 50 && (
            <div className="inline-flex items-center gap-1 ml-2 text-xs text-amber-600">
              <AlertTriangle className="h-3 w-3" />
              <span>Needs update</span>
            </div>
          )}
        </div>
      )}

      {/* Description Preview */}
      {persona.description && (
        <p className="text-sm text-gray-700 mb-3 line-clamp-2">
          {persona.description}
        </p>
      )}

      {/* Demographics/Psychographics Preview */}
      {(persona.demographics || persona.psychographics) && (
        <div className="text-xs text-gray-600 mb-3 line-clamp-1">
          {formatDemographicsOrPsychographics(persona.demographics) || formatDemographicsOrPsychographics(persona.psychographics)}
        </div>
      )}

      {/* Key Goals Preview */}
      {goalsPreview.length > 0 && (
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs font-medium text-gray-700">
            <Target className="h-3.5 w-3.5 text-blue-600" />
            <span>Key Goals</span>
          </div>
          <ul className="space-y-1">
            {goalsPreview.map((goal, idx) => (
              <li key={idx} className="text-sm text-gray-600 truncate pl-5">
                • {goal}
              </li>
            ))}
          </ul>
          {hasMoreGoals && (
            <p className="text-xs text-gray-500 italic pl-5">
              +{(persona.goals?.length || 0) - 2} more...
            </p>
          )}
        </div>
      )}

      {/* Pain Points Indicator */}
      {persona.pain_points && persona.pain_points.length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-100">
          <div className="flex items-center gap-1.5 text-xs text-gray-600">
            <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
            <span>{persona.pain_points.length} pain point{persona.pain_points.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
      )}

      {/* Related Items Count */}
      {((persona.related_features?.length || 0) > 0 || (persona.related_vp_steps?.length || 0) > 0) && (
        <div className="mt-3 flex items-center gap-3 text-xs text-gray-500">
          {(persona.related_features?.length || 0) > 0 && (
            <span>{persona.related_features?.length} feature{persona.related_features?.length !== 1 ? 's' : ''}</span>
          )}
          {(persona.related_vp_steps?.length || 0) > 0 && (
            <span>{persona.related_vp_steps?.length} VP step{persona.related_vp_steps?.length !== 1 ? 's' : ''}</span>
          )}
        </div>
      )}

      {/* Click to expand hint */}
      <div className="mt-3 text-xs text-blue-600 font-medium">
        Click to view details →
      </div>
    </button>
  )
}
