/**
 * PrepReviewModal - Full review UI for discovery prep before sending
 *
 * Shows agenda, questions, and document recommendations.
 * Allows confirming/rejecting individual items before sending to portal.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  CheckCircle,
  XCircle,
  FileText,
  HelpCircle,
  Loader2,
  RefreshCw,
  Send,
  Sparkles,
  User,
} from 'lucide-react'
import { Modal } from '@/components/ui/Modal'
import {
  getDiscoveryPrep,
  generateDiscoveryPrep,
  confirmPrepQuestion,
  confirmPrepDocument,
} from '@/lib/api'
import type { DiscoveryPrepBundle, PrepQuestion, DocRecommendation } from '@/types/api'

interface PrepReviewModalProps {
  projectId: string
  isOpen: boolean
  onClose: () => void
  onRefresh?: () => void
  onSendRequest?: (questionCount: number, documentCount: number) => void
}

export function PrepReviewModal({
  projectId,
  isOpen,
  onClose,
  onRefresh,
  onSendRequest,
}: PrepReviewModalProps) {
  const [bundle, setBundle] = useState<DiscoveryPrepBundle | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [togglingId, setTogglingId] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const data = await getDiscoveryPrep(projectId)
      setBundle(data)
    } catch {
      setBundle(null)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    if (isOpen) {
      loadData()
    }
  }, [isOpen, loadData])

  const handleGenerate = async () => {
    try {
      setGenerating(true)
      const resp = await generateDiscoveryPrep(projectId)
      setBundle(resp.bundle)
      onRefresh?.()
    } finally {
      setGenerating(false)
    }
  }

  const handleToggleQuestion = async (questionId: string, currentConfirmed: boolean) => {
    try {
      setTogglingId(questionId)
      const updated = await confirmPrepQuestion(projectId, questionId, !currentConfirmed)
      setBundle(updated)
    } finally {
      setTogglingId(null)
    }
  }

  const handleToggleDocument = async (documentId: string, currentConfirmed: boolean) => {
    try {
      setTogglingId(documentId)
      const updated = await confirmPrepDocument(projectId, documentId, !currentConfirmed)
      setBundle(updated)
    } finally {
      setTogglingId(null)
    }
  }

  const confirmedQuestions = bundle?.questions.filter((q) => q.confirmed).length ?? 0
  const totalQuestions = bundle?.questions.length ?? 0
  const confirmedDocs = bundle?.documents.filter((d) => d.confirmed).length ?? 0
  const totalDocs = bundle?.documents.length ?? 0
  const isSent = bundle?.status === 'sent'

  const footer = bundle && !isSent ? (
    <div className="flex items-center justify-between w-full">
      <p className="text-sm text-[#999999]">
        {confirmedQuestions}/{totalQuestions} questions, {confirmedDocs}/{totalDocs} documents confirmed
      </p>
      <button
        onClick={() => onSendRequest?.(confirmedQuestions, confirmedDocs)}
        disabled={confirmedQuestions === 0 && confirmedDocs === 0}
        className="flex items-center gap-1.5 px-4 py-2 bg-[#3FAF7A] text-white text-sm font-medium rounded-lg hover:bg-[#25785A] disabled:opacity-50 transition-colors"
      >
        <Send className="h-4 w-4" />
        Send to Portal
      </button>
    </div>
  ) : undefined

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Discovery Prep Review" size="xl" footer={footer}>
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-6 w-6 text-[#3FAF7A] animate-spin" />
        </div>
      ) : !bundle ? (
        <div className="text-center py-16">
          <HelpCircle className="h-10 w-10 text-[#999999]/40 mx-auto mb-3" />
          <p className="text-[#333333] font-medium mb-1">No prep generated yet</p>
          <p className="text-sm text-[#999999] mb-4">
            Generate discovery prep questions and document recommendations.
          </p>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#3FAF7A] text-white text-sm font-medium rounded-lg hover:bg-[#25785A] disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {generating ? 'Generating...' : 'Generate Prep'}
          </button>
        </div>
      ) : (
        <div className="space-y-6 max-h-[60vh] overflow-y-auto">
          {/* Sent badge */}
          {isSent && (
            <div className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg text-green-700 text-sm">
              <CheckCircle className="h-4 w-4" />
              Already sent to portal
              {bundle.sent_to_portal_at && (
                <span className="text-green-600 text-xs ml-auto">
                  {new Date(bundle.sent_to_portal_at).toLocaleDateString()}
                </span>
              )}
            </div>
          )}

          {/* Agenda Summary */}
          {bundle.agenda_summary && (
            <div className="bg-[#F9F9F9] rounded-lg p-4">
              <h3 className="text-sm font-semibold text-[#333333] mb-2">Agenda Summary</h3>
              <p className="text-sm text-[#333333] mb-2">{bundle.agenda_summary}</p>
              {bundle.agenda_bullets.length > 0 && (
                <ul className="list-disc list-inside space-y-1">
                  {bundle.agenda_bullets.map((bullet, i) => (
                    <li key={i} className="text-sm text-[#333333]">{bullet}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {/* Questions */}
          {totalQuestions > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-[#333333] mb-3 flex items-center gap-2">
                <HelpCircle className="h-4 w-4 text-[#3FAF7A]" />
                Questions ({confirmedQuestions}/{totalQuestions} confirmed)
              </h3>
              <div className="space-y-2">
                {bundle.questions.map((q) => (
                  <QuestionRow
                    key={q.id}
                    question={q}
                    disabled={isSent || togglingId === q.id}
                    toggling={togglingId === q.id}
                    onToggle={() => handleToggleQuestion(q.id, q.confirmed)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Documents */}
          {totalDocs > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-[#333333] mb-3 flex items-center gap-2">
                <FileText className="h-4 w-4 text-[#3FAF7A]" />
                Requested Documents ({confirmedDocs}/{totalDocs} confirmed)
              </h3>
              <div className="space-y-2">
                {bundle.documents.map((d) => (
                  <DocumentRow
                    key={d.id}
                    document={d}
                    disabled={isSent || togglingId === d.id}
                    toggling={togglingId === d.id}
                    onToggle={() => handleToggleDocument(d.id, d.confirmed)}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Regenerate */}
          {!isSent && (
            <div className="pt-2 border-t border-[#E5E5E5]">
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="flex items-center gap-1.5 text-sm text-[#999999] hover:text-[#3FAF7A] transition-colors"
              >
                {generating ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="h-3.5 w-3.5" />
                )}
                Regenerate all
              </button>
            </div>
          )}
        </div>
      )}
    </Modal>
  )
}

// =============================================================================
// Sub-components
// =============================================================================

function QuestionRow({
  question,
  disabled,
  toggling,
  onToggle,
}: {
  question: PrepQuestion
  disabled: boolean
  toggling: boolean
  onToggle: () => void
}) {
  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${
      question.confirmed ? 'border-green-200 bg-green-50/50' : 'border-[#E5E5E5] bg-white'
    }`}>
      <button
        onClick={onToggle}
        disabled={disabled}
        className="mt-0.5 flex-shrink-0 disabled:opacity-50"
      >
        {toggling ? (
          <Loader2 className="h-5 w-5 text-[#999999] animate-spin" />
        ) : question.confirmed ? (
          <CheckCircle className="h-5 w-5 text-green-600" />
        ) : (
          <XCircle className="h-5 w-5 text-[#E5E5E5] hover:text-red-400 transition-colors" />
        )}
      </button>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[#333333]">{question.question}</p>
        <div className="flex items-center gap-3 mt-1.5">
          <span className="inline-flex items-center gap-1 text-xs text-[#999999]">
            <User className="h-3 w-3" />
            {question.best_answered_by}
          </span>
        </div>
        {question.why_important && (
          <p className="text-xs text-[#999999] mt-1">{question.why_important}</p>
        )}
      </div>
    </div>
  )
}

function DocumentRow({
  document,
  disabled,
  toggling,
  onToggle,
}: {
  document: DocRecommendation
  disabled: boolean
  toggling: boolean
  onToggle: () => void
}) {
  const priorityClasses: Record<string, string> = {
    high: 'bg-red-100 text-red-700',
    medium: 'bg-amber-100 text-amber-700',
    low: 'bg-gray-100 text-gray-600',
  }

  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${
      document.confirmed ? 'border-green-200 bg-green-50/50' : 'border-[#E5E5E5] bg-white'
    }`}>
      <button
        onClick={onToggle}
        disabled={disabled}
        className="mt-0.5 flex-shrink-0 disabled:opacity-50"
      >
        {toggling ? (
          <Loader2 className="h-5 w-5 text-[#999999] animate-spin" />
        ) : document.confirmed ? (
          <CheckCircle className="h-5 w-5 text-green-600" />
        ) : (
          <XCircle className="h-5 w-5 text-[#E5E5E5] hover:text-red-400 transition-colors" />
        )}
      </button>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-[#333333]">{document.document_name}</p>
          <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
            priorityClasses[document.priority] || priorityClasses.low
          }`}>
            {document.priority}
          </span>
        </div>
        {document.why_important && (
          <p className="text-xs text-[#999999] mt-1">{document.why_important}</p>
        )}
      </div>
    </div>
  )
}
