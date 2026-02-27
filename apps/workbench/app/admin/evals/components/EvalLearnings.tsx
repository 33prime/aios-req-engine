'use client'

import { useEffect, useState } from 'react'
import { Plus, ToggleLeft, ToggleRight } from 'lucide-react'
import { listEvalLearnings, toggleEvalLearning } from '@/lib/api'
import type { EvalLearning } from '@/types/api'
import { AddLearningModal } from './AddLearningModal'

export function EvalLearnings() {
  const [learnings, setLearnings] = useState<EvalLearning[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [dimensionFilter, setDimensionFilter] = useState('')

  const loadLearnings = () => {
    setLoading(true)
    listEvalLearnings({ dimension: dimensionFilter || undefined })
      .then(setLearnings)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadLearnings()
  }, [dimensionFilter])

  const handleToggle = async (id: string, currentActive: boolean) => {
    try {
      await toggleEvalLearning(id, !currentActive)
      setLearnings((prev) =>
        prev.map((l) => (l.id === id ? { ...l, active: !currentActive } : l))
      )
    } catch (err) {
      console.error('Failed to toggle learning:', err)
    }
  }

  const dimensions = [...new Set(learnings.map((l) => l.dimension).filter(Boolean))]

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <select
            value={dimensionFilter}
            onChange={(e) => setDimensionFilter(e.target.value)}
            className="border border-border rounded-lg px-3 py-1.5 text-[13px] text-text-body focus:outline-none focus:ring-1 focus:ring-brand-primary"
          >
            <option value="">All dimensions</option>
            {dimensions.map((d) => (
              <option key={d} value={d!}>{d}</option>
            ))}
          </select>
          <span className="text-[12px] text-text-placeholder">
            {learnings.length} learnings ({learnings.filter((l) => l.active).length} active)
          </span>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-primary text-white text-[13px] font-medium rounded-lg hover:bg-[#35965A] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Learning
        </button>
      </div>

      {/* Loading */}
      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="w-5 h-5 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : !learnings.length ? (
        <div className="bg-white rounded-2xl shadow-md border border-border p-8 text-center">
          <p className="text-text-placeholder text-[13px]">No learnings yet. They&apos;re extracted automatically from successful eval runs.</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-md border border-border overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-[48px_100px_1fr_100px_80px_120px] gap-2 px-4 py-2.5 bg-surface-page border-b border-border text-[11px] font-medium text-text-placeholder uppercase tracking-wide">
            <span>Active</span>
            <span>Category</span>
            <span>Learning</span>
            <span>Dimension</span>
            <span>Score</span>
            <span>Date</span>
          </div>

          {/* Rows */}
          {learnings.map((l) => (
            <div
              key={l.id}
              className={`grid grid-cols-[48px_100px_1fr_100px_80px_120px] gap-2 px-4 py-3 border-b border-border items-center ${
                !l.active ? 'opacity-50' : ''
              }`}
            >
              <button
                onClick={() => handleToggle(l.id, l.active)}
                className="text-left"
              >
                {l.active ? (
                  <ToggleRight className="w-5 h-5 text-brand-primary" />
                ) : (
                  <ToggleLeft className="w-5 h-5 text-text-placeholder" />
                )}
              </button>
              <span className="text-[12px] text-[#666666]">{l.category}</span>
              <span className="text-[12px] text-text-body">{l.learning}</span>
              <span className="text-[11px] text-text-placeholder">{l.dimension || '—'}</span>
              <span className="text-[12px] text-[#666666]">
                {l.effectiveness_score.toFixed(2)}
              </span>
              <span className="text-[11px] text-text-placeholder">
                {new Date(l.created_at).toLocaleDateString()}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <AddLearningModal
          onClose={() => setShowModal(false)}
          onCreated={loadLearnings}
        />
      )}
    </div>
  )
}
