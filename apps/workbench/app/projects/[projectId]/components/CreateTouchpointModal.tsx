/**
 * CreateTouchpointModal Component
 *
 * Modal for consultants to create any type of collaboration touchpoint:
 * - Validation Round
 * - Refinement Call
 * - Prototype Review
 * - Feedback Session
 */

'use client'

import React, { useState } from 'react'
import { X, Loader2, CheckCircle2, FileText, Eye, MessageSquare, ClipboardCheck } from 'lucide-react'
import { createTouchpoint, type TouchpointType } from '@/lib/api'

interface TouchpointTypeConfig {
  type: TouchpointType
  label: string
  description: string
  icon: React.ReactNode
  defaultTitle: string
  color: string
}

const TOUCHPOINT_TYPES: TouchpointTypeConfig[] = [
  {
    type: 'validation_round',
    label: 'Validation Round',
    description: 'Confirm features and requirements with the client',
    icon: <ClipboardCheck className="w-6 h-6" />,
    defaultTitle: 'Validation Round',
    color: 'bg-blue-500',
  },
  {
    type: 'follow_up_call',
    label: 'Refinement Call',
    description: 'Clarify specific items and fill in gaps',
    icon: <MessageSquare className="w-6 h-6" />,
    defaultTitle: 'Refinement Call',
    color: 'bg-purple-500',
  },
  {
    type: 'prototype_review',
    label: 'Prototype Review',
    description: 'Get feedback on designs and prototypes',
    icon: <Eye className="w-6 h-6" />,
    defaultTitle: 'Prototype Review',
    color: 'bg-amber-500',
  },
  {
    type: 'feedback_session',
    label: 'Feedback Session',
    description: 'Ongoing iteration and feedback gathering',
    icon: <FileText className="w-6 h-6" />,
    defaultTitle: 'Feedback Session',
    color: 'bg-green-500',
  },
]

interface CreateTouchpointModalProps {
  projectId: string
  onClose: () => void
  onCreated?: () => void
}

export function CreateTouchpointModal({ projectId, onClose, onCreated }: CreateTouchpointModalProps) {
  const [selectedType, setSelectedType] = useState<TouchpointType | null>(null)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleTypeSelect = (config: TouchpointTypeConfig) => {
    setSelectedType(config.type)
    if (!title || TOUCHPOINT_TYPES.some(t => t.defaultTitle === title)) {
      setTitle(config.defaultTitle)
    }
  }

  const handleCreate = async () => {
    if (!selectedType || !title.trim()) return

    try {
      setIsCreating(true)
      setError(null)

      await createTouchpoint(projectId, {
        type: selectedType,
        title: title.trim(),
        description: description.trim() || undefined,
      })

      onCreated?.()
      onClose()
    } catch (err: any) {
      console.error('Failed to create touchpoint:', err)
      setError(err.message || 'Failed to create touchpoint')
    } finally {
      setIsCreating(false)
    }
  }

  const selectedConfig = TOUCHPOINT_TYPES.find(t => t.type === selectedType)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">Create Touchpoint</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Touchpoint Type Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-3">
              What type of touchpoint is this?
            </label>
            <div className="grid grid-cols-2 gap-3">
              {TOUCHPOINT_TYPES.map((config) => (
                <button
                  key={config.type}
                  onClick={() => handleTypeSelect(config)}
                  className={`
                    p-4 rounded-xl border-2 text-left transition-all
                    ${selectedType === config.type
                      ? 'border-[#009b87] bg-[#009b87]/5'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                    }
                  `}
                >
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-lg ${config.color} text-white flex items-center justify-center shrink-0`}>
                      {config.icon}
                    </div>
                    <div className="min-w-0">
                      <h3 className="font-semibold text-gray-900">{config.label}</h3>
                      <p className="text-sm text-gray-500 mt-0.5">{config.description}</p>
                    </div>
                  </div>
                  {selectedType === config.type && (
                    <div className="mt-2 flex justify-end">
                      <CheckCircle2 className="w-5 h-5 text-[#009b87]" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Title Input */}
          {selectedType && (
            <div>
              <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1.5">
                Title
              </label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={selectedConfig?.defaultTitle || 'Enter a title'}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent"
              />
            </div>
          )}

          {/* Description Input */}
          {selectedType && (
            <div>
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1.5">
                Description <span className="text-gray-400">(optional)</span>
              </label>
              <textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Add any notes or context for this touchpoint..."
                rows={3}
                className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#009b87] focus:border-transparent resize-none"
              />
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-600 text-sm">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleCreate}
            disabled={!selectedType || !title.trim() || isCreating}
            className="px-4 py-2 text-sm font-medium text-white bg-[#009b87] hover:bg-[#008577] rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isCreating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Creating...
              </>
            ) : (
              'Create Touchpoint'
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
