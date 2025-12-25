/**
 * Escalations Page
 *
 * Review queue for patches that require manual review before applying.
 * Phase 1: Surgical Updates for Features
 */

'use client'

import React, { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  AlertTriangle,
  CheckCircle,
  X,
  Edit,
  Info,
  ExternalLink,
} from 'lucide-react'
import { EvidenceGroup } from '@/components/evidence/EvidenceChip'

interface Escalation {
  id: string
  createdAt: string
  escalationReason: string
  recommendedAction: 'review' | 'reject' | 'modify'
  patch: {
    entityType: 'feature' | 'persona' | 'prd_section' | 'vp_step'
    entityId: string
    entityName: string
    changeSummary: string
    changes: Record<string, any>
    classification: {
      changeType: string
      severity: 'minor' | 'moderate' | 'major'
      rationale: string
    }
    evidence: Array<{
      chunkId: string
      signalId: string
      excerpt: string
      rationale?: string
      sourceType?: string
      sourceLabel?: string
      timestamp?: string
      page?: number
      confidence?: number
    }>
  }
}

export default function EscalationsPage() {
  const params = useParams()
  const router = useRouter()
  const projectId = params.projectId as string

  const [escalations, setEscalations] = useState<Escalation[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedEscalation, setSelectedEscalation] = useState<Escalation | null>(null)
  const [processingId, setProcessingId] = useState<string | null>(null)

  // TODO: Load escalations from API
  useEffect(() => {
    // Mock data for now
    setLoading(false)
  }, [projectId])

  const handleApprove = async (escalation: Escalation) => {
    setProcessingId(escalation.id)
    try {
      // TODO: API call to apply patch
      console.log('Approving escalation:', escalation.id)
      // Remove from list after approval
      setEscalations(escalations.filter((e) => e.id !== escalation.id))
      setSelectedEscalation(null)
    } catch (error) {
      console.error('Failed to approve:', error)
    } finally {
      setProcessingId(null)
    }
  }

  const handleReject = async (escalation: Escalation) => {
    setProcessingId(escalation.id)
    try {
      // TODO: API call to reject patch
      console.log('Rejecting escalation:', escalation.id)
      // Remove from list after rejection
      setEscalations(escalations.filter((e) => e.id !== escalation.id))
      setSelectedEscalation(null)
    } catch (error) {
      console.error('Failed to reject:', error)
    } finally {
      setProcessingId(null)
    }
  }

  const handleModify = (escalation: Escalation) => {
    // Navigate to entity edit page
    router.push(`/projects/${projectId}/${escalation.patch.entityType}s/${escalation.patch.entityId}`)
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'minor':
        return 'bg-green-50 text-green-700 border-green-200'
      case 'moderate':
        return 'bg-yellow-50 text-yellow-700 border-yellow-200'
      case 'major':
        return 'bg-red-50 text-red-700 border-red-200'
      default:
        return 'bg-gray-50 text-gray-700 border-gray-200'
    }
  }

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'feature':
        return '🎯'
      case 'persona':
        return '👤'
      case 'prd_section':
        return '📄'
      case 'vp_step':
        return '⚡'
      default:
        return '📦'
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center text-blue-600 hover:text-blue-800 mb-4"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Link>

        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-yellow-600" />
              Escalation Queue
            </h1>
            <p className="text-gray-600 mt-2">
              Review and approve changes that require manual confirmation
            </p>
          </div>

          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">{escalations.length}</div>
            <div className="text-sm text-gray-600">Pending Reviews</div>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      ) : escalations.length === 0 ? (
        /* Empty State */
        <div className="text-center py-16 bg-white rounded-lg border border-gray-200">
          <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 mb-2">All Clear!</h3>
          <p className="text-gray-600 max-w-md mx-auto">
            No escalations pending. Changes that require review will appear here.
          </p>
        </div>
      ) : (
        /* Escalation List */
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* List */}
          <div className="space-y-4">
            {escalations.map((escalation) => (
              <button
                key={escalation.id}
                onClick={() => setSelectedEscalation(escalation)}
                className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                  selectedEscalation?.id === escalation.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 bg-white hover:border-gray-300'
                }`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl">{getEntityIcon(escalation.patch.entityType)}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-gray-900">
                        {escalation.patch.entityName}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded border ${getSeverityColor(escalation.patch.classification.severity)}`}>
                        {escalation.patch.classification.severity}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700 mb-2">
                      {escalation.patch.changeSummary}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <AlertTriangle className="h-3 w-3" />
                      {escalation.escalationReason}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Detail Panel */}
          <div className="lg:sticky lg:top-8 h-fit">
            {selectedEscalation ? (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-3xl">{getEntityIcon(selectedEscalation.patch.entityType)}</span>
                      <h3 className="text-xl font-bold text-gray-900">
                        {selectedEscalation.patch.entityName}
                      </h3>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded border ${getSeverityColor(selectedEscalation.patch.classification.severity)}`}>
                      {selectedEscalation.patch.classification.changeType} • {selectedEscalation.patch.classification.severity}
                    </span>
                  </div>
                  <button
                    onClick={() => setSelectedEscalation(null)}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-5 w-5" />
                  </button>
                </div>

                {/* Escalation Reason */}
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3 mb-4">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="h-4 w-4 text-yellow-600 flex-shrink-0 mt-0.5" />
                    <div>
                      <h4 className="text-sm font-semibold text-yellow-900 mb-1">
                        Why This Was Escalated
                      </h4>
                      <p className="text-sm text-yellow-800">{selectedEscalation.escalationReason}</p>
                    </div>
                  </div>
                </div>

                {/* Change Summary */}
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Proposed Changes</h4>
                  <p className="text-sm text-gray-700">{selectedEscalation.patch.changeSummary}</p>
                </div>

                {/* Classification Rationale */}
                <div className="mb-4">
                  <h4 className="text-sm font-semibold text-gray-900 mb-2">Classification</h4>
                  <p className="text-sm text-gray-700">
                    {selectedEscalation.patch.classification.rationale}
                  </p>
                </div>

                {/* Evidence */}
                {selectedEscalation.patch.evidence.length > 0 && (
                  <div className="mb-6">
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">
                      Evidence ({selectedEscalation.patch.evidence.length})
                    </h4>
                    <EvidenceGroup evidence={selectedEscalation.patch.evidence} maxDisplay={5} />
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-4 border-t border-gray-200">
                  <button
                    onClick={() => handleApprove(selectedEscalation)}
                    disabled={processingId === selectedEscalation.id}
                    className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                  >
                    <CheckCircle className="h-4 w-4" />
                    {processingId === selectedEscalation.id ? 'Applying...' : 'Approve & Apply'}
                  </button>
                  <button
                    onClick={() => handleModify(selectedEscalation)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
                  >
                    <Edit className="h-4 w-4" />
                    Modify
                  </button>
                  <button
                    onClick={() => handleReject(selectedEscalation)}
                    disabled={processingId === selectedEscalation.id}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    <X className="h-4 w-4" />
                    {processingId === selectedEscalation.id ? 'Rejecting...' : 'Reject'}
                  </button>
                </div>

                {/* View Entity */}
                <button
                  onClick={() => handleModify(selectedEscalation)}
                  className="w-full mt-3 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center justify-center gap-2"
                >
                  <ExternalLink className="h-4 w-4" />
                  View Full Entity
                </button>
              </div>
            ) : (
              <div className="bg-gray-50 rounded-lg border border-gray-200 p-12 text-center">
                <Info className="h-12 w-12 text-gray-400 mx-auto mb-3" />
                <p className="text-gray-600">Select an escalation to review details</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
