'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/Button'
import { X, Plus, Trash2 } from 'lucide-react'

interface ResearchAgentModalProps {
  projectId: string
  seedContext?: {
    client_name: string
    industry: string
    competitors: string[]
    focus_areas: string[]
    custom_questions: string[]
  }
  onUpdate?: (context: any) => void
  onSubmit?: () => void
  onSuccess?: () => void
  onClose: () => void
}

const defaultSeedContext = {
  client_name: '',
  industry: '',
  competitors: [],
  focus_areas: [],
  custom_questions: [],
}

export function ResearchAgentModal({
  projectId,
  seedContext = defaultSeedContext,
  onUpdate,
  onSubmit,
  onSuccess,
  onClose,
}: ResearchAgentModalProps) {
  const [localContext, setLocalContext] = useState(seedContext)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [newCompetitor, setNewCompetitor] = useState('')
  const [newFocusArea, setNewFocusArea] = useState('')
  const [newQuestion, setNewQuestion] = useState('')

  const handleAdd = (field: 'competitors' | 'focus_areas' | 'custom_questions', value: string) => {
    if (!value.trim()) return
    setLocalContext({
      ...localContext,
      [field]: [...localContext[field], value.trim()],
    })
    if (field === 'competitors') setNewCompetitor('')
    if (field === 'focus_areas') setNewFocusArea('')
    if (field === 'custom_questions') setNewQuestion('')
  }

  const handleRemove = (field: 'competitors' | 'focus_areas' | 'custom_questions', index: number) => {
    setLocalContext({
      ...localContext,
      [field]: localContext[field].filter((_, i) => i !== index),
    })
  }

  const handleSubmit = async () => {
    // Validate required fields
    if (!localContext.client_name || !localContext.industry) {
      alert('Please fill in Client Name and Industry')
      return
    }

    // If using old-style callbacks (from page.tsx)
    if (onUpdate && onSubmit) {
      onUpdate(localContext)
      onSubmit()
      return
    }

    // New style: call API directly (from ResearchTab)
    try {
      setIsSubmitting(true)

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE}/v1/agents/research`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          seed_context: localContext,
          max_queries: 15,
        }),
      })

      if (!response.ok) {
        throw new Error(await response.text())
      }

      const result = await response.json()
      console.log('✅ Research Agent started:', result)

      if (onSuccess) {
        onSuccess()
      }

      onClose()
    } catch (error) {
      console.error('❌ Failed to run research agent:', error)
      alert('Failed to start research agent')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-ui-cardBorder">
          <div>
            <h2 className="text-xl font-semibold text-ui-text-primary">Research Agent</h2>
            <p className="text-sm text-ui-text-tertiary mt-1">
              Configure competitive & market research parameters
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-ui-text-tertiary hover:text-ui-text-primary"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form */}
        <div className="p-6 space-y-6">
          {/* Client Name */}
          <div>
            <label className="block text-sm font-medium text-ui-text-primary mb-2">
              Client Name *
            </label>
            <input
              type="text"
              value={localContext.client_name}
              onChange={(e) => setLocalContext({ ...localContext, client_name: e.target.value })}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-blue"
              placeholder="e.g., Acme Corp"
              required
            />
          </div>

          {/* Industry */}
          <div>
            <label className="block text-sm font-medium text-ui-text-primary mb-2">
              Industry *
            </label>
            <input
              type="text"
              value={localContext.industry}
              onChange={(e) => setLocalContext({ ...localContext, industry: e.target.value })}
              className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-blue"
              placeholder="e.g., HR Tech, FinTech, Healthcare"
              required
            />
          </div>

          {/* Competitors */}
          <div>
            <label className="block text-sm font-medium text-ui-text-primary mb-2">
              Competitors (optional)
            </label>
            <div className="space-y-2">
              {localContext.competitors.map((comp, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1 px-3 py-2 bg-ui-cardBg border border-ui-cardBorder rounded-lg text-sm">
                    {comp}
                  </div>
                  <button
                    onClick={() => handleRemove('competitors', i)}
                    className="p-2 text-ui-text-tertiary hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newCompetitor}
                  onChange={(e) => setNewCompetitor(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAdd('competitors', newCompetitor)}
                  className="flex-1 px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-blue text-sm"
                  placeholder="e.g., BambooHR, Rippling"
                />
                <Button
                  onClick={() => handleAdd('competitors', newCompetitor)}
                  variant="secondary"
                  icon={<Plus className="h-4 w-4" />}
                >
                  Add
                </Button>
              </div>
            </div>
          </div>

          {/* Focus Areas */}
          <div>
            <label className="block text-sm font-medium text-ui-text-primary mb-2">
              Focus Areas (optional)
            </label>
            <div className="space-y-2">
              {localContext.focus_areas.map((area, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1 px-3 py-2 bg-ui-cardBg border border-ui-cardBorder rounded-lg text-sm">
                    {area}
                  </div>
                  <button
                    onClick={() => handleRemove('focus_areas', i)}
                    className="p-2 text-ui-text-tertiary hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newFocusArea}
                  onChange={(e) => setNewFocusArea(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAdd('focus_areas', newFocusArea)}
                  className="flex-1 px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-blue text-sm"
                  placeholder="e.g., onboarding automation, mobile UX"
                />
                <Button
                  onClick={() => handleAdd('focus_areas', newFocusArea)}
                  variant="secondary"
                  icon={<Plus className="h-4 w-4" />}
                >
                  Add
                </Button>
              </div>
            </div>
          </div>

          {/* Custom Questions */}
          <div>
            <label className="block text-sm font-medium text-ui-text-primary mb-2">
              Custom Questions (optional)
            </label>
            <div className="space-y-2">
              {localContext.custom_questions.map((q, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="flex-1 px-3 py-2 bg-ui-cardBg border border-ui-cardBorder rounded-lg text-sm">
                    {q}
                  </div>
                  <button
                    onClick={() => handleRemove('custom_questions', i)}
                    className="p-2 text-ui-text-tertiary hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newQuestion}
                  onChange={(e) => setNewQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAdd('custom_questions', newQuestion)}
                  className="flex-1 px-3 py-2 border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-blue text-sm"
                  placeholder="e.g., What are top mobile-first features in 2025?"
                />
                <Button
                  onClick={() => handleAdd('custom_questions', newQuestion)}
                  variant="secondary"
                  icon={<Plus className="h-4 w-4" />}
                >
                  Add
                </Button>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-ui-cardBorder bg-ui-cardBg">
          <Button variant="outline" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!localContext.client_name || !localContext.industry || isSubmitting}
          >
            {isSubmitting ? 'Starting Research...' : 'Run Research'}
          </Button>
        </div>
      </div>
    </div>
  )
}
