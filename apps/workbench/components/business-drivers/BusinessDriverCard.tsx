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
  Loader2,
  ExternalLink,
  TrendingUp,
  Pencil,
  Trash2,
} from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'
import {
  MeasurementDetailsSection,
  BusinessImpactSection,
} from './KPISections'
import {
  PainDetailsSection,
  SolutionsSection,
  UserImpactSection,
} from './PainSections'
import {
  GoalDetailsSection,
  ProgressSection,
  SupportingFeaturesSection,
  RelatedMetricsSection,
} from './GoalSections'

interface Evidence {
  chunk_id?: string
  excerpt?: string
  text?: string
  rationale?: string
  confidence?: number
}

interface BusinessDriver {
  id: string
  driver_type: 'kpi' | 'pain' | 'goal'
  description: string
  priority?: number
  confirmation_status?: string
  evidence?: Evidence[]

  // Enrichment tracking
  enrichment_status?: 'not_enriched' | 'enriched' | 'enrichment_failed' | 'none' | 'stale'
  enriched_at?: string

  // KPI fields
  baseline_value?: string
  target_value?: string
  measurement_method?: string
  tracking_frequency?: string
  data_source?: string
  responsible_team?: string

  // Pain fields
  severity?: 'critical' | 'high' | 'medium' | 'low'
  frequency?: 'constant' | 'daily' | 'weekly' | 'monthly' | 'rare'
  affected_users?: string
  business_impact?: string
  current_workaround?: string

  // Goal fields
  goal_timeframe?: string
  success_criteria?: string
  dependencies?: string
  owner?: string

  // Display
  category?: string
  notes?: string
}

interface BusinessDriverCardProps {
  driver: BusinessDriver
  associations?: {
    features?: any[]
    personas?: any[]
    related_kpis?: any[]
    related_pains?: any[]
    related_goals?: any[]
  }
  onConfirmationChange?: (newStatus: string) => Promise<void>
  onViewEvidence?: (chunkId: string) => void
  onEdit?: () => void
  onDelete?: () => void
  onEnrich?: () => Promise<void>
  isEnriching?: boolean
  defaultExpanded?: boolean
}

export default function BusinessDriverCard({
  driver,
  associations,
  onConfirmationChange,
  onViewEvidence,
  onEdit,
  onDelete,
  onEnrich,
  isEnriching = false,
  defaultExpanded = false,
}: BusinessDriverCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const [updating, setUpdating] = useState(false)

  // Type-specific configuration
  const getTypeConfig = () => {
    switch (driver.driver_type) {
      case 'kpi':
        return {
          icon: Target,
          bgColor: 'bg-emerald-50',
          borderColor: 'border-emerald-200',
          hoverBorder: 'hover:border-emerald-300',
          textColor: 'text-emerald-900',
          accentColor: 'text-emerald-600',
          label: 'KPI',
        }
      case 'pain':
        return {
          icon: AlertCircle,
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          hoverBorder: 'hover:border-green-300',
          textColor: 'text-green-900',
          accentColor: 'text-green-700',
          label: 'Pain Point',
        }
      case 'goal':
        return {
          icon: Sparkles,
          bgColor: 'bg-teal-50',
          borderColor: 'border-teal-200',
          hoverBorder: 'hover:border-teal-300',
          textColor: 'text-teal-900',
          accentColor: 'text-teal-600',
          label: 'Goal',
        }
    }
  }

  const config = getTypeConfig()
  const Icon = config.icon

  // Confirmation status helpers
  const getConfirmationBadge = () => {
    const status = driver.confirmation_status || 'ai_generated'

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
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-200">
            <CheckCircle className="h-3 w-3" />
            Confirmed
          </span>
        )
      case 'needs_client':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-teal-100 text-teal-800 border border-teal-200">
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

  // Confidence indicator (based on priority or evidence count)
  const getConfidenceIndicator = () => {
    const evidenceCount = driver.evidence?.length || 0
    const filled = evidenceCount >= 3 ? 3 : evidenceCount >= 2 ? 2 : evidenceCount >= 1 ? 1 : 0

    return (
      <div className="flex items-center gap-1" title={`${filled} evidence sources`}>
        {[1, 2, 3].map(i => (
          <div
            key={i}
            className={`w-1.5 h-1.5 rounded-full ${
              i <= filled ? 'bg-[#009b87]' : 'bg-gray-200'
            }`}
          />
        ))}
        <span className="text-xs text-gray-500 ml-1">
          {filled === 3 ? 'High' : filled === 2 ? 'Medium' : 'Low'}
        </span>
      </div>
    )
  }

  // Check if enriched
  const isEnriched = driver.enrichment_status === 'enriched'
  const hasEnrichment = isEnriched && (
    // KPI enrichment
    driver.baseline_value || driver.target_value || driver.measurement_method ||
    // Pain enrichment
    driver.severity || driver.frequency || driver.affected_users ||
    // Goal enrichment
    driver.goal_timeframe || driver.success_criteria || driver.owner
  )

  // Generate preview text based on type
  const getPreviewText = () => {
    if (!expanded && hasEnrichment) {
      switch (driver.driver_type) {
        case 'kpi':
          const parts = []
          if (driver.baseline_value) parts.push(`Baseline: ${driver.baseline_value}`)
          if (driver.target_value) parts.push(`Target: ${driver.target_value}`)
          if (driver.tracking_frequency) parts.push(driver.tracking_frequency)
          return parts.join(' → ')
        case 'pain':
          const painParts = []
          if (driver.severity) painParts.push(driver.severity.charAt(0).toUpperCase() + driver.severity.slice(1))
          if (driver.affected_users) painParts.push(`Affects: ${driver.affected_users}`)
          if (driver.business_impact) painParts.push(`Impact: ${driver.business_impact}`)
          return painParts.join(' | ')
        case 'goal':
          const goalParts = []
          if (driver.goal_timeframe) goalParts.push(driver.goal_timeframe)
          if (driver.success_criteria) goalParts.push(`Success: ${driver.success_criteria}`)
          if (driver.owner) goalParts.push(`Owner: ${driver.owner}`)
          return goalParts.join(' | ')
      }
    }
    return null
  }

  const previewText = getPreviewText()

  // Handle confirmation actions
  const handleConfirm = async () => {
    if (!onConfirmationChange) return
    try {
      setUpdating(true)
      await onConfirmationChange('confirmed_consultant')
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
      await onConfirmationChange('needs_client')
    } catch (error) {
      console.error('Failed to mark for review:', error)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className={`bg-white border rounded-lg hover:shadow-md ${config.hoverBorder} transition-all duration-200 ${config.borderColor}`}>
      {/* Header - Always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset rounded-lg"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            {/* Name + Badges row */}
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <Icon className={`h-4 w-4 ${config.accentColor} flex-shrink-0`} />
              <h3 className={`font-semibold truncate ${config.textColor}`}>{driver.description}</h3>
              {hasEnrichment && (
                <span title="AI enriched">
                  <Sparkles className="h-4 w-4 text-emerald-500" />
                </span>
              )}
              {getConfirmationBadge()}
            </div>

            {/* Type + Confidence row */}
            <div className="flex items-center gap-3 text-sm text-gray-600">
              <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">{config.label}</span>
              {getConfidenceIndicator()}
            </div>
          </div>

          {/* Actions + Expand indicator */}
          <div className="flex items-center gap-2">
            {/* Edit/Delete on hover */}
            {(onEdit || onDelete) && (
              <div className="flex items-center gap-1 opacity-0 hover:opacity-100 transition-opacity">
                {onEdit && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onEdit()
                    }}
                    className="p-1 hover:bg-gray-200 rounded"
                  >
                    <Pencil className="h-3.5 w-3.5 text-gray-600" />
                  </button>
                )}
                {onDelete && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onDelete()
                    }}
                    className="p-1 hover:bg-green-200 rounded"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-green-700" />
                  </button>
                )}
              </div>
            )}

            {/* Expand indicator */}
            <div className="flex-shrink-0 p-1">
              {expanded ? (
                <ChevronUp className="h-5 w-5 text-gray-400" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" />
              )}
            </div>
          </div>
        </div>

        {/* Preview when collapsed */}
        {!expanded && previewText && (
          <p className="mt-2 text-sm text-gray-600 line-clamp-2">{previewText}</p>
        )}
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-100 pt-4">
          {/* Type-specific enrichment sections */}
          {driver.driver_type === 'kpi' && (
            <>
              <MeasurementDetailsSection driver={driver} />
              {associations && (
                <BusinessImpactSection
                  driver={driver}
                  associatedFeatures={associations.features}
                  associatedPersonas={associations.personas}
                  relatedPains={associations.related_pains}
                />
              )}
            </>
          )}

          {driver.driver_type === 'pain' && (
            <>
              <PainDetailsSection driver={driver} />
              {associations && (
                <>
                  <SolutionsSection driver={driver} solutionFeatures={associations.features} />
                  <UserImpactSection driver={driver} affectedPersonas={associations.personas} />
                </>
              )}
            </>
          )}

          {driver.driver_type === 'goal' && (
            <>
              <GoalDetailsSection driver={driver} />
              {associations && (
                <>
                  <ProgressSection driver={driver} supportingFeatures={associations.features} />
                  <SupportingFeaturesSection driver={driver} supportingFeatures={associations.features} />
                  <RelatedMetricsSection driver={driver} relatedKPIs={associations.related_kpis} />
                </>
              )}
            </>
          )}

          {/* Notes */}
          {driver.notes && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Notes
              </h4>
              <div className="text-sm text-gray-700">
                <Markdown content={driver.notes} />
              </div>
            </div>
          )}

          {/* Evidence */}
          {driver.evidence && driver.evidence.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Evidence ({driver.evidence.length})
              </h4>
              <div className="space-y-2">
                {driver.evidence.slice(0, 3).map((evidence, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-50 rounded-lg p-3 border border-gray-100"
                  >
                    <blockquote className="text-sm text-gray-700 italic mb-2">
                      "{evidence.excerpt || evidence.text}"
                    </blockquote>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-500">{evidence.rationale}</span>
                      {onViewEvidence && evidence.chunk_id && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onViewEvidence(evidence.chunk_id!)
                          }}
                          className="text-[#009b87] hover:text-emerald-700 flex items-center gap-1"
                        >
                          View source <ExternalLink className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
                {driver.evidence.length > 3 && (
                  <p className="text-xs text-gray-500 italic">
                    +{driver.evidence.length - 3} more evidence items
                  </p>
                )}
              </div>
            </div>
          )}

          {/* Confirmation Actions */}
          {onConfirmationChange && (
            <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
              <button
                onClick={handleConfirm}
                disabled={updating || driver.confirmation_status === 'confirmed_consultant'}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  driver.confirmation_status === 'confirmed_consultant'
                    ? 'bg-[#009b87] text-white'
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
                disabled={updating || driver.confirmation_status === 'needs_client'}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  driver.confirmation_status === 'needs_client'
                    ? 'bg-teal-600 text-white'
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
