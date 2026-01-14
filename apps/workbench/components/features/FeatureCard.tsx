'use client'

import { useState } from 'react'
import {
  Target,
  CheckCircle,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Check,
  Loader2,
  ExternalLink,
  Zap,
  Users,
  MousePointer,
  Settings,
  Layout,
  BookOpen,
  Link2
} from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'
import type { Feature } from '@/types/api'

interface FeatureCardProps {
  feature: Feature
  onConfirmationChange?: (featureId: string, newStatus: string) => Promise<void>
  onViewEvidence?: (chunkId: string) => void
  defaultExpanded?: boolean
}

export default function FeatureCard({
  feature,
  onConfirmationChange,
  onViewEvidence,
  defaultExpanded = false
}: FeatureCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [updating, setUpdating] = useState(false)

  // Confirmation status helpers
  const getConfirmationBadge = () => {
    const status = feature.confirmation_status || feature.status || 'ai_generated'

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
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 border border-gray-200">
            AI Draft
          </span>
        )
    }
  }

  // Confidence indicator
  const getConfidenceIndicator = () => {
    const confidence = feature.confidence?.toLowerCase() || 'medium'
    const filled = confidence === 'high' ? 3 : confidence === 'medium' ? 2 : 1

    return (
      <div className="flex items-center gap-1" title={`${confidence} confidence`}>
        {[1, 2, 3].map(i => (
          <div
            key={i}
            className={`w-1.5 h-1.5 rounded-full ${
              i <= filled ? 'bg-blue-500' : 'bg-gray-200'
            }`}
          />
        ))}
        <span className="text-xs text-gray-500 ml-1 capitalize">{confidence}</span>
      </div>
    )
  }

  // Handle confirmation actions
  const handleConfirm = async () => {
    if (!onConfirmationChange) return
    try {
      setUpdating(true)
      await onConfirmationChange(feature.id, 'confirmed_consultant')
    } catch (error) {
      console.error('Failed to confirm:', error)
    } finally {
      setUpdating(false)
    }
  }

  const handleNeedsReview = async () => {
    if (!onConfirmationChange) return
    try {
      setUpdating(true)
      await onConfirmationChange(feature.id, 'needs_client')
    } catch (error) {
      console.error('Failed to mark for review:', error)
    } finally {
      setUpdating(false)
    }
  }

  // Get enrichment data - prefer v2 fields, fall back to legacy
  const isV2Enriched = feature.enrichment_status === 'enriched' || Boolean(feature.overview)
  const hasLegacyEnrichment = feature.details && Object.keys(feature.details).length > 0
  const hasEnrichment = isV2Enriched || hasLegacyEnrichment

  // V2 enrichment fields
  const overview = feature.overview || feature.details?.summary || null
  const targetPersonas = feature.target_personas || []
  const userActions = feature.user_actions || []
  const systemBehaviors = feature.system_behaviors || []
  const uiRequirements = feature.ui_requirements || []
  const rules = feature.rules || []
  const integrations = feature.integrations || []

  // Legacy fields as fallback
  const acceptanceCriteria = feature.details?.acceptance_criteria || []
  const legacyBusinessRules = feature.details?.business_rules || []

  return (
    <div className="bg-white border border-gray-200 rounded-lg hover:shadow-md hover:border-blue-200 transition-all duration-200">
      {/* Header - Always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset rounded-lg"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Name + Badges row */}
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <h3 className="font-semibold text-gray-900 truncate">{feature.name}</h3>
              {feature.is_mvp && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-blue-600 text-white">
                  MVP
                </span>
              )}
              {hasEnrichment && (
                <span title="AI enriched">
                  <Sparkles className="h-4 w-4 text-amber-500" />
                </span>
              )}
              {getConfirmationBadge()}
            </div>

            {/* Category + Confidence row */}
            <div className="flex items-center gap-3 text-sm text-gray-600">
              <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">{feature.category}</span>
              {getConfidenceIndicator()}
            </div>
          </div>

          {/* Expand indicator */}
          <div className="flex-shrink-0 p-1">
            {expanded ? (
              <ChevronUp className="h-5 w-5 text-gray-400" />
            ) : (
              <ChevronDown className="h-5 w-5 text-gray-400" />
            )}
          </div>
        </div>

        {/* Preview when collapsed */}
        {!expanded && overview && (
          <p className="mt-2 text-sm text-gray-600 line-clamp-2">{overview}</p>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-100 pt-4">
          {/* Overview */}
          {overview && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">Overview</h4>
              <div className="text-sm text-gray-700">
                <Markdown content={overview} />
              </div>
            </div>
          )}

          {/* Target Personas (V2) */}
          {targetPersonas.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5" />
                Who Uses This
              </h4>
              <div className="space-y-2">
                {targetPersonas.map((persona, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-sm">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      persona.role === 'primary'
                        ? 'bg-blue-100 text-blue-800'
                        : 'bg-gray-100 text-gray-700'
                    }`}>
                      {persona.role === 'primary' ? 'Primary' : 'Secondary'}
                    </span>
                    <div>
                      <span className="font-medium text-gray-900">{persona.persona_name}</span>
                      <span className="text-gray-600"> - {persona.context}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* User Actions (V2) */}
          {userActions.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <MousePointer className="h-3.5 w-3.5" />
                User Actions
              </h4>
              <ol className="space-y-1.5 list-decimal list-inside">
                {userActions.map((action, idx) => (
                  <li key={idx} className="text-sm text-gray-700">{action}</li>
                ))}
              </ol>
            </div>
          )}

          {/* System Behaviors (V2) */}
          {systemBehaviors.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Settings className="h-3.5 w-3.5" />
                System Behaviors
              </h4>
              <ul className="space-y-1.5">
                {systemBehaviors.map((behavior, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-gray-400">•</span>
                    {behavior}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* UI Requirements (V2) */}
          {uiRequirements.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Layout className="h-3.5 w-3.5" />
                UI Requirements
              </h4>
              <ul className="space-y-1.5">
                {uiRequirements.map((req, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-gray-400">•</span>
                    {req}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Rules (V2) */}
          {rules.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5" />
                Business Rules
              </h4>
              <ul className="space-y-1.5">
                {rules.map((rule, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-amber-500">!</span>
                    {rule}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Integrations (V2) */}
          {integrations.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Link2 className="h-3.5 w-3.5" />
                Integrations
              </h4>
              <div className="flex flex-wrap gap-2">
                {integrations.map((integration, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center px-2 py-1 bg-purple-50 text-purple-700 text-xs rounded border border-purple-100"
                  >
                    {integration}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Legacy: Acceptance Criteria */}
          {acceptanceCriteria.length > 0 && !isV2Enriched && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Acceptance Criteria
              </h4>
              <ul className="space-y-1.5">
                {acceptanceCriteria.map((criteria: any, idx: number) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                    <Check className="h-4 w-4 text-green-500 flex-shrink-0 mt-0.5" />
                    <span>{criteria.criterion || criteria}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Legacy: Business Rules */}
          {legacyBusinessRules.length > 0 && !isV2Enriched && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Business Rules
              </h4>
              <ul className="space-y-2">
                {legacyBusinessRules.map((rule: any, idx: number) => (
                  <li key={idx} className="text-sm border-l-2 border-gray-200 pl-3">
                    <p className="font-medium text-gray-800">{rule.title || rule.rule}</p>
                    {rule.rule && rule.title && (
                      <p className="text-gray-600 mt-0.5">{rule.rule}</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Evidence */}
          {feature.evidence && feature.evidence.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Evidence ({feature.evidence.length})
              </h4>
              <div className="space-y-2">
                {feature.evidence.slice(0, 3).map((evidence: any, idx: number) => (
                  <div
                    key={idx}
                    className="bg-gray-50 rounded-lg p-3 border border-gray-100"
                  >
                    <blockquote className="text-sm text-gray-700 italic mb-2">
                      "{evidence.excerpt}"
                    </blockquote>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">{evidence.rationale}</span>
                      {onViewEvidence && evidence.chunk_id && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onViewEvidence(evidence.chunk_id)
                          }}
                          className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
                        >
                          View source <ExternalLink className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
                {feature.evidence.length > 3 && (
                  <p className="text-xs text-gray-500 italic">
                    +{feature.evidence.length - 3} more evidence items
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Dependencies */}
          {feature.details?.dependencies?.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Dependencies
              </h4>
              <div className="flex flex-wrap gap-2">
                {feature.details.dependencies.map((dep: any, idx: number) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 px-2 py-1 bg-purple-50 text-purple-700 text-xs rounded border border-purple-100"
                  >
                    <Zap className="h-3 w-3" />
                    {dep.name || dep}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Confirmation Actions */}
          {onConfirmationChange && (
            <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
              <button
                onClick={handleConfirm}
                disabled={updating || feature.confirmation_status === 'confirmed_consultant'}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  feature.confirmation_status === 'confirmed_consultant'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                } disabled:opacity-50`}
              >
                {updating ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <CheckCircle className="h-4 w-4" />
                )}
                Confirm
              </button>
              <button
                onClick={handleNeedsReview}
                disabled={updating || feature.confirmation_status === 'needs_client'}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  feature.confirmation_status === 'needs_client'
                    ? 'bg-amber-600 text-white'
                    : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50'
                } disabled:opacity-50`}
              >
                <AlertCircle className="h-4 w-4" />
                Needs Review
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
