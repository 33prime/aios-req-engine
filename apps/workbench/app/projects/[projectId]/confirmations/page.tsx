'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft,
  CheckSquare,
  MessageSquare,
  Phone,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  ExternalLink,
  Eye
} from 'lucide-react'
import { listConfirmations, updateConfirmationStatus, getSignal, getSignalChunks } from '@/lib/api'
import { Confirmation, Signal, SignalChunk } from '@/types/api'

export default function ConfirmationsPage() {
  const params = useParams()
  const projectId = params.projectId as string

  const [confirmations, setConfirmations] = useState<Confirmation[]>([])
  const [selectedConfirmation, setSelectedConfirmation] = useState<Confirmation | null>(null)
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [signalChunks, setSignalChunks] = useState<SignalChunk[]>([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<string>('open')

  useEffect(() => {
    loadConfirmations()
  }, [projectId, statusFilter])

  const loadConfirmations = async () => {
    try {
      setLoading(true)
      const response = await listConfirmations(projectId, statusFilter === 'all' ? undefined : statusFilter)
      setConfirmations(response.confirmations)
    } catch (error) {
      console.error('Failed to load confirmations:', error)
      alert('Failed to load confirmations')
    } finally {
      setLoading(false)
    }
  }

  const handleStatusUpdate = async (confirmationId: string, newStatus: string, resolutionEvidence?: any) => {
    try {
      setUpdating(confirmationId)
      await updateConfirmationStatus(confirmationId, newStatus, resolutionEvidence)
      await loadConfirmations() // Refresh list
      setSelectedConfirmation(null) // Close detail view
    } catch (error) {
      console.error('Failed to update confirmation:', error)
      alert('Failed to update confirmation')
    } finally {
      setUpdating(null)
    }
  }

  const viewEvidence = async (chunkId: string) => {
    try {
      // Find the signal ID from evidence
      const confirmation = confirmations.find(c => c.evidence.some(e => e.chunk_id === chunkId))
      if (!confirmation) return

      const evidence = confirmation.evidence.find(e => e.chunk_id === chunkId)
      if (!evidence) return

      // Load signal details
      const signal = await getSignal(chunkId.split('-')[0]) // Extract signal ID from chunk ID
      const chunks = await getSignalChunks(chunkId.split('-')[0])

      setSelectedSignal(signal)
      setSignalChunks(chunks.chunks)
    } catch (error) {
      console.error('Failed to load evidence:', error)
      alert('Failed to load evidence details')
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'resolved':
        return <CheckCircle className="h-5 w-5 text-green-600" />
      case 'dismissed':
        return <XCircle className="h-5 w-5 text-gray-600" />
      case 'queued':
        return <Clock className="h-5 w-5 text-yellow-600" />
      default:
        return <AlertCircle className="h-5 w-5 text-orange-600" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'border-l-red-500 bg-red-50'
      case 'medium':
        return 'border-l-yellow-500 bg-yellow-50'
      default:
        return 'border-l-green-500 bg-green-50'
    }
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href={`/projects/${projectId}`} className="btn btn-secondary">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Confirmations</h1>
              <p className="text-gray-600 mt-1">
                {confirmations.length} confirmation{confirmations.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>

          <div className="flex space-x-2">
            {['open', 'queued', 'resolved', 'dismissed', 'all'].map((status) => (
              <button
                key={status}
                onClick={() => setStatusFilter(status)}
                className={`px-4 py-2 rounded-md text-sm font-medium ${
                  statusFilter === status
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                }`}
              >
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Confirmations List */}
        <div className="lg:col-span-2">
          <div className="space-y-4">
            {confirmations.map((confirmation) => (
              <div
                key={confirmation.id}
                className={`border-l-4 p-6 rounded-r-lg cursor-pointer transition-colors hover:bg-gray-50 ${
                  selectedConfirmation?.id === confirmation.id ? 'ring-2 ring-blue-500' : ''
                } ${getPriorityColor(confirmation.priority)}`}
                onClick={() => setSelectedConfirmation(confirmation)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      {getStatusIcon(confirmation.status)}
                      <h3 className="text-lg font-semibold text-gray-900">
                        {confirmation.title}
                      </h3>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        confirmation.kind === 'feature' ? 'bg-blue-100 text-blue-800' :
                        confirmation.kind === 'prd' ? 'bg-green-100 text-green-800' :
                        confirmation.kind === 'vp' ? 'bg-purple-100 text-purple-800' :
                        confirmation.kind === 'insight' ? 'bg-orange-100 text-orange-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {confirmation.kind}
                      </span>
                    </div>

                    <p className="text-gray-700 mb-3">{confirmation.ask}</p>

                    <div className="flex items-center space-x-4 text-sm text-gray-600">
                      <div className="flex items-center">
                        {confirmation.suggested_method === 'email' ? (
                          <MessageSquare className="h-4 w-4 mr-1" />
                        ) : (
                          <Phone className="h-4 w-4 mr-1" />
                        )}
                        {confirmation.suggested_method}
                      </div>
                      <div className="flex items-center">
                        <AlertCircle className="h-4 w-4 mr-1" />
                        {confirmation.evidence.length} evidence item{confirmation.evidence.length !== 1 ? 's' : ''}
                      </div>
                      <div className="text-xs text-gray-500">
                        {new Date(confirmation.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>

                  <div className="ml-4 flex-shrink-0">
                    <Eye className="h-5 w-5 text-gray-400" />
                  </div>
                </div>
              </div>
            ))}

            {confirmations.length === 0 && (
              <div className="text-center py-12">
                <CheckSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  {statusFilter === 'open' ? 'No open confirmations' : `No ${statusFilter} confirmations`}
                </h3>
                <p className="text-gray-600">
                  {statusFilter === 'open'
                    ? 'All items have been resolved or no confirmations need attention.'
                    : `No confirmations with ${statusFilter} status.`}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Detail Panel */}
        <div className="lg:col-span-1">
          {selectedConfirmation ? (
            <div className="card sticky top-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">
                Confirmation Details
              </h3>

              <div className="space-y-6">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Why this needs confirmation</h4>
                  <p className="text-sm text-gray-600">{selectedConfirmation.why}</p>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Evidence</h4>
                  <div className="space-y-3">
                    {selectedConfirmation.evidence.map((evidence, idx) => (
                      <div key={idx} className="border border-gray-200 rounded-lg p-3">
                        <p className="text-sm text-gray-700 mb-2">"{evidence.excerpt}"</p>
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-500">{evidence.rationale}</span>
                          <button
                            onClick={() => viewEvidence(evidence.chunk_id)}
                            className="text-xs text-blue-600 hover:text-blue-800 flex items-center"
                          >
                            View source <ExternalLink className="h-3 w-3 ml-1" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Actions</h4>
                  <div className="space-y-2">
                    <button
                      onClick={() => handleStatusUpdate(selectedConfirmation.id, 'resolved', {
                        type: 'email',
                        ref: 'consultant_review',
                        note: 'Confirmed by consultant review'
                      })}
                      disabled={updating === selectedConfirmation.id}
                      className="w-full btn btn-success flex items-center justify-center"
                    >
                      {updating === selectedConfirmation.id ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      ) : (
                        <CheckCircle className="h-4 w-4 mr-2" />
                      )}
                      Confirm & Resolve
                    </button>

                    <button
                      onClick={() => handleStatusUpdate(selectedConfirmation.id, 'queued', {
                        type: 'meeting',
                        ref: 'needs_discussion',
                        note: 'Requires client meeting for clarification'
                      })}
                      disabled={updating === selectedConfirmation.id}
                      className="w-full btn btn-warning flex items-center justify-center"
                    >
                      {updating === selectedConfirmation.id ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-orange-600 mr-2"></div>
                      ) : (
                        <Phone className="h-4 w-4 mr-2" />
                      )}
                      Queue for Meeting
                    </button>

                    <button
                      onClick={() => handleStatusUpdate(selectedConfirmation.id, 'dismissed', {
                        type: 'consultant_decision',
                        ref: 'not_relevant',
                        note: 'Dismissed as not relevant to current scope'
                      })}
                      disabled={updating === selectedConfirmation.id}
                      className="w-full btn btn-secondary flex items-center justify-center"
                    >
                      {updating === selectedConfirmation.id ? (
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                      ) : (
                        <XCircle className="h-4 w-4 mr-2" />
                      )}
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="card sticky top-8">
              <div className="text-center py-8">
                <CheckSquare className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  Select a confirmation
                </h3>
                <p className="text-gray-600">
                  Click on any confirmation item to view details and take action.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Evidence Modal */}
      {selectedSignal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Evidence Source</h3>
                <button
                  onClick={() => setSelectedSignal(null)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <XCircle className="h-6 w-6" />
                </button>
              </div>
              <div className="mt-2 text-sm text-gray-600">
                <p><strong>Source:</strong> {selectedSignal.source}</p>
                <p><strong>Type:</strong> {selectedSignal.signal_type}</p>
                <p><strong>Date:</strong> {new Date(selectedSignal.created_at).toLocaleString()}</p>
              </div>
            </div>

            <div className="p-6 overflow-y-auto max-h-96">
              <div className="space-y-4">
                {signalChunks.map((chunk, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        Chunk {chunk.chunk_index + 1}
                      </span>
                      <span className="text-xs text-gray-500">
                        Characters {chunk.start_char}-{chunk.end_char}
                      </span>
                    </div>
                    <p className="text-sm text-gray-700">{chunk.content}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
