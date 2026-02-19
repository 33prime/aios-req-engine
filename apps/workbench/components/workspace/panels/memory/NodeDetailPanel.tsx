/**
 * NodeDetailPanel — Slide-in detail for a selected graph node
 *
 * Shows: node info, confidence bar, feedback actions (confirm/dispute/archive),
 * edit capability, supporting/contradicting facts, belief history sparkline.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { X, ThumbsUp, ThumbsDown, Archive, Pencil, Check, ChevronRight } from 'lucide-react'
import { getIntelligenceNodeDetail, getConfidenceCurve } from '@/lib/api'
import type { IntelGraphNode, IntelNodeDetail, IntelConfidenceCurve } from '@/types/workspace'

interface NodeDetailPanelProps {
  projectId: string
  node: IntelGraphNode
  onClose: () => void
  onFeedback: (nodeId: string, action: 'confirm' | 'dispute' | 'archive', note?: string) => void
}

export function NodeDetailPanel({ projectId, node, onClose, onFeedback }: NodeDetailPanelProps) {
  const [detail, setDetail] = useState<IntelNodeDetail | null>(null)
  const [curve, setCurve] = useState<IntelConfidenceCurve | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showDisputeInput, setShowDisputeInput] = useState(false)
  const [disputeNote, setDisputeNote] = useState('')
  const [feedbackPending, setFeedbackPending] = useState(false)

  useEffect(() => {
    setIsLoading(true)
    setShowDisputeInput(false)
    setDisputeNote('')

    getIntelligenceNodeDetail(projectId, node.id)
      .then(setDetail)
      .catch(() => setDetail(null))
      .finally(() => setIsLoading(false))

    if (node.node_type === 'belief') {
      getConfidenceCurve(projectId, node.id)
        .then(setCurve)
        .catch(() => setCurve(null))
    } else {
      setCurve(null)
    }
  }, [projectId, node.id, node.node_type])

  const handleConfirm = useCallback(async () => {
    setFeedbackPending(true)
    await onFeedback(node.id, 'confirm')
    setFeedbackPending(false)
  }, [node.id, onFeedback])

  const handleDispute = useCallback(async () => {
    if (!showDisputeInput) {
      setShowDisputeInput(true)
      return
    }
    setFeedbackPending(true)
    await onFeedback(node.id, 'dispute', disputeNote || undefined)
    setFeedbackPending(false)
    setShowDisputeInput(false)
    setDisputeNote('')
  }, [node.id, onFeedback, showDisputeInput, disputeNote])

  const handleArchive = useCallback(async () => {
    setFeedbackPending(true)
    await onFeedback(node.id, 'archive')
    setFeedbackPending(false)
    onClose()
  }, [node.id, onFeedback, onClose])

  const confidencePct = Math.round(node.confidence * 100)

  return (
    <div className="p-5">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <span
            className={`inline-block text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full mb-2 ${
              node.node_type === 'fact'
                ? 'bg-emerald-100 text-emerald-700'
                : node.node_type === 'belief'
                  ? 'bg-[#0A1E2F]/10 text-[#0A1E2F]'
                  : 'bg-gray-100 text-gray-600'
            }`}
          >
            {node.node_type}
          </span>
          {node.consultant_status && (
            <span
              className={`inline-block ml-2 text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                node.consultant_status === 'confirmed'
                  ? 'bg-[#E8F5E9] text-[#25785A]'
                  : 'bg-gray-100 text-gray-500'
              }`}
            >
              {node.consultant_status}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-gray-100 text-[#999999]"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Summary */}
      <p className="text-sm font-medium text-[#333333] mb-2">{node.summary}</p>

      {/* Content */}
      <p className="text-[12px] text-[#666666] mb-4 whitespace-pre-wrap leading-relaxed">
        {node.content}
      </p>

      {/* Confidence bar */}
      {node.node_type !== 'fact' && (
        <div className="mb-4">
          <div className="flex items-center justify-between text-[11px] mb-1">
            <span className="text-[#666666]">Confidence</span>
            <span className="font-medium text-[#333333]">{confidencePct}%</span>
          </div>
          <div className="w-full bg-[#F0F0F0] rounded-full h-2">
            <div
              className="h-2 rounded-full bg-[#3FAF7A] transition-all"
              style={{ width: `${confidencePct}%` }}
            />
          </div>
        </div>
      )}

      {/* Mini sparkline for beliefs */}
      {curve && curve.points.length > 1 && (
        <div className="mb-4">
          <p className="text-[11px] text-[#666666] mb-1">Confidence history</p>
          <svg viewBox="0 0 200 40" className="w-full h-8">
            <polyline
              fill="none"
              stroke="#3FAF7A"
              strokeWidth="2"
              points={curve.points.map((p, i) => {
                const x = (i / (curve.points.length - 1)) * 200
                const y = 40 - p.confidence * 40
                return `${x},${y}`
              }).join(' ')}
            />
          </svg>
        </div>
      )}

      {/* Feedback actions */}
      <div className="flex items-center gap-2 mb-4 pb-4 border-b border-[#E5E5E5]">
        <button
          onClick={handleConfirm}
          disabled={feedbackPending || node.consultant_status === 'confirmed'}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-lg transition-colors disabled:opacity-50 ${
            node.consultant_status === 'confirmed'
              ? 'bg-[#E8F5E9] text-[#25785A]'
              : 'text-[#25785A] hover:bg-[#E8F5E9]'
          }`}
        >
          {node.consultant_status === 'confirmed' ? (
            <Check className="w-3.5 h-3.5" />
          ) : (
            <ThumbsUp className="w-3.5 h-3.5" />
          )}
          {node.consultant_status === 'confirmed' ? 'Confirmed' : 'Confirm'}
        </button>
        <button
          onClick={handleDispute}
          disabled={feedbackPending}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium rounded-lg transition-colors disabled:opacity-50 ${
            node.consultant_status === 'disputed'
              ? 'bg-gray-100 text-gray-600'
              : 'text-[#666666] hover:bg-gray-100'
          }`}
        >
          <ThumbsDown className="w-3.5 h-3.5" />
          Dispute
        </button>
        <button
          onClick={handleArchive}
          disabled={feedbackPending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[11px] font-medium text-[#999999] hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
        >
          <Archive className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Dispute note input */}
      {showDisputeInput && (
        <div className="mb-4 pb-4 border-b border-[#E5E5E5]">
          <textarea
            value={disputeNote}
            onChange={(e) => setDisputeNote(e.target.value)}
            placeholder="Why do you dispute this? (optional)"
            className="w-full text-[12px] border border-[#E5E5E5] rounded-lg px-3 py-2 text-[#333333] placeholder:text-[#999999] focus:outline-none focus:ring-1 focus:ring-[#3FAF7A] resize-none"
            rows={2}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={handleDispute}
              disabled={feedbackPending}
              className="px-3 py-1 text-[11px] font-medium text-white bg-[#333333] hover:bg-[#0A1E2F] rounded-lg transition-colors disabled:opacity-50"
            >
              Submit Dispute
            </button>
            <button
              onClick={() => { setShowDisputeInput(false); setDisputeNote('') }}
              className="px-3 py-1 text-[11px] font-medium text-[#666666] hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Metadata */}
      <div className="space-y-1.5 text-[11px] text-[#666666] mb-4">
        {node.belief_domain && (
          <p>Domain: <span className="font-medium text-[#333333]">{node.belief_domain.replace('_', ' ')}</span></p>
        )}
        {node.source_type && (
          <p>Source: <span className="font-medium text-[#333333]">{node.source_type}</span></p>
        )}
        {node.linked_entity_type && (
          <p>Linked to: <span className="font-medium text-[#333333]">{node.linked_entity_type}</span></p>
        )}
        <p>Created: <span className="font-medium text-[#333333]">{new Date(node.created_at).toLocaleDateString()}</span></p>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-4">
          <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-[#3FAF7A]" />
        </div>
      ) : detail && (
        <>
          {/* Supporting facts */}
          {detail.supporting_facts.length > 0 && (
            <div className="mb-4">
              <h6 className="text-[11px] font-semibold text-[#333333] uppercase tracking-wide mb-2">
                Supporting ({detail.supporting_facts.length})
              </h6>
              <div className="space-y-1.5">
                {detail.supporting_facts.map((f) => (
                  <div key={f.id} className="bg-[#F4F4F4] rounded-lg px-3 py-2">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="text-[9px] font-semibold uppercase text-emerald-600">{f.node_type}</span>
                    </div>
                    <p className="text-[11px] text-[#333333]">{f.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Contradicting facts */}
          {detail.contradicting_facts.length > 0 && (
            <div className="mb-4">
              <h6 className="text-[11px] font-semibold text-[#333333] uppercase tracking-wide mb-2">
                Contradicting ({detail.contradicting_facts.length})
              </h6>
              <div className="space-y-1.5">
                {detail.contradicting_facts.map((f) => (
                  <div key={f.id} className="bg-[#F4F4F4] rounded-lg px-3 py-2 border-l-2 border-gray-400">
                    <p className="text-[11px] text-[#333333]">{f.summary}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* History */}
          {detail.history.length > 0 && (
            <div>
              <h6 className="text-[11px] font-semibold text-[#333333] uppercase tracking-wide mb-2">
                History ({detail.history.length})
              </h6>
              <div className="space-y-2">
                {detail.history.slice(0, 5).map((h) => (
                  <div key={h.id} className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-[#3FAF7A] mt-1.5 shrink-0" />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 text-[10px] text-[#999999]">
                        <span className="font-medium text-[#666666]">
                          {h.change_type.replace('_', ' ')}
                        </span>
                        {h.previous_confidence !== h.new_confidence && (
                          <span>
                            {Math.round(h.previous_confidence * 100)}% → {Math.round(h.new_confidence * 100)}%
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-[#666666] mt-0.5">{h.change_reason}</p>
                      <p className="text-[10px] text-[#999999] mt-0.5">
                        {new Date(h.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Consultant note (if disputed) */}
      {node.consultant_note && (
        <div className="mt-4 pt-4 border-t border-[#E5E5E5]">
          <p className="text-[11px] text-[#666666]">
            <span className="font-medium">Consultant note:</span> {node.consultant_note}
          </p>
        </div>
      )}
    </div>
  )
}
