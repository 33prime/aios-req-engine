'use client'

import { useState } from 'react'
import type { IntelLayerAgent } from '@/types/workspace'
import { validateAgent } from '@/lib/api/intel-layer'

interface Props {
  agent: IntelLayerAgent
  executionId: string | null
  projectId: string
  onValidated: () => void
  onAdjust: () => void
}

export function AgentValidationBar({ agent, executionId, projectId, onValidated, onAdjust }: Props) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [validated, setValidated] = useState(false)

  const handleConfirm = async () => {
    if (!executionId || isSubmitting) return
    setIsSubmitting(true)
    try {
      await validateAgent(projectId, agent.id, executionId, 'confirmed')
      setValidated(true)
      onValidated()
    } catch {
      // Validation failed — allow retry
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleAdjust = () => {
    onAdjust()
  }

  if (validated) {
    return (
      <div className="space-y-2">
        <div
          className="flex items-center justify-center gap-2 rounded-lg py-2.5"
          style={{ background: 'rgba(63,175,122,0.08)' }}
        >
          <span className="text-[12px] font-semibold" style={{ color: '#1B6B3A' }}>
            Validated &#x2713;
          </span>
        </div>

        {/* Cascade alert (shown even after validation) */}
        {agent.cascade_effects.length > 0 && (
          <CascadeAlert effects={agent.cascade_effects} />
        )}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      {/* Action buttons */}
      <div className="flex gap-2">
        <button
          onClick={handleConfirm}
          disabled={!executionId || isSubmitting}
          className="flex-1 rounded-lg py-2 text-[11px] font-semibold text-white transition-colors"
          style={{
            background: !executionId || isSubmitting ? '#A0AEC0' : '#3FAF7A',
            cursor: !executionId || isSubmitting ? 'not-allowed' : 'pointer',
          }}
        >
          {isSubmitting ? 'Validating...' : 'This is exactly right'}
        </button>
        <button
          onClick={handleAdjust}
          disabled={!executionId || isSubmitting}
          className="flex-1 rounded-lg py-2 text-[11px] font-semibold transition-colors"
          style={{
            border: '1px solid rgba(10,30,47,0.15)',
            background: 'transparent',
            color: '#4A5568',
            cursor: !executionId || isSubmitting ? 'not-allowed' : 'pointer',
          }}
        >
          I&apos;d adjust this
        </button>
      </div>

      {/* Cascade alert */}
      {agent.cascade_effects.length > 0 && (
        <CascadeAlert effects={agent.cascade_effects} />
      )}
    </div>
  )
}

function CascadeAlert({ effects }: { effects: IntelLayerAgent['cascade_effects'] }) {
  return (
    <div
      className="rounded-lg p-3"
      style={{ background: 'rgba(10,30,47,0.02)', border: '1px solid rgba(10,30,47,0.08)' }}
    >
      <p className="text-[10px] font-medium uppercase tracking-wide mb-1.5" style={{ color: '#A0AEC0' }}>
        This affects other agents
      </p>
      <div className="space-y-1">
        {effects.map((effect, i) => (
          <div key={i} className="flex items-start gap-2">
            <span className="text-[10px] flex-shrink-0 mt-0.5" style={{ color: '#3FAF7A' }}>
              &#8594;
            </span>
            <p className="text-[10px] leading-snug" style={{ color: '#4A5568' }}>
              <span className="font-medium" style={{ color: '#0A1E2F' }}>{effect.target_agent_name}</span>
              {': '}{effect.effect_description}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
