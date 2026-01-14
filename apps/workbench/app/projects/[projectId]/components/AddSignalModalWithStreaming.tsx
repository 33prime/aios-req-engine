/**
 * AddSignalModal Component (Enhanced with Streaming)
 *
 * Modal for adding client signals with real-time processing progress:
 * - Text input area
 * - Source/type fields
 * - Submit to API
 * - Show streaming progress automatically
 */

'use client'

import React, { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui'
import { useSignalStream } from '@/lib/useSignalStream'
import { StreamingProgress } from './StreamingProgress'

interface AddSignalModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  onSuccess: () => void
}

export function AddSignalModal({ isOpen, onClose, projectId, onSuccess }: AddSignalModalProps) {
  const [source, setSource] = useState('')
  const [signalType, setSignalType] = useState('note')
  const [rawText, setRawText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [uploadedSignalId, setUploadedSignalId] = useState<string | null>(null)

  // Streaming hook
  const stream = useSignalStream({
    onComplete: () => {
      // Refresh data when processing completes
      onSuccess()
    },
    onError: (error) => {
      console.error('Streaming error:', error)
    },
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!rawText.trim() || !source.trim()) {
      alert('Please fill in all required fields')
      return
    }

    try {
      setSubmitting(true)

      // Step 1: Upload signal
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          source: source.trim(),
          signal_type: signalType,
          raw_text: rawText.trim(),
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create signal')
      }

      const result = await response.json()
      const signalId = result.signal_id

      // Step 2: Start streaming processing
      setUploadedSignalId(signalId)
      stream.start(signalId, projectId)

      // Don't close modal yet - show streaming progress
      // Modal will close when user clicks "Done" after processing completes
    } catch (error) {
      console.error('Failed to create signal:', error)
      alert('Failed to create signal. Please try again.')
      setSubmitting(false)
    }
  }

  const handleClose = () => {
    if (stream.isStreaming) {
      if (!confirm('Processing is still in progress. Are you sure you want to close?')) {
        return
      }
      stream.stop()
    }

    // Reset state
    setSource('')
    setSignalType('note')
    setRawText('')
    setSubmitting(false)
    setUploadedSignalId(null)

    onClose()
  }

  const isProcessingComplete = uploadedSignalId && !stream.isStreaming && stream.progress === 100

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={uploadedSignalId ? 'Processing Signal' : 'Add Client Signal'}
      size="lg"
      footer={
        <>
          {!uploadedSignalId ? (
            <>
              <Button variant="outline" onClick={handleClose} disabled={submitting}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSubmit} loading={submitting}>
                Add Signal & Process
              </Button>
            </>
          ) : (
            <>
              {stream.isStreaming && (
                <Button variant="outline" onClick={handleClose}>
                  Close (Processing Continues)
                </Button>
              )}
              {isProcessingComplete && (
                <Button variant="primary" onClick={handleClose}>
                  Done
                </Button>
              )}
            </>
          )}
        </>
      }
    >
      {!uploadedSignalId ? (
        // Form view
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="source" className="block text-sm font-medium text-ui-bodyText mb-2">
              Source <span className="text-red-600">*</span>
            </label>
            <input
              type="text"
              id="source"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="e.g., Email from John Doe, Slack conversation, Meeting notes"
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent"
              required
            />
          </div>

          <div>
            <label htmlFor="signalType" className="block text-sm font-medium text-ui-bodyText mb-2">
              Signal Type
            </label>
            <select
              id="signalType"
              value={signalType}
              onChange={(e) => setSignalType(e.target.value)}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent"
            >
              <option value="note">Note</option>
              <option value="meeting">Meeting</option>
              <option value="email">Email</option>
              <option value="interview">Interview</option>
              <option value="document">Document</option>
            </select>
          </div>

          <div>
            <label htmlFor="rawText" className="block text-sm font-medium text-ui-bodyText mb-2">
              Content <span className="text-red-600">*</span>
            </label>
            <textarea
              id="rawText"
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              placeholder="Paste or type the signal content here..."
              rows={12}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent resize-none font-mono text-sm"
              required
            />
            <p className="text-xs text-ui-supportText mt-1">
              {rawText.length} characters
            </p>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-900">
              <strong>Automatic Processing:</strong> After uploading, the signal will automatically be processed through:
            </p>
            <ul className="text-sm text-blue-800 mt-2 ml-4 space-y-1 list-disc">
              <li>Build State (reconcile facts)</li>
              <li>Smart Research (if needed)</li>
              <li>Red Team (gap analysis)</li>
              <li>A-Team (solution generation)</li>
            </ul>
          </div>
        </form>
      ) : (
        // Streaming progress view
        <div className="space-y-4">
          <StreamingProgress
            isStreaming={stream.isStreaming}
            progress={stream.progress}
            currentPhase={stream.currentPhase}
            events={stream.events}
            error={stream.error}
          />
        </div>
      )}
    </Modal>
  )
}
