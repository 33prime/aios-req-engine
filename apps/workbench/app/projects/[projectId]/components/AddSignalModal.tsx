/**
 * AddSignalModal Component
 *
 * Modal for adding client signals:
 * - Text input area
 * - Source/type fields
 * - Submit to API
 */

'use client'

import React, { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui'

interface AddSignalModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  onSuccess: () => void
}

export function AddSignalModal({ isOpen, onClose, projectId, onSuccess }: AddSignalModalProps) {
  const [source, setSource] = useState('')
  const [signalType, setSignalType] = useState('client_communication')
  const [rawText, setRawText] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!rawText.trim() || !source.trim()) {
      alert('Please fill in all required fields')
      return
    }

    try {
      setSubmitting(true)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/signals`, {
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

      // Reset form
      setSource('')
      setSignalType('client_communication')
      setRawText('')

      // Close modal and refresh
      onSuccess()
      onClose()
    } catch (error) {
      console.error('Failed to create signal:', error)
      alert('Failed to create signal. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Client Signal"
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={submitting}>
            Add Signal
          </Button>
        </>
      }
    >
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
          <p className="text-xs text-ui-supportText mt-1">
            Where did this signal come from?
          </p>
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
            <option value="client_communication">Client Communication</option>
            <option value="meeting_notes">Meeting Notes</option>
            <option value="requirements_doc">Requirements Document</option>
            <option value="user_feedback">User Feedback</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label htmlFor="rawText" className="block text-sm font-medium text-ui-bodyText mb-2">
            Signal Content <span className="text-red-600">*</span>
          </label>
          <textarea
            id="rawText"
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            placeholder="Paste the full text of the client signal here..."
            rows={12}
            className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent font-mono text-sm"
            required
          />
          <p className="text-xs text-ui-supportText mt-1">
            The AI will extract requirements from this text
          </p>
        </div>
      </form>
    </Modal>
  )
}
