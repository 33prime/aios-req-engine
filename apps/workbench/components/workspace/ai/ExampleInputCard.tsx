'use client'

import type { AgentExampleResponse } from '@/types/workspace'

interface Props {
  example: AgentExampleResponse
  agentName: string
  onRun: () => void
  onSwitchToCustom: () => void
  isRunning: boolean
}

export function ExampleInputCard({ example, agentName, onRun, onSwitchToCustom, isRunning }: Props) {
  const excerpt = example.example_input.slice(0, 200) + (example.example_input.length > 200 ? '...' : '')

  return (
    <div className="rounded-lg overflow-hidden" style={{ border: '1px solid rgba(10,30,47,0.10)' }}>
      {/* Header */}
      <div className="px-3 py-2" style={{ background: 'rgba(0,0,0,0.02)', borderBottom: '1px solid rgba(10,30,47,0.06)' }}>
        <div className="text-[8px] font-semibold uppercase tracking-wide mb-0.5" style={{ color: '#A0AEC0' }}>
          Sample Input
        </div>
        {(example.source_label || example.input_type) && (
          <div className="text-[10px]" style={{ color: '#718096' }}>
            {example.source_label}{example.source_label && example.input_type ? ' \u00B7 ' : ''}{example.input_type}
          </div>
        )}
      </div>

      {/* Excerpt */}
      <div className="px-3 py-2.5">
        <div
          className="text-[11px] leading-relaxed p-2.5 rounded-[6px]"
          style={{ background: 'rgba(63,175,122,0.03)', borderLeft: '3px solid rgba(63,175,122,0.3)', color: '#2D3748' }}
        >
          {excerpt}
        </div>
      </div>

      {/* Key signals */}
      {example.key_signals && example.key_signals.length > 0 && (
        <div className="px-3 pb-2.5 flex flex-wrap gap-1">
          {example.key_signals.map((signal, i) => (
            <span
              key={i}
              className="px-1.5 py-0.5 rounded text-[9px]"
              style={{ background: 'rgba(63,175,122,0.08)', color: '#2A8F5F' }}
            >
              {signal}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="px-3 pb-3 space-y-2">
        <button
          onClick={onRun}
          disabled={isRunning}
          className="w-full rounded-lg py-2 text-[11px] font-semibold text-white transition-all"
          style={{
            background: isRunning ? '#A0AEC0' : '#3FAF7A',
            cursor: isRunning ? 'not-allowed' : 'pointer',
          }}
        >
          {isRunning ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Running...
            </span>
          ) : (
            `Run ${agentName} \u2192`
          )}
        </button>
        <button
          onClick={onSwitchToCustom}
          className="w-full text-center text-[10px] font-medium py-1"
          style={{ color: '#718096' }}
        >
          Use custom input instead
        </button>
      </div>
    </div>
  )
}
