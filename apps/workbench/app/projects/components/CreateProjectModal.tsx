/**
 * CreateProjectModal Component
 *
 * Modal for creating new projects with optional description auto-ingestion
 *
 * Features:
 * - Name input (required, min 3 chars)
 * - Description textarea (optional)
 * - Auto-ingest toggle (default: checked)
 * - Validation and error handling
 */

'use client'

import React, { useState } from 'react'
import { X } from 'lucide-react'
import { createProject } from '@/lib/api'

interface CreateProjectModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: (response: { id: string; name: string; onboarding_job_id?: string }) => void
}

export function CreateProjectModal({ isOpen, onClose, onSuccess }: CreateProjectModalProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [autoIngest, setAutoIngest] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validation
    if (name.trim().length < 3) {
      setError('Project name must be at least 3 characters')
      return
    }

    try {
      setLoading(true)

      const response = await createProject({
        name: name.trim(),
        description: description.trim() || undefined,
        auto_ingest_description: autoIngest && !!description.trim(),
      })

      // Reset form
      setName('')
      setDescription('')
      setAutoIngest(true)

      // Call success handler with full response (includes onboarding_job_id)
      onSuccess({
        id: response.id,
        name: response.name,
        onboarding_job_id: response.onboarding_job_id,
      })
    } catch (err: unknown) {
      console.error('Failed to create project:', err)
      setError(err instanceof Error ? err.message : 'Failed to create project')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    if (!loading) {
      setName('')
      setDescription('')
      setAutoIngest(true)
      setError(null)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-border">
            <h2 className="text-xl font-semibold text-text-body">
              Create New Project
            </h2>
            <button
              onClick={handleClose}
              disabled={loading}
              className="p-1 rounded-lg hover:bg-surface-muted transition-colors disabled:opacity-50"
            >
              <X className="w-5 h-5 text-text-placeholder" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit}>
            <div className="p-6 space-y-6">
              {/* Error Alert */}
              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              {/* Name Input */}
              <div>
                <label htmlFor="project-name" className="block text-sm font-medium text-text-body mb-2">
                  Project Name <span className="text-red-500">*</span>
                </label>
                <input
                  id="project-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., Mobile Todo App"
                  disabled={loading}
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent disabled:bg-surface-muted disabled:opacity-50"
                  required
                  minLength={3}
                />
                <p className="text-xs text-text-placeholder mt-1">
                  Minimum 3 characters
                </p>
              </div>

              {/* Description Textarea */}
              <div>
                <label htmlFor="project-description" className="block text-sm font-medium text-text-body mb-2">
                  Project Description
                </label>
                <textarea
                  id="project-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe your project requirements, goals, and context..."
                  disabled={loading}
                  rows={6}
                  className="w-full px-4 py-2 border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent disabled:bg-surface-muted disabled:opacity-50 resize-none"
                />
                <p className="text-xs text-text-placeholder mt-1">
                  Optional. If provided, can be used as the first signal for your project.
                </p>
              </div>

              {/* Auto-ingest Checkbox */}
              {description.trim() && (
                <div className="flex items-start gap-3 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <input
                    id="auto-ingest"
                    type="checkbox"
                    checked={autoIngest}
                    onChange={(e) => setAutoIngest(e.target.checked)}
                    disabled={loading}
                    className="mt-1 w-4 h-4 text-brand-primary border-gray-300 rounded focus:ring-brand-primary disabled:opacity-50"
                  />
                  <div className="flex-1">
                    <label htmlFor="auto-ingest" className="text-sm font-medium text-text-body cursor-pointer">
                      Use description as first signal
                    </label>
                    <p className="text-xs text-text-placeholder mt-1">
                      Your description will be ingested as a signal and automatically processed to extract initial requirements. This helps jumpstart your project.
                    </p>
                  </div>
                </div>
              )}

              {/* Info Box */}
              <div className="p-4 bg-surface-muted rounded-lg border border-border">
                <h4 className="text-sm font-medium text-text-body mb-2">
                  What happens next?
                </h4>
                <ul className="space-y-2 text-sm text-text-placeholder">
                  <li className="flex items-start gap-2">
                    <span className="text-brand-primary mt-0.5">1.</span>
                    <span>Your project will be created in <strong>Initial mode</strong></span>
                  </li>
                  {description.trim() && autoIngest && (
                    <li className="flex items-start gap-2">
                      <span className="text-brand-primary mt-0.5">2.</span>
                      <span>Description will be ingested as your first signal</span>
                    </li>
                  )}
                  <li className="flex items-start gap-2">
                    <span className="text-brand-primary mt-0.5">{description.trim() && autoIngest ? '3' : '2'}.</span>
                    <span>Add more signals (emails, transcripts, documents)</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-brand-primary mt-0.5">{description.trim() && autoIngest ? '4' : '3'}.</span>
                    <span>Run "Build State" to generate your initial PRD</span>
                  </li>
                </ul>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-6 border-t border-border bg-surface-muted">
              <button
                type="button"
                onClick={handleClose}
                disabled={loading}
                className="px-4 py-2 text-sm font-medium text-text-body bg-white border border-border rounded-lg hover:bg-surface-subtle transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading || name.trim().length < 3}
                className="px-4 py-2 text-sm font-medium text-white bg-brand-primary rounded-lg hover:bg-brand-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Creating...
                  </span>
                ) : (
                  'Create Project'
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
