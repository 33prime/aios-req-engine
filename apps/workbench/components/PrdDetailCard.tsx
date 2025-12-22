'use client'

import { useState } from 'react'
import { FileText, CheckCircle, AlertCircle, Info, ExternalLink, ChevronDown, ChevronUp, Users, Target, Zap } from 'lucide-react'
import { PrdSection } from '@/types/api'

interface PrdDetailCardProps {
  section: PrdSection
  onViewEvidence?: (chunkId: string) => void
}

export default function PrdDetailCard({ section, onViewEvidence }: PrdDetailCardProps) {
  const [showDetails, setShowDetails] = useState(false)
  const [showEvidence, setShowEvidence] = useState(false)

  // Debug logging
  console.log(`🎯 PRD Section ${section.slug}:`, {
    hasEnrichment: !!section.enrichment,
    enrichmentKeys: section.enrichment ? Object.keys(section.enrichment) : [],
    evidenceCount: section.enrichment?.evidence?.length || 0,
    evidenceItems: section.enrichment?.evidence,
    clientNeedsCount: section.enrichment?.proposed_client_needs?.length || 0,
    sectionEvidence: section.evidence,
    combinedEvidence: (section.evidence || section.enrichment?.evidence || []),
    combinedLength: (section.evidence || section.enrichment?.evidence || []).length
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
          <div className="flex items-center space-x-2 mb-2">
            <h3 className="text-lg font-semibold text-gray-900">{section.label}</h3>
            {section.required && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                Required
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 mb-2">
            {section.slug === 'personas' && 'User personas and characteristics'}
            {section.slug === 'key_features' && 'Core product features and capabilities'}
            {section.slug === 'happy_path' && 'Ideal user journey and workflow'}
            {section.slug || 'Section content'}
          </p>
          <div className="flex items-center space-x-4 mb-3">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(section.status)}`}>
              {section.status}
            </span>
            {section.enrichment && (
              <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 ml-2">
                🤖 Enriched
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500">
            Created: {new Date(section.created_at).toLocaleDateString()}
            {section.enrichment && ' • Enriched: ' + (new Date(section.updated_at).toLocaleDateString())}
          </div>
        </div>
        {section.slug === 'personas' && <Users className="h-6 w-6 text-blue-600 flex-shrink-0" />}
        {section.slug === 'key_features' && <Target className="h-6 w-6 text-green-600 flex-shrink-0" />}
        {section.slug === 'happy_path' && <Zap className="h-6 w-6 text-purple-600 flex-shrink-0" />}
        {!['personas', 'key_features', 'happy_path'].includes(section.slug) && <FileText className="h-6 w-6 text-green-600 flex-shrink-0" />}
      </div>

      {/* Fields - Enhanced based on section type */}
      {section.fields && Object.keys(section.fields).length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-medium text-gray-700 mb-2">
            {section.slug === 'personas' && 'User Personas'}
            {section.slug === 'key_features' && 'Key Features Overview'}
            {section.slug === 'happy_path' && 'User Journey Overview'}
            {!['personas', 'key_features', 'happy_path'].includes(section.slug) && 'Content'}
          </h4>

          {section.slug === 'personas' && section.enrichment?.enhanced_fields?.content ? (
            <div className="text-sm text-gray-700 space-y-4">
              {/* Enhanced personas content */}
              <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                <h5 className="font-medium text-blue-900 mb-2">Detailed Personas</h5>
                <div className="whitespace-pre-wrap text-blue-800">
                  {section.enrichment.enhanced_fields.content}
                </div>
              </div>

              {/* Original content if different */}
              {section.fields.content && section.fields.content !== section.enrichment?.enhanced_fields?.content && (
                <div className="bg-gray-50 p-3 rounded border">
                  <h6 className="text-xs font-medium text-gray-600 mb-1">Original Content</h6>
                  <div className="text-gray-700 text-sm">
                    {section.fields.content}
                  </div>
                </div>
              )}
            </div>
          ) : section.slug === 'key_features' && section.enrichment?.enhanced_fields?.content ? (
            <div className="text-sm text-gray-700 space-y-4">
              {/* Enhanced features content */}
              <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                <h5 className="font-medium text-green-900 mb-2">Enhanced Features</h5>
                <div className="whitespace-pre-wrap text-green-800">
                  {section.enrichment.enhanced_fields.content}
                </div>
              </div>

              {/* Original content if different */}
              {section.fields.content && section.fields.content !== section.enrichment?.enhanced_fields?.content && (
                <div className="bg-gray-50 p-3 rounded border">
                  <h6 className="text-xs font-medium text-gray-600 mb-1">Original Content</h6>
                  <div className="text-gray-700 text-sm">
                    {section.fields.content}
                  </div>
                </div>
              )}
            </div>
          ) : section.slug === 'happy_path' && section.enrichment?.enhanced_fields?.content ? (
            <div className="text-sm text-gray-700 space-y-4">
              {/* Enhanced happy path as high-level value path */}
              <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                <h5 className="font-medium text-purple-900 mb-2">High-Level User Journey</h5>
                <div className="whitespace-pre-wrap text-purple-800">
                  {section.enrichment.enhanced_fields.content}
                </div>
                <div className="mt-3 text-xs text-purple-600">
                  💡 This represents the high-level value path through the application
                </div>
              </div>

              {/* Original content if different */}
              {section.fields.content && section.fields.content !== section.enrichment?.enhanced_fields?.content && (
                <div className="bg-gray-50 p-3 rounded border">
                  <h6 className="text-xs font-medium text-gray-600 mb-1">Original Content</h6>
                  <div className="text-gray-700 text-sm">
                    {section.fields.content}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Default content display */
            <div className="text-sm text-gray-700 bg-gray-50 p-3 rounded">
              {section.enrichment?.enhanced_fields?.content || section.fields.content || 'No content available'}
            </div>
          )}
        </div>
      )}

      {/* Contextual Information */}
      {section.enrichment && (
        <div className="mb-4 p-4 bg-indigo-50 rounded-lg border border-indigo-200">
          <h4 className="text-sm font-medium text-indigo-900 mb-2 flex items-center">
            <Info className="h-4 w-4 mr-2" />
            Contextual Insights
          </h4>
          <div className="text-sm text-indigo-800 space-y-2">
            {section.slug === 'personas' && (
              <div>
                <strong>🎯 Purpose:</strong> Defines the target users and their characteristics to guide feature development and user experience design.
              </div>
            )}
            {section.slug === 'key_features' && (
              <div>
                <strong>⚡ Purpose:</strong> Outlines the core functionality that delivers value to users and addresses their needs.
              </div>
            )}
            {section.slug === 'happy_path' && (
              <div>
                <strong>🚀 Purpose:</strong> Maps the ideal user journey through the application, ensuring smooth and valuable interactions.
              </div>
            )}
            {section.enrichment.summary && (
              <div>
                <strong>📋 Summary:</strong> {section.enrichment.summary}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Enrichment Toggle */}
      {section.enrichment && Object.keys(section.enrichment).length > 0 && (
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
      {showDetails && section.enrichment && (
        <div className="border-t border-gray-200 pt-4 mb-4 space-y-4">
          {section.enrichment.summary && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Summary</h4>
              <p className="text-sm text-gray-700">{section.enrichment.summary}</p>
            </div>
          )}

          {section.enrichment.enhanced_fields && Object.keys(section.enrichment.enhanced_fields).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2">Enhanced Fields</h4>
              <div className="space-y-2">
                {Object.entries(section.enrichment.enhanced_fields).map(([field, value]) => (
                  <div key={field} className="text-sm border border-gray-200 rounded p-3">
                    <div className="font-medium text-gray-900 capitalize">{field.replace(/_/g, ' ')}</div>
                    <div className="text-gray-600 mt-1">{String(value)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {section.enrichment.proposed_client_needs && section.enrichment.proposed_client_needs.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                <Users className="h-4 w-4 mr-2" />
                Proposed Client Needs ({section.enrichment.proposed_client_needs.length})
              </h4>
              <div className="space-y-3">
                {section.enrichment.proposed_client_needs.map((need: any, idx: number) => (
                  <div key={idx} className="text-sm border border-gray-200 rounded-lg p-4 bg-white">
                    <div className="font-medium text-gray-900 mb-1">{need.title || need.ask}</div>
                    <div className="text-gray-600 mb-2">{need.ask || need.title}</div>
                    {need.why && (
                      <div className="text-gray-500 text-xs mb-2 italic">
                        "{need.why}"
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          need.priority === 'high' ? 'bg-red-100 text-red-800' :
                          need.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-green-100 text-green-800'
                        }`}>
                          {need.priority} priority
                        </span>
                        <span className="text-xs text-gray-500">{need.suggested_method}</span>
                      </div>
                      {need.evidence && need.evidence.length > 0 && (
                        <span className="text-xs text-blue-600">
                          {need.evidence.length} evidence item{need.evidence.length !== 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Additional enrichment insights */}
          {section.enrichment.enhanced_fields && Object.keys(section.enrichment.enhanced_fields).length > 1 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                <Target className="h-4 w-4 mr-2" />
                Additional Enhancements
              </h4>
              <div className="space-y-2">
                {Object.entries(section.enrichment.enhanced_fields)
                  .filter(([key]) => key !== 'content') // Skip content as it's shown above
                  .map(([field, value]) => (
                    <div key={field} className="text-sm border border-gray-200 rounded p-3">
                      <div className="font-medium text-gray-900 capitalize mb-1">
                        {field.replace(/_/g, ' ')}
                      </div>
                      <div className="text-gray-600 whitespace-pre-wrap">{String(value)}</div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Evidence Section */}
      {(section.evidence || (section.enrichment && section.enrichment.evidence)) && (
        <div className="border-t border-gray-200 pt-4">
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => setShowEvidence(!showEvidence)}
              className="flex items-center text-sm font-medium text-blue-600 hover:text-blue-800"
            >
              <AlertCircle className="h-4 w-4 mr-1" />
              Evidence ({(section.evidence || section.enrichment?.evidence || []).length} items)
              {showEvidence ? <ChevronUp className="h-4 w-4 ml-1" /> : <ChevronDown className="h-4 w-4 ml-1" />}
            </button>
          </div>

          {showEvidence && (
            <div className="space-y-3">
              {(section.evidence || section.enrichment?.evidence || []).map((evidence: any, idx: number) => (
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
