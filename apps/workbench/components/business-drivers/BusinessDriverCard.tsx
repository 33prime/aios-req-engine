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
  enrichment_status?: 'none' | 'enriched' | 'stale'
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
  onConfirmationChange?: (driverId: string, newStatus: string) => Promise<void>
  onViewEvidence?: (chunkId: string) => void
  onEdit?: (driver: BusinessDriver) => void
  onDelete?: (driverId: string) => void
  defaultExpanded?: boolean
}

export default function BusinessDriverCard({
  driver,
  onConfirmationChange,
  onViewEvidence,
  onEdit,
  onDelete,
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
          bgColor: 'bg-green-50',
          borderColor: 'border-green-200',
          hoverBorder: 'hover:border-green-300',
          textColor: 'text-green-900',
          accentColor: 'text-green-700',
          label: 'KPI',
        }
      case 'pain':
        return {
          icon: AlertCircle,
          bgColor: 'bg-red-50',
          borderColor: 'border-red-200',
          hoverBorder: 'hover:border-red-300',
          textColor: 'text-red-900',
          accentColor: 'text-red-700',
          label: 'Pain Point',
        }
      case 'goal':
        return {
          icon: Sparkles,
          bgColor: 'bg-emerald-50',
          borderColor: 'border-emerald-200',
          hoverBorder: 'hover:border-emerald-300',
          textColor: 'text-gray-900',
          accentColor: 'text-emerald-700',
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
              i <= filled ? 'bg-blue-500' : 'bg-gray-200'
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
      await onConfirmationChange(driver.id, 'confirmed_consultant')
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
      await onConfirmationChange(driver.id, 'needs_client')
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
                  <Sparkles className="h-4 w-4 text-amber-500" />
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
                      onEdit(driver)
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
                      onDelete(driver.id)
                    }}
                    className="p-1 hover:bg-red-200 rounded"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-red-600" />
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
          {/* Type-specific enrichment sections will go here */}
          {/* For now, show basic enrichment */}

          {/* KPI Enrichment */}
          {driver.driver_type === 'kpi' && (hasEnrichment) && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <TrendingUp className="h-3.5 w-3.5" />
                Measurement Details
              </h4>
              <div className="space-y-2 text-sm">
                {driver.baseline_value && (
                  <div>
                    <span className="font-medium text-gray-700">Baseline: </span>
                    <span className="text-gray-600">{driver.baseline_value}</span>
                  </div>
                )}
                {driver.target_value && (
                  <div>
                    <span className="font-medium text-gray-700">Target: </span>
                    <span className="text-green-700 font-medium">{driver.target_value}</span>
                  </div>
                )}
                {driver.measurement_method && (
                  <div>
                    <span className="font-medium text-gray-700">Method: </span>
                    <span className="text-gray-600">{driver.measurement_method}</span>
                  </div>
                )}
                {driver.tracking_frequency && (
                  <div>
                    <span className="font-medium text-gray-700">Frequency: </span>
                    <span className="text-gray-600">{driver.tracking_frequency}</span>
                  </div>
                )}
                {driver.data_source && (
                  <div>
                    <span className="font-medium text-gray-700">Data Source: </span>
                    <span className="text-gray-600">{driver.data_source}</span>
                  </div>
                )}
                {driver.responsible_team && (
                  <div>
                    <span className="font-medium text-gray-700">Owner: </span>
                    <span className="text-gray-600">{driver.responsible_team}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Pain Enrichment */}
          {driver.driver_type === 'pain' && (hasEnrichment) && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <AlertCircle className="h-3.5 w-3.5" />
                Impact Analysis
              </h4>
              <div className="space-y-2 text-sm">
                {driver.severity && (
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-700">Severity: </span>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      driver.severity === 'critical' ? 'bg-red-600 text-white' :
                      driver.severity === 'high' ? 'bg-orange-500 text-white' :
                      driver.severity === 'medium' ? 'bg-yellow-500 text-white' :
                      'bg-gray-500 text-white'
                    }`}>
                      {driver.severity.charAt(0).toUpperCase() + driver.severity.slice(1)}
                    </span>
                  </div>
                )}
                {driver.frequency && (
                  <div>
                    <span className="font-medium text-gray-700">Frequency: </span>
                    <span className="text-gray-600">{driver.frequency.charAt(0).toUpperCase() + driver.frequency.slice(1)}</span>
                  </div>
                )}
                {driver.affected_users && (
                  <div>
                    <span className="font-medium text-gray-700">Affected Users: </span>
                    <span className="text-gray-600">{driver.affected_users}</span>
                  </div>
                )}
                {driver.business_impact && (
                  <div>
                    <span className="font-medium text-gray-700">Business Impact: </span>
                    <span className="text-red-700 font-medium">{driver.business_impact}</span>
                  </div>
                )}
                {driver.current_workaround && (
                  <div>
                    <span className="font-medium text-gray-700">Current Workaround: </span>
                    <span className="text-gray-600">{driver.current_workaround}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Goal Enrichment */}
          {driver.driver_type === 'goal' && (hasEnrichment) && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Target className="h-3.5 w-3.5" />
                Achievement Criteria
              </h4>
              <div className="space-y-2 text-sm">
                {driver.goal_timeframe && (
                  <div>
                    <span className="font-medium text-gray-700">Timeframe: </span>
                    <span className="text-emerald-700 font-medium">{driver.goal_timeframe}</span>
                  </div>
                )}
                {driver.success_criteria && (
                  <div>
                    <span className="font-medium text-gray-700">Success Criteria: </span>
                    <span className="text-gray-600">{driver.success_criteria}</span>
                  </div>
                )}
                {driver.dependencies && (
                  <div>
                    <span className="font-medium text-gray-700">Dependencies: </span>
                    <span className="text-gray-600">{driver.dependencies}</span>
                  </div>
                )}
                {driver.owner && (
                  <div>
                    <span className="font-medium text-gray-700">Owner: </span>
                    <span className="text-gray-600">{driver.owner}</span>
                  </div>
                )}
              </div>
            </div>
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
                          className="text-blue-600 hover:text-blue-800 flex items-center gap-1"
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
                disabled={updating || driver.confirmation_status === 'needs_client'}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  driver.confirmation_status === 'needs_client'
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
