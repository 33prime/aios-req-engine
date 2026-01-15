'use client'

import { User, Target, AlertCircle, CheckCircle, Clock, TrendingUp, AlertTriangle, Zap, MapPin, ChevronRight } from 'lucide-react'
import { Persona, getPersonaInitials, formatDemographicsOrPsychographics } from '@/lib/persona-utils'

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

// Extract age range from demographics
const getAgeRange = (demographics: string | Record<string, any> | undefined): string | null => {
  if (!demographics) return null
  if (typeof demographics === 'string') {
    const ageMatch = demographics.match(/(\d+[-–]\d+|\d+\+?)\s*(years?|y\/o)?/i)
    return ageMatch ? ageMatch[1] : null
  }
  if (typeof demographics === 'object') {
    return demographics.age || demographics.ageRange || demographics.age_range || null
  }
  return null
}

// Extract location from demographics
const getLocation = (demographics: string | Record<string, any> | undefined): string | null => {
  if (!demographics) return null
  if (typeof demographics === 'object') {
    return demographics.location || demographics.region || demographics.city || null
  }
  return null
}

export default function PersonaCard({ persona, onClick }: PersonaCardProps) {
  const initials = getPersonaInitials(persona)
  const recentlyUpdated = isRecentlyUpdated((persona as any).updated_at)

  // Get preview of goals (first 3)
  const goalsPreview = persona.goals?.slice(0, 3) || []
  const hasMoreGoals = (persona.goals?.length || 0) > 3
  const remainingCount = (persona.goals?.length || 0) - 3

  // Score helpers
  const coverageScore = persona.coverage_score ?? null
  const healthScore = persona.health_score ?? null

  // Demographics parsing
  const ageRange = getAgeRange(persona.demographics)
  const location = getLocation(persona.demographics)

  // Confirmation status badge
  const getConfirmationBadge = () => {
    const status = persona.confirmation_status || 'ai_generated'

    switch (status) {
      case 'confirmed_client':
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-700 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" /> Client
          </span>
        )
      case 'confirmed_consultant':
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-emerald-100 text-emerald-700 flex items-center gap-1">
            <CheckCircle className="w-3 h-3" /> Confirmed
          </span>
        )
      case 'needs_client':
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-amber-100 text-amber-700 flex items-center gap-1">
            <Clock className="w-3 h-3" /> Needs Review
          </span>
        )
      case 'ai_generated':
      default:
        return (
          <span className="px-2 py-1 text-xs font-medium rounded-full bg-gray-100 text-gray-600">
            AI Draft
          </span>
        )
    }
  }

  return (
    <div
      onClick={onClick}
      className="bg-white rounded-xl border-2 border-gray-200 overflow-hidden hover:shadow-lg hover:border-[#009b87] transition-all duration-200 cursor-pointer"
    >
      {/* Recently Updated Banner */}
      {recentlyUpdated && (
        <div className="bg-emerald-50 border-b border-emerald-200 px-4 py-2">
          <div className="flex items-center gap-1.5">
            <Zap className="w-4 h-4 text-[#009b87]" />
            <span className="text-xs font-medium text-emerald-700">Recently Updated</span>
          </div>
        </div>
      )}

      <div className="p-5">
        {/* Header with Avatar, Name, Role, Confirmation Badge */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            {/* Emerald Avatar */}
            <div className="w-12 h-12 rounded-full bg-emerald-100 flex items-center justify-center text-lg font-semibold text-emerald-700">
              {initials}
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">{persona.name}</h3>
              {persona.role && (
                <p className="text-sm text-gray-600">{persona.role}</p>
              )}
            </div>
          </div>
          {/* Confirmation badge */}
          {getConfirmationBadge()}
        </div>

        {/* Metadata Row */}
        {(location || ageRange) && (
          <div className="flex items-center gap-3 text-xs text-gray-600 mb-4 pb-4 border-b border-gray-200">
            {location && (
              <span className="flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5" /> {location}
              </span>
            )}
            {location && ageRange && <span className="text-gray-300">•</span>}
            {ageRange && (
              <span className="flex items-center gap-1">
                <User className="w-3.5 h-3.5" /> Age: {ageRange}
              </span>
            )}
          </div>
        )}

        {/* Coverage Score */}
        {coverageScore !== null && (
          <div className="mb-4">
            <div className="flex items-center gap-1 text-xs text-gray-600">
              <TrendingUp className="w-4 h-4" />
              <span className="font-medium">{coverageScore.toFixed(0)}% coverage</span>
              {healthScore !== null && healthScore < 50 && (
                <span className="ml-2 text-amber-600 flex items-center gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  Needs update
                </span>
              )}
            </div>
          </div>
        )}

        {/* Key Goals with teal header */}
        {goalsPreview.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-4 h-4 text-[#009b87]" />
              <h4 className="text-xs font-semibold text-[#009b87] uppercase tracking-wide">Key Goals</h4>
            </div>
            <ul className="space-y-1.5 text-sm text-gray-700">
              {goalsPreview.map((goal, idx) => (
                <li key={idx} className="flex items-start">
                  <span className="text-[#009b87] mr-2 mt-0.5">•</span>
                  <span className="line-clamp-1">{goal}</span>
                </li>
              ))}
            </ul>
            {hasMoreGoals && (
              <button className="text-xs text-[#009b87] hover:underline mt-2 flex items-center gap-1">
                +{remainingCount} more...
              </button>
            )}
          </div>
        )}

        {/* Pain Points Badge */}
        {persona.pain_points && persona.pain_points.length > 0 && (
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-gray-600" />
            <span className="text-sm text-gray-700">{persona.pain_points.length} pain point{persona.pain_points.length !== 1 ? 's' : ''}</span>
          </div>
        )}

        {/* View Details Button */}
        <button className="w-full text-sm text-[#009b87] hover:text-[#007a6b] font-medium flex items-center justify-center gap-1 py-2 hover:bg-emerald-50 rounded-lg transition-colors">
          View Details
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
}
