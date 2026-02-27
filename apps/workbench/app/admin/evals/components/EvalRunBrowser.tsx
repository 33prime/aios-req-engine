'use client'

import { useEffect, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { listEvalRuns } from '@/lib/api'
import type { EvalRunListItem } from '@/types/api'
import { ScoreBreakdownBar, ActionBadge } from './ScoreBreakdownBar'
import { EvalRunDetail } from './EvalRunDetail'

export function EvalRunBrowser() {
  const [runs, setRuns] = useState<EvalRunListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    listEvalRuns()
      .then(setRuns)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-5 h-5 border-2 border-brand-primary border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!runs.length) {
    return (
      <div className="bg-white rounded-2xl shadow-md border border-border p-8 text-center">
        <p className="text-text-placeholder text-[13px]">No eval runs yet. Trigger an eval from a prototype to get started.</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-2xl shadow-md border border-border overflow-hidden">
      {/* Header */}
      <div className="grid grid-cols-[40px_1fr_80px_100px_80px_80px_80px_140px] gap-2 px-4 py-2.5 bg-surface-page border-b border-border text-[11px] font-medium text-text-placeholder uppercase tracking-wide">
        <span />
        <span>Prototype</span>
        <span>Iter</span>
        <span>Overall</span>
        <span>Det</span>
        <span>LLM</span>
        <span>Action</span>
        <span>Date</span>
      </div>

      {/* Rows */}
      {runs.map((run) => (
        <div key={run.id}>
          <button
            onClick={() => setExpandedId(expandedId === run.id ? null : run.id)}
            className="w-full grid grid-cols-[40px_1fr_80px_100px_80px_80px_80px_140px] gap-2 px-4 py-3 hover:bg-[#F4F4F4] transition-colors items-center text-left border-b border-border"
          >
            <span className="text-text-placeholder">
              {expandedId === run.id ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronRight className="w-3.5 h-3.5" />
              )}
            </span>
            <span className="text-[12px] text-text-body font-mono truncate">
              {run.prototype_id.slice(0, 8)}…
            </span>
            <span className="text-[12px] text-[#666666]">#{run.iteration_number}</span>
            <div className="pr-2">
              <ScoreBreakdownBar score={run.overall_score} showValue />
            </div>
            <span className="text-[12px] text-[#666666]">
              {(run.det_composite * 100).toFixed(0)}%
            </span>
            <span className="text-[12px] text-[#666666]">
              {(run.llm_overall * 100).toFixed(0)}%
            </span>
            <ActionBadge action={run.action} />
            <span className="text-[11px] text-text-placeholder">
              {new Date(run.created_at).toLocaleDateString()} {new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </button>

          {expandedId === run.id && (
            <div className="px-4 py-3 border-b border-border">
              <EvalRunDetail runId={run.id} />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
