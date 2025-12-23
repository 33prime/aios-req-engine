/**
 * AddResearchModal Component
 *
 * Modal for uploading research documents:
 * - File upload or text paste
 * - Document title and type
 * - Submit to research ingestion API
 */

'use client'

import React, { useState } from 'react'
import { Modal } from '@/components/ui/Modal'
import { Button } from '@/components/ui'
import { Upload } from 'lucide-react'

interface AddResearchModalProps {
  isOpen: boolean
  onClose: () => void
  projectId: string
  onSuccess: () => void
}

export function AddResearchModal({ isOpen, onClose, projectId, onSuccess }: AddResearchModalProps) {
  const [title, setTitle] = useState('')
  const [docType, setDocType] = useState('competitive_analysis')
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim() || !content.trim()) {
      alert('Please fill in all required fields')
      return
    }

    try {
      setSubmitting(true)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/research/ingest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          title: title.trim(),
          doc_type: docType,
          content: content.trim(),
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to upload research')
      }

      // Reset form
      setTitle('')
      setDocType('competitive_analysis')
      setContent('')

      // Close modal and refresh
      onSuccess()
      onClose()
    } catch (error) {
      console.error('Failed to upload research:', error)
      alert('Failed to upload research. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Add Research Document"
      size="lg"
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={submitting}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit} loading={submitting} icon={<Upload className="h-4 w-4" />}>
            Upload Research
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="title" className="block text-sm font-medium text-ui-bodyText mb-2">
            Document Title <span className="text-red-600">*</span>
          </label>
          <input
            type="text"
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g., Mobile Banking Competitive Analysis Q4 2024"
            className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent"
            required
          />
        </div>

        <div>
          <label htmlFor="docType" className="block text-sm font-medium text-ui-bodyText mb-2">
            Document Type
          </label>
          <select
            id="docType"
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent"
          >
            <option value="competitive_analysis">Competitive Analysis</option>
            <option value="market_research">Market Research</option>
            <option value="user_research">User Research</option>
            <option value="technical_spec">Technical Specification</option>
            <option value="industry_report">Industry Report</option>
            <option value="best_practices">Best Practices</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div>
          <label htmlFor="content" className="block text-sm font-medium text-ui-bodyText mb-2">
            Document Content <span className="text-red-600">*</span>
          </label>
          <textarea
            id="content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Paste the full research document content here..."
            rows={12}
            className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent font-mono text-sm"
            required
          />
          <p className="text-xs text-ui-supportText mt-1">
            This research will be used to enrich requirements and validate assumptions
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <strong>Note:</strong> Research documents are processed and indexed for semantic search.
            They will be used to validate assumptions and enrich PRD/VP content when research mode is enabled.
          </p>
        </div>
      </form>
    </Modal>
  )
}
