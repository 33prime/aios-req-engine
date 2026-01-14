/**
 * DiscoveryPrepSection Component
 *
 * Pre-call preparation interface for generating and managing
 * questions and document requests to send to clients via portal.
 */

'use client'

import React, { useState, useEffect } from 'react'
import {
  getDiscoveryPrep,
  generateDiscoveryPrep,
  confirmPrepQuestion,
  confirmPrepDocument,
  sendDiscoveryPrepToPortal,
  regeneratePrepQuestions,
  regeneratePrepDocuments,
} from '@/lib/api'
import type { DiscoveryPrepBundle, PrepQuestion, DocRecommendation } from '@/types/api'
import {
  Sparkles,
  Check,
  X,
  Loader2,
  FileText,
  MessageSquare,
  Send,
  RefreshCw,
  Calendar,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  CheckCircle2,
  User,
} from 'lucide-react'

interface DiscoveryPrepSectionProps {
  projectId: string
  projectName?: string
  portalEnabled?: boolean
}

export function DiscoveryPrepSection({
  projectId,
  projectName = 'Project',
  portalEnabled = false,
}: DiscoveryPrepSectionProps) {
  const [bundle, setBundle] = useState<DiscoveryPrepBundle | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [regenerating, setRegenerating] = useState<'questions' | 'documents' | null>(null)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(true)
  const [confirmingId, setConfirmingId] = useState<string | null>(null)

  // Load existing bundle on mount
  useEffect(() => {
    loadBundle()
  }, [projectId])

  const loadBundle = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getDiscoveryPrep(projectId)
      setBundle(data)
    } catch (err: any) {
      // 404 is expected if no bundle exists yet
      if (err.status !== 404) {
        console.error('Failed to load discovery prep:', err)
        setError('Failed to load discovery prep')
      }
      setBundle(null)
    } finally {
      setLoading(false)
    }
  }

  const handleGenerate = async () => {
    try {
      setGenerating(true)
      setError(null)
      const result = await generateDiscoveryPrep(projectId, false)
      setBundle(result.bundle)
    } catch (err: any) {
      console.error('Failed to generate:', err)
      setError('Failed to generate discovery prep. Please try again.')
    } finally {
      setGenerating(false)
    }
  }

  const handleRegenerateQuestions = async () => {
    try {
      setRegenerating('questions')
      setError(null)
      const updated = await regeneratePrepQuestions(projectId)
      setBundle(updated)
    } catch (err) {
      console.error('Failed to regenerate questions:', err)
      setError('Failed to regenerate questions')
    } finally {
      setRegenerating(null)
    }
  }

  const handleRegenerateDocuments = async () => {
    try {
      setRegenerating('documents')
      setError(null)
      const updated = await regeneratePrepDocuments(projectId)
      setBundle(updated)
    } catch (err) {
      console.error('Failed to regenerate documents:', err)
      setError('Failed to regenerate documents')
    } finally {
      setRegenerating(null)
    }
  }

  const handleConfirmQuestion = async (questionId: string, confirmed: boolean) => {
    try {
      setConfirmingId(questionId)
      const updated = await confirmPrepQuestion(projectId, questionId, confirmed)
      setBundle(updated)
    } catch (err) {
      console.error('Failed to confirm question:', err)
    } finally {
      setConfirmingId(null)
    }
  }

  const handleConfirmDocument = async (documentId: string, confirmed: boolean) => {
    try {
      setConfirmingId(documentId)
      const updated = await confirmPrepDocument(projectId, documentId, confirmed)
      setBundle(updated)
    } catch (err) {
      console.error('Failed to confirm document:', err)
    } finally {
      setConfirmingId(null)
    }
  }

  const handleSendToPortal = async () => {
    if (!bundle) return

    const confirmedQuestions = bundle.questions.filter(q => q.confirmed)
    const confirmedDocs = bundle.documents.filter(d => d.confirmed)

    if (confirmedQuestions.length === 0 && confirmedDocs.length === 0) {
      setError('Please confirm at least one question or document before sending.')
      return
    }

    try {
      setSending(true)
      setError(null)
      const result = await sendDiscoveryPrepToPortal(projectId)
      if (result.success) {
        await loadBundle() // Refresh to show updated status
        alert(`Sent ${result.questions_sent} questions and ${result.documents_sent} documents to portal.`)
      }
    } catch (err) {
      console.error('Failed to send to portal:', err)
      setError('Failed to send to portal')
    } finally {
      setSending(false)
    }
  }

  // Calculate stats
  const confirmedQuestions = bundle?.questions.filter(q => q.confirmed).length || 0
  const confirmedDocs = bundle?.documents.filter(d => d.confirmed).length || 0
  const totalConfirmed = confirmedQuestions + confirmedDocs

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      </div>
    )
  }

  // Empty state - no bundle yet
  if (!bundle) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <Calendar className="w-5 h-5 text-purple-600" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">Discovery Call Prep</h3>
            <p className="text-sm text-gray-500">Generate questions and document requests for your client</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <button
          onClick={handleGenerate}
          disabled={generating}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {generating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              Generate Pre-Call Prep
            </>
          )}
        </button>
      </div>
    )
  }

  // Bundle exists - show content
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
            <Calendar className="w-5 h-5 text-purple-600" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-gray-900">Discovery Call Prep</h3>
            <p className="text-sm text-gray-500">
              {bundle.status === 'sent'
                ? 'Sent to client portal'
                : `${totalConfirmed} of ${bundle.questions.length + bundle.documents.length} items confirmed`}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {bundle.status === 'sent' && (
            <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-medium rounded-full">
              Sent
            </span>
          )}
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="border-t border-gray-100">
          {error && (
            <div className="m-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm flex items-start gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {/* Agenda Section */}
          {bundle.agenda_summary && (
            <div className="p-4 border-b border-gray-100">
              <h4 className="text-sm font-medium text-gray-700 mb-2">Call Agenda</h4>
              <p className="text-gray-600 text-sm mb-3">{bundle.agenda_summary}</p>
              {bundle.agenda_bullets.length > 0 && (
                <ul className="space-y-1">
                  {bundle.agenda_bullets.map((bullet, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                      <span className="text-purple-500 mt-1">•</span>
                      {bullet}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Questions Section */}
          <div className="p-4 border-b border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Questions ({confirmedQuestions}/{bundle.questions.length} confirmed)
              </h4>
              <button
                onClick={handleRegenerateQuestions}
                disabled={regenerating !== null || bundle.status === 'sent'}
                className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 disabled:opacity-50"
              >
                {regenerating === 'questions' ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <RefreshCw className="w-3 h-3" />
                )}
                Regenerate
              </button>
            </div>

            <div className="space-y-3">
              {bundle.questions.map(question => (
                <QuestionCard
                  key={question.id}
                  question={question}
                  onConfirm={handleConfirmQuestion}
                  confirming={confirmingId === question.id}
                  disabled={bundle.status === 'sent'}
                />
              ))}
            </div>
          </div>

          {/* Documents Section */}
          <div className="p-4 border-b border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-medium text-gray-700 flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Documents ({confirmedDocs}/{bundle.documents.length} confirmed)
              </h4>
              <button
                onClick={handleRegenerateDocuments}
                disabled={regenerating !== null || bundle.status === 'sent'}
                className="text-xs text-gray-500 hover:text-gray-700 flex items-center gap-1 disabled:opacity-50"
              >
                {regenerating === 'documents' ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <RefreshCw className="w-3 h-3" />
                )}
                Regenerate
              </button>
            </div>

            <div className="space-y-3">
              {bundle.documents.map(doc => (
                <DocumentCard
                  key={doc.id}
                  document={doc}
                  onConfirm={handleConfirmDocument}
                  confirming={confirmingId === doc.id}
                  disabled={bundle.status === 'sent'}
                />
              ))}
            </div>
          </div>

          {/* Actions */}
          {bundle.status !== 'sent' && portalEnabled && (
            <div className="p-4 bg-gray-50">
              <button
                onClick={handleSendToPortal}
                disabled={sending || totalConfirmed === 0}
                className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-brand-primary text-white rounded-lg hover:bg-brand-primaryDark disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {sending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Send {totalConfirmed} Item{totalConfirmed !== 1 ? 's' : ''} to Client Portal
                  </>
                )}
              </button>
              {totalConfirmed === 0 && (
                <p className="text-xs text-gray-500 text-center mt-2">
                  Confirm at least one question or document to send
                </p>
              )}
            </div>
          )}

          {bundle.status === 'sent' && (
            <div className="p-4 bg-green-50">
              <div className="flex items-center gap-2 text-green-700">
                <CheckCircle2 className="w-5 h-5" />
                <span className="font-medium">Sent to client portal</span>
              </div>
              {bundle.sent_to_portal_at && (
                <p className="text-sm text-green-600 mt-1">
                  {new Date(bundle.sent_to_portal_at).toLocaleDateString()} at{' '}
                  {new Date(bundle.sent_to_portal_at).toLocaleTimeString()}
                </p>
              )}
            </div>
          )}

          {!portalEnabled && bundle.status !== 'sent' && (
            <div className="p-4 bg-amber-50">
              <p className="text-sm text-amber-700">
                Enable the client portal above to send these items to your client.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// Question Card Component
interface QuestionCardProps {
  question: PrepQuestion
  onConfirm: (id: string, confirmed: boolean) => void
  confirming: boolean
  disabled: boolean
}

function QuestionCard({ question, onConfirm, confirming, disabled }: QuestionCardProps) {
  return (
    <div
      className={`
        border rounded-lg p-3 transition-colors
        ${question.confirmed ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'}
      `}
    >
      <div className="flex items-start gap-3">
        <button
          onClick={() => onConfirm(question.id, !question.confirmed)}
          disabled={confirming || disabled}
          className={`
            flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors
            ${question.confirmed
              ? 'border-green-500 bg-green-500 text-white'
              : 'border-gray-300 hover:border-green-400'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          {confirming ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : question.confirmed ? (
            <Check className="w-3 h-3" />
          ) : null}
        </button>

        <div className="flex-1 min-w-0">
          <p className="text-gray-900 font-medium text-sm">{question.question}</p>

          <div className="flex items-center gap-4 mt-2 text-xs">
            <span className="flex items-center gap-1 text-gray-500">
              <User className="w-3 h-3" />
              {question.best_answered_by}
            </span>
          </div>

          <p className="text-xs text-gray-500 mt-1">{question.why_important}</p>

          {question.client_answer && (
            <div className="mt-2 p-2 bg-blue-50 rounded text-sm text-blue-800">
              <span className="font-medium">Client answer:</span> {question.client_answer}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Document Card Component
interface DocumentCardProps {
  document: DocRecommendation
  onConfirm: (id: string, confirmed: boolean) => void
  confirming: boolean
  disabled: boolean
}

function DocumentCard({ document, onConfirm, confirming, disabled }: DocumentCardProps) {
  const priorityColors = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-yellow-100 text-yellow-700',
    low: 'bg-gray-100 text-gray-600',
  }

  return (
    <div
      className={`
        border rounded-lg p-3 transition-colors
        ${document.confirmed ? 'border-green-200 bg-green-50' : 'border-gray-200 bg-white'}
      `}
    >
      <div className="flex items-start gap-3">
        <button
          onClick={() => onConfirm(document.id, !document.confirmed)}
          disabled={confirming || disabled}
          className={`
            flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors
            ${document.confirmed
              ? 'border-green-500 bg-green-500 text-white'
              : 'border-gray-300 hover:border-green-400'
            }
            ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
          `}
        >
          {confirming ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : document.confirmed ? (
            <Check className="w-3 h-3" />
          ) : null}
        </button>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-gray-400" />
            <p className="text-gray-900 font-medium text-sm">{document.document_name}</p>
            <span className={`text-xs px-2 py-0.5 rounded-full ${priorityColors[document.priority]}`}>
              {document.priority}
            </span>
          </div>

          <p className="text-xs text-gray-500 mt-1">{document.why_important}</p>

          {document.uploaded_file_id && (
            <div className="mt-2 flex items-center gap-1 text-xs text-green-600">
              <CheckCircle2 className="w-3 h-3" />
              Uploaded
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DiscoveryPrepSection
