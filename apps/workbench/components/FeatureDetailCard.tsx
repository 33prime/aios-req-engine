'use client'

import { useState } from 'react'
import { Target, CheckCircle, AlertCircle, Info, ExternalLink, ChevronDown, ChevronUp, History } from 'lucide-react'
import { Feature } from '@/types/api'
import ChangeLogTimeline from '@/components/revisions/ChangeLogTimeline'

interface FeatureDetailCardProps {
  feature: Feature
  onViewEvidence?: (chunkId: string) => void
  onConfirmationChange?: (featureId: string, newStatus: string) => Promise<void>
}

export default function FeatureDetailCard({ feature, onViewEvidence, onConfirmationChange }: FeatureDetailCardProps) {
  const [showDetails, setShowDetails] = useState(false)
  const [showEvidence, setShowEvidence] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [updating, setUpdating] = useState(false)

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed_client':
        return 'bg-green-100 text-green-800'
      case 'confirmed_consultant':
        return 'bg-blue-100 text-blue-800'
      case 'needs_client':
      case 'needs_confirmation':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getConfidenceColor = (confidence: string) => {
    switch (confidence) {
      case 'high':
        return 'text-green-600'
      case 'medium':
        return 'text-yellow-600'
      case 'low':
        return 'text-red-600'
      default:
        return 'text-gray-600'
    }
  }

  const handleConfirmationChange = async (newStatus: string) => {
    if (!onConfirmationChange) return

    try {
      setUpdating(true)
      await onConfirmationChange(feature.id, newStatus)
    } catch (error) {
      console.error('Failed to update confirmation status:', error)
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-2 mb-2">
            <h3 className="text-lg font-semibold text-gray-900">{feature.name}</h3>
            {feature.is_mvp && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                MVP
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mb-2">{feature.category}</p>
          <div className="flex items-center space-x-4 mb-3">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(feature.status)}`}>
              {feature.status}
            </span>
            <span className={`text-sm font-medium ${getConfidenceColor(feature.confidence)}`}>
              {feature.confidence} confidence
            </span>
          </div>
          <div className="text-xs text-gray-500">
            Created: {new Date(feature.created_at).toLocaleDateString()}
            {feature.details && ' • Enriched: ' + (new Date(feature.created_at).toLocaleDateString())}
          </div>
        </div>
        <Target className="h-6 w-6 text-blue-600 flex-shrink-0" />
      </div>

      {/* Confirmation Actions */}
      {onConfirmationChange && (
        <div className="mb-4 pb-4 border-b border-gray-200">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Confirmation Status</h4>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleConfirmationChange('confirmed_consultant')}
              disabled={updating || feature.confirmation_status === 'confirmed_consultant'}
              className={`flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                feature.confirmation_status === 'confirmed_consultant'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50'
              }`}
            >
              <CheckCircle className="h-4 w-4" />
              Confirm
            </button>
            <button
              onClick={() => handleConfirmationChange('needs_client')}
              disabled={updating || feature.confirmation_status === 'needs_client'}
              className={`flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                feature.confirmation_status === 'needs_client'
                  ? 'bg-amber-600 text-white'
                  : 'bg-white border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50'
              }`}
            >
              <AlertCircle className="h-4 w-4" />
              Needs Client Review
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            Confirm if the feature is accurate. Mark for client review if clarification is needed.
          </p>
        </div>
      )}

      {/* Enrichment Toggle */}
      {feature.details && Object.keys(feature.details).length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            <Info className="h-4 w-4 mr-1" />
            AI Enrichment Details
            {showDetails ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
          </button>
        </div>
      )}

      {/* Enrichment Details */}
      {showDetails && feature.details && (
        <div className="border-t border-gray-200 pt-4 mb-4 space-y-4">
          {feature.details.summary && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
              <p className="text-sm text-gray-700">{feature.details.summary}</p>
            </div>
          )}

          {feature.details.data_requirements && feature.details.data_requirements.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Data Requirements</h4>
              <div className="space-y-2">
                {feature.details.data_requirements.map((req: any, idx: number) => (
                  <div key={idx} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900">{req.entity}</div>
                    <div className="text-gray-600 mt-1">Fields: {req.fields.join(', ')}</div>
                    {req.notes && <div className="text-gray-500 mt-1">{req.notes}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {feature.details.business_rules && feature.details.business_rules.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Business Rules</h4>
              <div className="space-y-2">
                {feature.details.business_rules.map((rule: any, idx: number) => (
                  <div key={idx} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900">{rule.title}</div>
                    <div className="text-gray-600 mt-1">{rule.rule}</div>
                    {rule.verification && <div className="text-gray-500 mt-1">Verification: {rule.verification}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {feature.details.acceptance_criteria && feature.details.acceptance_criteria.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Acceptance Criteria</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                {feature.details.acceptance_criteria.map((criteria: any, idx: number) => (
                  <li key={idx} className="flex items-start">
                    <CheckCircle className="h-3 w-3 text-green-600 mr-2 mt-0.5 flex-shrink-0" />
                    <span>{criteria.criterion}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {feature.details.dependencies && feature.details.dependencies.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Dependencies</h4>
              <div className="space-y-2">
                {feature.details.dependencies.map((dep: any, idx: number) => (
                  <div key={idx} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900">{dep.name}</div>
                    <div className="text-gray-600 mt-1">Type: {dep.dependency_type}</div>
                    <div className="text-gray-500 mt-1">{dep.why}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {feature.details.integrations && feature.details.integrations.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Integrations</h4>
              <div className="space-y-2">
                {feature.details.integrations.map((integration: any, idx: number) => (
                  <div key={idx} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900">{integration.system}</div>
                    <div className="text-gray-600 mt-1">Direction: {integration.direction}</div>
                    <div className="text-gray-500 mt-1">Data: {integration.data_exchanged}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {feature.details.telemetry_events && feature.details.telemetry_events.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Telemetry Events</h4>
              <div className="space-y-2">
                {feature.details.telemetry_events.map((event: any, idx: number) => (
                  <div key={idx} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900">{event.event_name}</div>
                    <div className="text-gray-600 mt-1">When: {event.when_fired}</div>
                    <div className="text-gray-500 mt-1">Properties: {event.properties.join(', ')}</div>
                    {event.success_metric && <div className="text-gray-500">Success: {event.success_metric}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {feature.details.risks && feature.details.risks.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Risks</h4>
              <div className="space-y-2">
                {feature.details.risks.map((risk: any, idx: number) => (
                  <div key={idx} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900">{risk.title}</div>
                    <div className="text-gray-600 mt-1">{risk.risk}</div>
                    <div className="text-gray-500 mt-1">Mitigation: {risk.mitigation}</div>
                    <div className="text-gray-500">Severity: {risk.severity}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Evidence Section */}
      {feature.evidence && feature.evidence.length > 0 && (
        <div className="border-t border-gray-200 pt-4">
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              <AlertCircle className="h-4 w-4 mr-1" />
              Evidence ({feature.evidence.length} items)
              {showEvidence ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
            </button>
          </div>

          {showEvidence && (
            <div className="space-y-3">
              {feature.evidence.map((evidence, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-3">
                  <p className="text-sm text-gray-700 mb-2">"{evidence.excerpt}"</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">{evidence.rationale}</span>
                    {onViewEvidence && (
                      <button
                        onClick={() => onViewEvidence(evidence.chunk_id)}
                        className="text-xs text-blue-600 hover:text-blue-800 flex items-center"
                      >
                        View source <ExternalLink className="h-3 w-3 ml-1" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Change History Section */}
      <div className="border-t border-gray-200 pt-4">
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-800"
        >
          <History className="h-4 w-4 mr-1" />
          Change History
          {showHistory ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
        </button>

        {showHistory && (
          <div className="mt-4">
            <ChangeLogTimeline entityType="feature" entityId={feature.id} limit={10} />
          </div>
        )}
      </div>
    </div>
  )
}



