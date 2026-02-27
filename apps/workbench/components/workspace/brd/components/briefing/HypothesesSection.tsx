'use client'

import { useState } from 'react'
import { ChevronDown, FlaskConical } from 'lucide-react'
import type { Hypothesis } from '@/types/workspace'
import {
  HYPOTHESIS_STATUS_LABELS,
  HYPOTHESIS_STATUS_COLORS,
} from '@/lib/action-constants'

interface HypothesesSectionProps {
  hypotheses: Hypothesis[]
  projectId: string
}

export function HypothesesSection({ hypotheses, projectId }: HypothesesSectionProps) {
  const [expanded, setExpanded] = useState(true)

  // Only show proposed + testing
  const active = hypotheses.filter(h => h.status === 'proposed' || h.status === 'testing')
  if (active.length === 0) return null

  return (
    <div className="border-b border-border">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2.5 flex items-center justify-between hover:bg-surface-page transition-colors"
      >
        <div className="flex items-center gap-2">
          <FlaskConical className="w-3.5 h-3.5 text-[#666666]" />
          <span className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide">
            Hypotheses
          </span>
          <span className="text-[10px] font-medium text-[#666666] bg-[#F0F0F0] px-1.5 py-0.5 rounded-full">
            {active.length}
          </span>
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 text-text-placeholder transition-transform duration-200 ${
            expanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {active.map((hyp) => (
            <HypothesisCard key={hyp.hypothesis_id} hypothesis={hyp} />
          ))}
        </div>
      )}
    </div>
  )
}

function HypothesisCard({ hypothesis }: { hypothesis: Hypothesis }) {
  const statusColor = HYPOTHESIS_STATUS_COLORS[hypothesis.status] || '#666666'
  const statusLabel = HYPOTHESIS_STATUS_LABELS[hypothesis.status] || hypothesis.status
  const confidencePct = Math.round(hypothesis.confidence * 100)

  return (
    <div className="border border-border rounded-xl p-3 bg-white">
      {/* Status + domain */}
      <div className="flex items-center gap-2 mb-1.5">
        <span
          className="text-[10px] font-medium px-1.5 py-0.5 rounded-full"
          style={{
            backgroundColor: statusColor + '15',
            color: statusColor,
          }}
        >
          {statusLabel}
        </span>
        {hypothesis.domain && (
          <span className="text-[10px] text-text-placeholder">{hypothesis.domain}</span>
        )}
      </div>

      {/* Statement */}
      <p className="text-[12px] text-text-body leading-relaxed mb-2">
        {hypothesis.statement}
      </p>

      {/* Confidence bar */}
      <div className="flex items-center gap-2 mb-2">
        <div className="flex-1 h-1.5 bg-border rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${confidencePct}%`,
              backgroundColor: confidencePct >= 70 ? '#3FAF7A' : confidencePct >= 50 ? '#666666' : '#999999',
            }}
          />
        </div>
        <span className="text-[10px] font-medium text-[#666666]">{confidencePct}%</span>
      </div>

      {/* Evidence counts */}
      <div className="flex items-center gap-3">
        <span className="text-[10px] text-brand-primary">
          {hypothesis.evidence_for} supporting
        </span>
        <span className="text-[10px] text-text-placeholder">
          {hypothesis.evidence_against} contradicting
        </span>
      </div>

      {/* Test suggestion */}
      {hypothesis.test_suggestion && (
        <div className="mt-2 p-2 bg-[#F4F4F4] rounded-lg">
          <p className="text-[11px] text-[#666666]">
            <span className="font-medium">Test:</span> {hypothesis.test_suggestion}
          </p>
        </div>
      )}
    </div>
  )
}
