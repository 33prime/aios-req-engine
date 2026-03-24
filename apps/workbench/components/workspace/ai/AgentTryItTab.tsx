'use client'

import { useState, useCallback } from 'react'
import type { IntelLayerAgent, AgentExecutionResult, SampleOutputRow } from '@/types/workspace'
import { executeAgent } from '@/lib/api/intel-layer'
import { ProcessingAnimation } from './ProcessingAnimation'
import { AgentValidationBar } from './AgentValidationBar'

interface Props {
  agent: IntelLayerAgent
  projectId: string
  onValidated: () => void
}

function OutputRow({ row }: { row: SampleOutputRow }) {
  return (
    <div className="py-2.5" style={{ borderBottom: '1px solid rgba(10,30,47,0.04)' }}>
      <div className="flex items-center gap-2 mb-1">
        <p className="text-[10px] font-medium" style={{ color: '#A0AEC0' }}>
          {row.key}
        </p>
        {row.badge && (
          <span
            className="px-1.5 py-0 rounded text-[8px] font-medium"
            style={{ color: '#4A5568', background: 'rgba(10,30,47,0.06)' }}
          >
            {row.badge}
          </span>
        )}
      </div>
      {row.val && (
        <p className="text-[11px] leading-relaxed" style={{ color: '#2D3748' }}>
          {row.val}
        </p>
      )}
      {row.list && row.list.length > 0 && (
        <ul className="space-y-0.5">
          {row.list.map((item, i) => (
            <li key={i} className="text-[11px] leading-relaxed flex items-start gap-1.5" style={{ color: '#4A5568' }}>
              <span className="w-1 h-1 rounded-full mt-1.5 flex-shrink-0" style={{ background: '#3FAF7A' }} />
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function AgentTryItTab({ agent, projectId, onValidated }: Props) {
  const [inputText, setInputText] = useState(agent.sample_input || '')
  const [isRunning, setIsRunning] = useState(false)
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null)
  const [result, setResult] = useState<AgentExecutionResult | null>(null)

  const handleRun = useCallback(async () => {
    if (!inputText.trim() || isRunning) return
    setIsRunning(true)
    setRunStartedAt(Date.now())
    setResult(null)

    try {
      const data = await executeAgent(projectId, agent.id, inputText.trim())
      setResult(data)
    } catch {
      // stay on input state
    } finally {
      setIsRunning(false)
      setRunStartedAt(null)
    }
  }, [projectId, agent.id, inputText, isRunning])

  return (
    <div className="px-5 py-4 overflow-y-auto h-full">
      {/* Sample input */}
      <div className="mb-3">
        <p className="text-[10px] font-medium uppercase tracking-wide mb-1.5" style={{ color: '#A0AEC0' }}>
          Sample scenario
        </p>
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Describe a scenario to test..."
          className="w-full rounded-lg p-2.5 text-[11px] leading-relaxed resize-none focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
          style={{
            color: '#2D3748',
            background: 'rgba(0,0,0,0.02)',
            border: '1px solid rgba(10,30,47,0.10)',
            minHeight: 120,
            maxHeight: 200,
          }}
          disabled={isRunning}
        />
      </div>

      {/* Run button */}
      {!isRunning && !result && (
        <button
          onClick={handleRun}
          disabled={!inputText.trim()}
          className="rounded-md px-4 py-1.5 text-[10px] font-semibold text-white transition-all mb-3"
          style={{
            background: !inputText.trim() ? '#A0AEC0' : '#3FAF7A',
            cursor: !inputText.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          Run {agent.name}
        </button>
      )}

      {/* Processing animation */}
      {isRunning && (
        <ProcessingAnimation
          agentType={agent.agent_type}
          agentName={agent.name}
          isRunning={isRunning}
          startedAt={runStartedAt}
          steps={agent.processing_steps}
        />
      )}

      {/* Output card */}
      {result && !isRunning && (
        <div className="mb-3">
          <div
            className="rounded-lg overflow-hidden"
            style={{ border: '1px solid rgba(63,175,122,0.12)' }}
          >
            {/* Output header */}
            <div className="flex items-center gap-2 px-3 py-1.5" style={{ background: 'rgba(63,175,122,0.04)', borderBottom: '1px solid rgba(63,175,122,0.08)' }}>
              <span className="text-[9px] font-medium" style={{ color: '#3FAF7A' }}>&#x2713; Output</span>
              <span className="text-[9px] ml-auto" style={{ color: '#A0AEC0' }}>
                {(result.execution_time_ms / 1000).toFixed(1)}s
              </span>
            </div>
            {/* Output rows */}
            <div className="px-3">
              {result.output.map((row, i) => (
                <OutputRow key={i} row={row} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Validation bar */}
      {result && !isRunning && (
        <AgentValidationBar
          agent={agent}
          executionId={result.execution_id}
          projectId={projectId}
          onValidated={onValidated}
          onAdjust={() => setResult(null)}
        />
      )}
    </div>
  )
}
