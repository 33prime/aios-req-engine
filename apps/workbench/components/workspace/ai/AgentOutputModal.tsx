'use client'

import type { DerivedAgent, AgentExecuteResponse } from '@/types/workspace'
import { AgentOutputRenderer } from './AgentOutputRenderer'
import { HumanValueCallout } from './HumanValueCallout'

interface Props {
  agent: DerivedAgent
  result: AgentExecuteResponse
  isOpen: boolean
  onClose: () => void
}

export function AgentOutputModal({ agent, result, isOpen, onClose }: Props) {
  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-[300]"
        style={{ background: 'rgba(10,30,47,0.4)' }}
        onClick={onClose}
      />

      {/* Centered card */}
      <div className="fixed inset-0 z-[301] flex items-center justify-center p-6 pointer-events-none">
        <div
          className="bg-white rounded-xl w-full flex flex-col overflow-hidden pointer-events-auto"
          style={{
            maxWidth: 800,
            maxHeight: '92vh',
            boxShadow: '0 20px 60px rgba(10,30,47,0.25)',
            animation: 'agentOutputIn 0.3s ease',
          }}
        >
          {/* Browser chrome header */}
          <div
            className="flex items-center px-4 py-2.5 flex-shrink-0 gap-2"
            style={{ background: 'linear-gradient(180deg, #FAFAFA 0%, #F0F0F0 100%)', borderBottom: '1px solid #E2E8F0' }}
          >
            <div className="flex gap-1">
              <div className="w-2 h-2 rounded-full" style={{ background: '#FF5F57' }} />
              <div className="w-2 h-2 rounded-full" style={{ background: '#FEBC2E' }} />
              <div className="w-2 h-2 rounded-full" style={{ background: '#28C840' }} />
            </div>
            <div className="flex-1 text-center text-[10px] font-medium" style={{ color: '#718096' }}>
              {agent.icon} {agent.name} Output &middot; {result.execution_time_ms}ms
            </div>
            <button
              onClick={onClose}
              className="w-[22px] h-[22px] rounded-full flex items-center justify-center transition-colors"
              style={{ border: '1px solid #E2E8F0', background: '#fff', color: '#718096' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#EDF2F7'; e.currentTarget.style.color = '#0A1E2F' }}
              onMouseLeave={e => { e.currentTarget.style.background = '#fff'; e.currentTarget.style.color = '#718096' }}
            >
              &#x2715;
            </button>
          </div>

          {/* Human value callout */}
          <HumanValueCallout
            statement={agent.humanValueStatement || null}
            agentType={agent.type}
            agentName={agent.name}
            automationRate={agent.automationRate}
            humanPartner={agent.humanPartners?.[0]}
          />

          {/* Divider */}
          <div style={{ height: 1, background: '#E2E8F0' }} />

          {/* Output content */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            <AgentOutputRenderer
              agentType={result.agent_type}
              output={result.output}
              executionTimeMs={result.execution_time_ms}
              hideFooter
            />
          </div>

          {/* Footer bar */}
          <div
            className="flex items-center justify-between px-5 py-2 flex-shrink-0"
            style={{ borderTop: '1px solid #E2E8F0', background: '#FAFAFA' }}
          >
            <span className="text-[10px]" style={{ color: '#A0AEC0' }}>
              Processed in {result.execution_time_ms}ms
            </span>
            <span className="text-[10px]" style={{ color: '#A0AEC0' }}>
              Readytogo Agents
            </span>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes agentOutputIn {
          from { opacity: 0; transform: scale(0.96) translateY(10px); }
          to { opacity: 1; transform: scale(1) translateY(0); }
        }
      `}</style>
    </>
  )
}
