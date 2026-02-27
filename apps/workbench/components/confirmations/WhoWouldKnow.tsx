'use client'

import { useState } from 'react'
import {
  User,
  Lightbulb,
  Star,
  ChevronDown,
  ChevronUp,
  MessageCircle,
  Mail,
  Loader2,
  HelpCircle,
  Sparkles,
} from 'lucide-react'

interface StakeholderSuggestion {
  stakeholder_id: string
  stakeholder_name: string
  role?: string
  match_score: number
  reasons: string[]
  is_primary_contact: boolean
  suggestion_text?: string
  topic_matches: string[]
}

interface WhoWouldKnowProps {
  projectId: string
  entityType: 'feature' | 'persona' | 'vp_step'
  entityId: string
  entityName?: string
  gapDescription?: string
  onAskStakeholder?: (stakeholderId: string, stakeholderName: string) => void
  onMarkResolved?: () => void
  className?: string
}

import { API_BASE } from '@/lib/config'

export default function WhoWouldKnow({
  projectId,
  entityType,
  entityId,
  entityName,
  gapDescription,
  onAskStakeholder,
  onMarkResolved,
  className = '',
}: WhoWouldKnowProps) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [suggestions, setSuggestions] = useState<StakeholderSuggestion[]>([])
  const [topicsExtracted, setTopicsExtracted] = useState<string[]>([])
  const [hasFetched, setHasFetched] = useState(false)

  const fetchSuggestions = async () => {
    if (hasFetched) return

    setLoading(true)
    setError(null)

    try {
      const response = await fetch(`${API_BASE}/v1/confirmations/who-would-know`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          project_id: projectId,
          entity_type: entityType,
          entity_id: entityId,
          gap_description: gapDescription,
        }),
      })

      if (!response.ok) {
        throw new Error(`Failed to fetch suggestions: ${response.status}`)
      }

      const data = await response.json()
      setSuggestions(data.suggestions || [])
      setTopicsExtracted(data.topics_extracted || [])
      setHasFetched(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load suggestions')
    } finally {
      setLoading(false)
    }
  }

  const handleExpand = () => {
    if (!expanded && !hasFetched) {
      fetchSuggestions()
    }
    setExpanded(!expanded)
  }

  const getMatchBadgeColor = (score: number) => {
    if (score >= 15) return 'bg-green-100 text-green-700'
    if (score >= 10) return 'bg-blue-100 text-brand-primary-hover'
    if (score >= 5) return 'bg-yellow-100 text-yellow-700'
    return 'bg-gray-100 text-gray-600'
  }

  const getMatchLabel = (score: number) => {
    if (score >= 15) return 'Strong match'
    if (score >= 10) return 'Good match'
    if (score >= 5) return 'Possible match'
    return 'Weak match'
  }

  return (
    <div className={`border border-[#88BABF]/30 rounded-lg bg-[#88BABF]/5 ${className}`}>
      {/* Header - Always visible */}
      <button
        onClick={handleExpand}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[#88BABF]/10 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-2">
          <Lightbulb className="w-4 h-4 text-accent" />
          <span className="text-sm font-medium text-accent">
            Who would know?
          </span>
          {hasFetched && suggestions.length > 0 && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-accent-light text-accent">
              {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        {loading ? (
          <Loader2 className="w-4 h-4 text-accent animate-spin" />
        ) : expanded ? (
          <ChevronUp className="w-4 h-4 text-accent" />
        ) : (
          <ChevronDown className="w-4 h-4 text-accent" />
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Gap description if provided */}
          {gapDescription && (
            <div className="flex items-start gap-2 p-3 bg-white/50 rounded-lg border border-border">
              <HelpCircle className="w-4 h-4 text-text-muted mt-0.5 flex-shrink-0" />
              <p className="text-sm text-text-secondary">{gapDescription}</p>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
              <button
                onClick={() => {
                  setHasFetched(false)
                  fetchSuggestions()
                }}
                className="mt-2 text-xs text-red-600 hover:text-red-800 underline"
              >
                Try again
              </button>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex items-center justify-center py-6">
              <Loader2 className="w-5 h-5 text-accent animate-spin" />
              <span className="ml-2 text-sm text-text-muted">Finding stakeholders...</span>
            </div>
          )}

          {/* No suggestions */}
          {!loading && !error && hasFetched && suggestions.length === 0 && (
            <div className="text-center py-6">
              <User className="w-8 h-8 text-text-muted mx-auto mb-2" />
              <p className="text-sm text-text-muted">
                No stakeholders found with matching expertise.
              </p>
              <p className="text-xs text-text-muted mt-1">
                Try adding stakeholders with domain expertise in related areas.
              </p>
            </div>
          )}

          {/* Suggestions list */}
          {!loading && !error && suggestions.length > 0 && (
            <div className="space-y-3">
              {suggestions.map((suggestion) => (
                <div
                  key={suggestion.stakeholder_id}
                  className="p-3 bg-white rounded-lg border border-border hover:border-[#88BABF] transition-colors"
                >
                  {/* Stakeholder header */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                        suggestion.is_primary_contact ? 'bg-accent-light' : 'bg-gray-100'
                      }`}>
                        <User className={`w-4 h-4 ${
                          suggestion.is_primary_contact ? 'text-accent' : 'text-gray-500'
                        }`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-text-primary text-sm">
                            {suggestion.stakeholder_name}
                          </span>
                          {suggestion.is_primary_contact && (
                            <Star className="w-3.5 h-3.5 text-yellow-500 fill-yellow-500" />
                          )}
                        </div>
                        {suggestion.role && (
                          <p className="text-xs text-text-muted">{suggestion.role}</p>
                        )}
                      </div>
                    </div>

                    {/* Match score badge */}
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${getMatchBadgeColor(suggestion.match_score)}`}>
                      {getMatchLabel(suggestion.match_score)}
                    </span>
                  </div>

                  {/* Topic matches */}
                  {suggestion.topic_matches.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {suggestion.topic_matches.slice(0, 5).map((topic, idx) => (
                        <span
                          key={idx}
                          className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-[#88BABF]/10 text-accent"
                        >
                          <Sparkles className="w-3 h-3 mr-1" />
                          {topic}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Match reasons */}
                  {suggestion.reasons.length > 0 && (
                    <div className="mt-2 text-xs text-text-muted">
                      {suggestion.reasons.slice(0, 2).map((reason, idx) => (
                        <span key={idx} className="block">
                          • {reason.replace(/expertise:|mentioned:/g, '')}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="mt-3 flex items-center gap-2">
                    {onAskStakeholder && (
                      <>
                        <button
                          onClick={() => onAskStakeholder(suggestion.stakeholder_id, suggestion.stakeholder_name)}
                          className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-accent text-white rounded hover:bg-accent-hover transition-colors"
                        >
                          <MessageCircle className="w-3.5 h-3.5 mr-1.5" />
                          Ask {suggestion.stakeholder_name.split(' ')[0]}
                        </button>
                        <button
                          onClick={() => window.open(`mailto:?subject=Question about ${entityName || entityType}`, '_blank')}
                          className="inline-flex items-center px-3 py-1.5 text-xs font-medium bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
                        >
                          <Mail className="w-3.5 h-3.5 mr-1.5" />
                          Email
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Topics extracted (collapsed by default) */}
          {topicsExtracted.length > 0 && (
            <details className="text-xs text-text-muted">
              <summary className="cursor-pointer hover:text-text-secondary">
                Topics analyzed ({topicsExtracted.length})
              </summary>
              <div className="mt-2 flex flex-wrap gap-1">
                {topicsExtracted.map((topic, idx) => (
                  <span
                    key={idx}
                    className="px-2 py-0.5 bg-gray-100 rounded text-text-muted"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </details>
          )}

          {/* Mark resolved action */}
          {onMarkResolved && hasFetched && (
            <div className="pt-3 border-t border-border">
              <button
                onClick={onMarkResolved}
                className="text-xs text-text-muted hover:text-text-secondary underline"
              >
                Mark as resolved
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
