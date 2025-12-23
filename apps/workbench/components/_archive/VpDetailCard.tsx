'use client'

import { useState } from 'react'
import { Zap, CheckCircle, AlertCircle, Info, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'
import { VpStep } from '@/types/api'

interface VpDetailCardProps {
  step: VpStep
  onViewEvidence?: (chunkId: string) => void
}

export default function VpDetailCard({ step, onViewEvidence }: VpDetailCardProps) {
  const [showDetails, setShowDetails] = useState(false)
  const [showEvidence, setShowEvidence] = useState(false)

  // Debug logging
  console.log(`🎯 VP Step ${step.step_index}:`, {
    hasEnrichment: !!step.enrichment,
    enrichmentKeys: step.enrichment ? Object.keys(step.enrichment) : [],
    evidenceCount: step.enrichment?.evidence?.length || 0,
    evidenceItems: step.enrichment?.evidence,
    combinedEvidence: (step.evidence || step.enrichment?.evidence || []),
    combinedLength: (step.evidence || step.enrichment?.evidence || []).length
  })

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'confirmed_client':
        return 'bg-green-100 text-green-800'
      case 'confirmed_consultant':
        return 'bg-blue-100 text-blue-800'
      case 'needs_confirmation':
        return 'bg-yellow-100 text-yellow-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="card">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <div className="flex items-center justify-center w-8 h-8 bg-purple-100 rounded-full text-purple-600 font-semibold text-sm">
              {step.step_index}
            </div>
            <h3 className="text-lg font-semibold text-gray-900">{step.label}</h3>
          </div>
          <div className="flex items-center space-x-4 mb-3">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(step.status)}`}>
              {step.status}
            </span>
          </div>
          <div className="text-xs text-gray-500">
            Created: {new Date(step.created_at).toLocaleDateString()}
            {step.enrichment && ' • Enriched: ' + (new Date(step.updated_at).toLocaleDateString())}
          </div>
        </div>
        <Zap className="h-6 w-6 text-purple-600 flex-shrink-0" />
      </div>

      {/* Description */}
      {step.description && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">Description</h4>
          <p className="text-sm text-gray-700">{step.description}</p>
        </div>
      )}

      {/* Core Fields */}
      {(step.user_benefit_pain || step.ui_overview || step.value_created || step.kpi_impact) && (
        <div className="mb-4 space-y-3">
          {step.user_benefit_pain && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">User Benefit/Pain</h4>
              <p className="text-sm text-gray-700">{step.user_benefit_pain}</p>
            </div>
          )}
          {step.ui_overview && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">UI Overview</h4>
              <p className="text-sm text-gray-700">{step.ui_overview}</p>
            </div>
          )}
          {step.value_created && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">Value Created</h4>
              <p className="text-sm text-gray-700">{step.value_created}</p>
            </div>
          )}
          {step.kpi_impact && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-1">KPI Impact</h4>
              <p className="text-sm text-gray-700">{step.kpi_impact}</p>
            </div>
          )}
        </div>
      )}

      {/* Enrichment Toggle */}
      {step.enrichment && Object.keys(step.enrichment).length > 0 && (
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
      {showDetails && step.enrichment && (
        <div className="border-t border-gray-200 pt-4 mb-4 space-y-4">
          {step.enrichment.summary && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
              <p className="text-sm text-gray-700">{step.enrichment.summary}</p>
            </div>
          )}

          {step.enrichment.enhanced_fields && Object.keys(step.enrichment.enhanced_fields).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Enhanced Fields</h4>
              <div className="space-y-3">
                {Object.entries(step.enrichment.enhanced_fields).map(([field, value]) => (
                  <div key={field} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900 capitalize">{field.replace(/_/g, ' ')}</div>
                    <div className="text-gray-600 mt-1 whitespace-pre-wrap">{String(value)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {step.enrichment.proposed_needs && step.enrichment.proposed_needs.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Proposed Client Needs</h4>
              <div className="space-y-2">
                {step.enrichment.proposed_needs.map((need: any, idx: number) => (
                  <div key={idx} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900">{need.title || need.ask}</div>
                    <div className="text-gray-600 mt-1">{need.ask || need.title}</div>
                    <div className="flex items-center space-x-2 mt-2">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        need.priority === 'high' ? 'bg-red-100 text-red-800' :
                        need.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-green-100 text-green-800'
                      }`}>
                        {need.priority}
                      </span>
                      <span className="text-xs text-gray-500">{need.suggested_method}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Evidence Section */}
      {step.enrichment && step.enrichment.evidence && step.enrichment.evidence.length > 0 && (
        <div className="border-t border-gray-200 pt-4">
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              <AlertCircle className="h-4 w-4 mr-1" />
              Evidence ({step.enrichment.evidence.length} items)
              {showEvidence ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
            </button>
          </div>

          {showEvidence && (
            <div className="space-y-3">
              {step.enrichment.evidence.map((evidence: any, idx: number) => (
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
    </div>
  )
}
