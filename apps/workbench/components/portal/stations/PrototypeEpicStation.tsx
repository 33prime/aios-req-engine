'use client'

import { useState } from 'react'
import { Check, X, AlertTriangle } from 'lucide-react'
import type { ClientEpic, VerdictType } from '@/types/portal'

interface PrototypeEpicStationProps {
  epic: ClientEpic
  onAssumptionResponse: (assumptionIndex: number, response: 'agree' | 'disagree') => void
  assumptionResponses: Record<number, 'agree' | 'disagree'>
  onVerdict?: (verdict: VerdictType, notes?: string) => void
  currentVerdict?: VerdictType | null
}

export function PrototypeEpicStation({
  epic,
  onAssumptionResponse,
  assumptionResponses,
  onVerdict,
  currentVerdict,
}: PrototypeEpicStationProps) {
  const [notes, setNotes] = useState('')

  return (
    <div className="space-y-4">
      {/* Epic narrative */}
      <div>
        <h3 className="text-sm font-semibold text-text-primary">{epic.title}</h3>
        {epic.narrative && (
          <p className="text-xs text-text-muted mt-1 leading-relaxed">{epic.narrative}</p>
        )}
      </div>

      {/* Consultant note */}
      {epic.consultant_note && (
        <div className="bg-blue-50 rounded-lg px-3 py-2 border border-blue-100">
          <p className="text-[10px] uppercase tracking-wide text-blue-500 font-medium mb-0.5">
            From your consultant
          </p>
          <p className="text-xs text-blue-800">{epic.consultant_note}</p>
        </div>
      )}

      {/* Feature pills */}
      {epic.features.length > 0 && (
        <div className="flex flex-wrap gap-1">
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
          <p className="text-[10px] uppercase tracking-wide text-text-placeholder font-medium">
            Assumptions
          </p>
          {epic.assumptions.map((a, i) => {
            const response = assumptionResponses[i]
            return (
              <div key={i} className="flex items-start gap-2">
                <p className="text-xs text-text-secondary flex-1 pt-0.5">{a.text}</p>
                <div className="flex gap-1 flex-shrink-0">
                  <button
                    onClick={() => onAssumptionResponse(i, 'agree')}
                    className={`p-1 rounded transition-colors ${
                      response === 'agree'
                        ? 'bg-green-100 text-green-700'
                        : 'text-text-placeholder hover:bg-green-50 hover:text-green-600'
                    }`}
                  >
                    <Check className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => onAssumptionResponse(i, 'disagree')}
                    className={`p-1 rounded transition-colors ${
                      response === 'disagree'
                        ? 'bg-red-100 text-red-700'
                        : 'text-text-placeholder hover:bg-red-50 hover:text-red-600'
                    }`}
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Verdict buttons */}
      {onVerdict && (
        <div className="space-y-2 pt-2 border-t border-border">
          <div className="flex gap-2">
            {(['confirmed', 'refine', 'flag'] as VerdictType[]).map((v) => {
              const isActive = currentVerdict === v
              const styles: Record<VerdictType, string> = {
                confirmed: isActive ? 'border-green-400 bg-green-50 text-green-800' : 'border-border hover:border-green-400 hover:bg-green-50',
                refine: isActive ? 'border-amber-400 bg-amber-50 text-amber-800' : 'border-border hover:border-amber-400 hover:bg-amber-50',
                flag: isActive ? 'border-red-400 bg-red-50 text-red-800' : 'border-border hover:border-red-400 hover:bg-red-50',
              }
              const icons: Record<VerdictType, React.ReactNode> = {
                confirmed: <Check className="w-3 h-3" />,
                refine: <AlertTriangle className="w-3 h-3" />,
                flag: <X className="w-3 h-3" />,
              }
              const labels: Record<VerdictType, string> = {
                confirmed: 'Confirm',
                refine: 'Refine',
                flag: 'Flag',
              }
              return (
                <button
                  key={v}
                  onClick={() => onVerdict(v, notes || undefined)}
                  className={`flex-1 flex items-center justify-center gap-1 px-3 py-2 rounded-lg border text-xs font-medium transition-all ${styles[v]}`}
                >
                  {icons[v]}
                  {labels[v]}
                </button>
              )
            })}
          </div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Notes (optional)..."
            rows={2}
            className="w-full text-xs px-3 py-2 border border-border rounded-lg focus:ring-2 focus:ring-brand-primary-ring focus:border-brand-primary resize-none"
          />
        </div>
      )}
    </div>
  )
}
