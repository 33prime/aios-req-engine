/**
 * AddBeliefModal — Form to create a new belief node
 *
 * Fields: statement (required), domain (select), confidence (slider), optional entity link.
 * Created beliefs auto-get consultant_status='confirmed'.
 */

'use client'

import { useState, useCallback } from 'react'
import { X } from 'lucide-react'
import { createBelief } from '@/lib/api'
import type { IntelGraphNode } from '@/types/workspace'

interface AddBeliefModalProps {
  projectId: string
  onCreated: (node: IntelGraphNode) => void
  onClose: () => void
}

const DOMAINS = [
  { value: '', label: 'No domain' },
  { value: 'requirements', label: 'Requirements' },
  { value: 'technical', label: 'Technical' },
  { value: 'business', label: 'Business' },
  { value: 'user_experience', label: 'User Experience' },
  { value: 'process', label: 'Process' },
  { value: 'stakeholder', label: 'Stakeholder' },
  { value: 'market', label: 'Market' },
  { value: 'risk', label: 'Risk' },
]

export function AddBeliefModal({ projectId, onCreated, onClose }: AddBeliefModalProps) {
  const [statement, setStatement] = useState('')
  const [domain, setDomain] = useState('')
  const [confidence, setConfidence] = useState(70)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = useCallback(async () => {
    if (statement.trim().length < 5) {
      setError('Statement must be at least 5 characters.')
      return
    }

    setIsSubmitting(true)
    setError(null)

    try {
      const node = await createBelief(projectId, {
        statement: statement.trim(),
        domain: domain || undefined,
        confidence: confidence / 100,
      })
      onCreated(node)
    } catch (e) {
      setError('Failed to create belief. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }, [projectId, statement, domain, confidence, onCreated])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-8">
      <div className="absolute inset-0 bg-black/20" onClick={onClose} />
      <div className="relative bg-white rounded-2xl shadow-xl border border-border w-full max-w-md p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-base font-semibold text-text-body">Add Belief</h3>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 text-text-placeholder"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Statement */}
        <div className="mb-4">
          <label className="block text-[12px] font-medium text-text-body mb-1.5">
            Belief statement
          </label>
          <textarea
            value={statement}
            onChange={(e) => setStatement(e.target.value)}
            placeholder="e.g., Users prefer mobile-first onboarding"
            className="w-full text-sm border border-border rounded-xl px-4 py-3 text-text-body placeholder:text-text-placeholder focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary resize-none"
            rows={3}
            autoFocus
          />
        </div>

        {/* Domain */}
        <div className="mb-4">
          <label className="block text-[12px] font-medium text-text-body mb-1.5">
            Domain
          </label>
          <select
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            className="w-full text-sm border border-border rounded-xl px-4 py-2.5 text-text-body focus:outline-none focus:ring-2 focus:ring-brand-primary/30 focus:border-brand-primary bg-white"
          >
            {DOMAINS.map((d) => (
              <option key={d.value} value={d.value}>
                {d.label}
              </option>
            ))}
          </select>
        </div>

        {/* Confidence slider */}
        <div className="mb-5">
          <div className="flex items-center justify-between mb-1.5">
            <label className="text-[12px] font-medium text-text-body">
              Confidence
            </label>
            <span className="text-[12px] font-medium text-brand-primary">{confidence}%</span>
          </div>
          <input
            type="range"
            min={10}
            max={100}
            value={confidence}
            onChange={(e) => setConfidence(Number(e.target.value))}
            className="w-full h-2 bg-[#F0F0F0] rounded-full appearance-none cursor-pointer accent-brand-primary"
          />
          <div className="flex justify-between text-[10px] text-text-placeholder mt-1">
            <span>Low</span>
            <span>High</span>
          </div>
        </div>

        {/* Error */}
        {error && (
          <p className="text-[12px] text-red-600 mb-3">{error}</p>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-[#666666] hover:bg-gray-100 rounded-xl transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting || statement.trim().length < 5}
            className="px-6 py-2 text-sm font-medium text-white bg-brand-primary hover:bg-[#25785A] rounded-xl transition-colors disabled:opacity-50"
          >
            {isSubmitting ? 'Creating...' : 'Add Belief'}
          </button>
        </div>
      </div>
    </div>
  )
}
