'use client'

import { ThumbsUp, ThumbsDown, Lightbulb } from 'lucide-react'
import type { ClientEpic, EpicAssumption } from '@/types/portal'

interface EpicExplorationCardProps {
  epic: ClientEpic
  responses: Record<number, 'agree' | 'disagree'>
  onAssumptionResponse: (assumptionIndex: number, response: 'agree' | 'disagree') => void
  onNewIdea: () => void
}

export function EpicExplorationCard({
  epic,
  responses,
  onAssumptionResponse,
  onNewIdea,
}: EpicExplorationCardProps) {
  return (
    <div className="space-y-3">
      {/* Epic header */}
      <div>
        <h2 className="text-lg font-semibold text-accent">{epic.title}</h2>
        <p className="text-sm text-text-secondary mt-1 leading-relaxed">{epic.narrative}</p>
      </div>

      {/* Consultant note */}
      {epic.consultant_note && (
        <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3">
          <p className="text-xs text-blue-500 font-medium uppercase tracking-wide mb-0.5">From your consultant</p>
          <p className="text-sm text-blue-900">{epic.consultant_note}</p>
        </div>
      )}

      {/* Features */}
      {epic.features.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {epic.features.map((f, i) => (
            <span
              key={i}
              className="text-[10px] bg-surface-subtle text-text-muted px-2 py-0.5 rounded-full"
            >
              {f.name}
            </span>
          ))}
        </div>
      )}

      {/* Assumptions */}
      {epic.assumptions.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-text-placeholder uppercase tracking-wide">
            We assumed that...
          </p>
          {epic.assumptions.map((assumption: EpicAssumption, i: number) => {
            const resp = responses[i]
            return (
              <div
                key={i}
                className={`rounded-xl border px-4 py-3 transition-all ${
                  resp === 'agree'
                    ? 'border-brand-primary/30 bg-brand-primary/5'
                    : resp === 'disagree'
                    ? 'border-amber-300/30 bg-amber-50'
                    : 'border-border bg-surface-card'
                }`}
              >
                <p className="text-sm text-text-body mb-2">{assumption.text}</p>
                <div className="flex gap-2">
                  <button
                    onClick={() => onAssumptionResponse(i, 'agree')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      resp === 'agree'
                        ? 'bg-brand-primary text-white'
                        : 'bg-surface-subtle text-text-muted hover:bg-brand-primary/10 hover:text-brand-primary'
                    }`}
                  >
                    <ThumbsUp className="w-3.5 h-3.5" />
                    Yes, exactly
                  </button>
                  <button
                    onClick={() => onAssumptionResponse(i, 'disagree')}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      resp === 'disagree'
                        ? 'bg-amber-500 text-white'
                        : 'bg-surface-subtle text-text-muted hover:bg-amber-50 hover:text-amber-600'
                    }`}
                  >
                    <ThumbsDown className="w-3.5 h-3.5" />
                    Not quite
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* New idea button */}
      <button
        onClick={onNewIdea}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-dashed border-border-strong rounded-xl text-sm text-text-muted hover:border-brand-primary hover:text-brand-primary transition-all"
      >
        <Lightbulb className="w-4 h-4" />
        Something came to mind?
      </button>
    </div>
  )
}
