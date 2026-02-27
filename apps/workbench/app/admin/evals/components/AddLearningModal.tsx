'use client'

import { useState } from 'react'
import { X } from 'lucide-react'
import { createEvalLearning } from '@/lib/api'

const DIMENSIONS = [
  'feature_coverage',
  'structure',
  'mock_data',
  'flow',
  'feature_id',
  'handoff',
  'jsdoc',
  'route_count',
  'general',
]

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function AddLearningModal({ onClose, onCreated }: Props) {
  const [category, setCategory] = useState('general')
  const [learning, setLearning] = useState('')
  const [dimension, setDimension] = useState('')
  const [gapPattern, setGapPattern] = useState('')
  const [saving, setSaving] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!learning.trim()) return

    setSaving(true)
    try {
      await createEvalLearning({
        category,
        learning: learning.trim(),
        dimension: dimension || undefined,
        gap_pattern: gapPattern || undefined,
      })
      onCreated()
      onClose()
    } catch (err) {
      console.error('Failed to create learning:', err)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h3 className="text-[15px] font-semibold text-text-body">Add Learning</h3>
          <button onClick={onClose} className="text-text-placeholder hover:text-text-body">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-[12px] font-medium text-[#666666] mb-1">
              Category
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full border border-border rounded-lg px-3 py-2 text-[13px] text-text-body focus:outline-none focus:ring-1 focus:ring-brand-primary"
            >
              {DIMENSIONS.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[12px] font-medium text-[#666666] mb-1">
              Learning
            </label>
            <textarea
              value={learning}
              onChange={(e) => setLearning(e.target.value)}
              rows={3}
              placeholder="Concise, actionable instruction..."
              className="w-full border border-border rounded-lg px-3 py-2 text-[13px] text-text-body focus:outline-none focus:ring-1 focus:ring-brand-primary resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-[12px] font-medium text-[#666666] mb-1">
                Dimension (optional)
              </label>
              <select
                value={dimension}
                onChange={(e) => setDimension(e.target.value)}
                className="w-full border border-border rounded-lg px-3 py-2 text-[13px] text-text-body focus:outline-none focus:ring-1 focus:ring-brand-primary"
              >
                <option value="">None</option>
                {DIMENSIONS.filter(d => d !== 'general').map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[12px] font-medium text-[#666666] mb-1">
                Gap Pattern (optional)
              </label>
              <input
                type="text"
                value={gapPattern}
                onChange={(e) => setGapPattern(e.target.value)}
                placeholder="e.g., missing_handoff_template"
                className="w-full border border-border rounded-lg px-3 py-2 text-[13px] text-text-body focus:outline-none focus:ring-1 focus:ring-brand-primary"
              />
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-[13px] text-[#666666] hover:text-text-body"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!learning.trim() || saving}
              className="px-4 py-2 bg-brand-primary text-white text-[13px] font-medium rounded-lg hover:bg-[#35965A] disabled:opacity-50 transition-colors"
            >
              {saving ? 'Saving...' : 'Add Learning'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
