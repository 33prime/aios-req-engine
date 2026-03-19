'use client'

/**
 * TryItPanel — Interactive agent execution panel for the Intelligence Workbench.
 *
 * Input textarea + "Load example" + "Run [Agent]" button.
 * Calls executeAgent() API → loading state → renders output via AgentOutputRenderer.
 */

import { useState, useCallback } from 'react'
import type { DerivedAgent, AgentExecuteResponse } from '@/types/workspace'
import { executeAgent, getAgentExample } from '@/lib/api/workspace'
import { AgentOutputRenderer } from './AgentOutputRenderer'

interface Props {
  agent: DerivedAgent
  projectId: string
}

export function TryItPanel({ agent, projectId }: Props) {
  const [inputText, setInputText] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [isLoadingExample, setIsLoadingExample] = useState(false)
  const [result, setResult] = useState<AgentExecuteResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleLoadExample = useCallback(async () => {
    setIsLoadingExample(true)
    try {
      const example = await getAgentExample(projectId, agent.type)
      setInputText(example.example_input)
      setResult(null)
      setError(null)
    } catch {
      setError('Failed to load example')
    } finally {
      setIsLoadingExample(false)
    }
  }, [projectId, agent.type])

  const handleRun = useCallback(async () => {
    if (!inputText.trim()) return
    setIsRunning(true)
    setError(null)
    setResult(null)

    try {
      const response = await executeAgent(projectId, {
        agent_type: agent.type,
        agent_name: agent.name,
        input_text: inputText.trim(),
        step_id: agent.sourceStepId,
      })
      setResult(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Execution failed')
    } finally {
      setIsRunning(false)
    }
  }, [projectId, agent, inputText])

  return (
    <div className="flex flex-col h-full">
      {/* Input area */}
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between">
          <p className="text-[11px] font-medium text-[#0A1E2F]">Input</p>
          <button
            onClick={handleLoadExample}
            disabled={isLoadingExample}
            className="text-[11px] font-medium transition-colors"
            style={{ color: '#3FAF7A' }}
          >
            {isLoadingExample ? 'Loading...' : 'Load example'}
          </button>
        </div>

        <textarea
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          placeholder="Paste a meeting transcript, email, or any text..."
          className="w-full rounded-lg p-3 text-[12px] text-[#2D3748] leading-relaxed resize-none focus:outline-none focus:ring-1 focus:ring-[#3FAF7A]"
          style={{
            background: 'rgba(0,0,0,0.02)',
            border: '1px solid rgba(10,30,47,0.10)',
            minHeight: 120,
            maxHeight: 200,
          }}
        />

        <button
          onClick={handleRun}
          disabled={isRunning || !inputText.trim()}
          className="w-full rounded-lg py-2.5 text-[12px] font-semibold text-white transition-all duration-200"
          style={{
            background: isRunning || !inputText.trim() ? '#A0AEC0' : '#3FAF7A',
            cursor: isRunning || !inputText.trim() ? 'not-allowed' : 'pointer',
          }}
        >
          {isRunning ? (
            <span className="flex items-center justify-center gap-2">
              <span className="inline-block w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Running {agent.name}...
            </span>
          ) : (
            `Run ${agent.name}`
          )}
        </button>
      </div>

      {/* Output area */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {error && (
          <div
            className="rounded-lg p-3 text-[12px]"
            style={{ background: 'rgba(220,80,80,0.06)', color: '#9B2C2C' }}
          >
            {error}
          </div>
        )}

        {result && (
          <div>
            <p className="text-[10px] font-medium text-[#A0AEC0] uppercase tracking-wide mb-2">
              Output
            </p>
            <AgentOutputRenderer
              agentType={result.agent_type}
              output={result.output}
              executionTimeMs={result.execution_time_ms}
            />
          </div>
        )}

        {!result && !error && !isRunning && (
          <div className="flex items-center justify-center h-24 text-[12px] text-[#A0AEC0]">
            Paste input and click Run to see {agent.name} in action
          </div>
        )}
      </div>
    </div>
  )
}
