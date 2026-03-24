'use client'

/**
 * AgentProfileTab — Clean, focused profile for a sub-agent.
 *
 * Shows only what matters at discovery altitude:
 * 1. What it does (role description)
 * 2. Tools & Capabilities (expandable cards)
 * 3. Human partner (single line, not a card)
 *
 * Removed (implementation detail, not discovery):
 * - Data Access list
 * - Autonomy breakdown (Acts alone / Escalates / Won't do)
 * - Pipeline Connections (already visible in workflow chain)
 */

import { useState } from 'react'
import type { IntelLayerAgent } from '@/types/workspace'
import { AgentToolCard } from './AgentToolCard'

interface Props {
  agent: IntelLayerAgent
  agents: IntelLayerAgent[]
}

export function AgentProfileTab({ agent }: Props) {
  const [expandedToolId, setExpandedToolId] = useState<string | null>(null)

  const partnerLabel = agent.partner_role || agent.partner_name || ''

  return (
    <div className="px-5 py-4">
      {/* What this agent does */}
      <div className="mb-5">
        <p className="text-[10px] font-medium uppercase tracking-wide mb-2" style={{ color: '#A0AEC0' }}>
          What {agent.name} does
        </p>
        <p className="text-[12px] leading-relaxed" style={{ color: '#4A5568' }}>
          {agent.role_description}
        </p>

        {/* Human partner — single line */}
        {partnerLabel && (
          <p className="text-[10px] mt-2" style={{ color: '#718096' }}>
            Works with <span className="font-semibold text-[#0A1E2F]">{partnerLabel}</span>
          </p>
        )}
      </div>

      {/* Tools & Capabilities */}
      {agent.tools.length > 0 && (
        <div>
          <p className="text-[10px] font-medium uppercase tracking-wide mb-2" style={{ color: '#A0AEC0' }}>
            Tools & Capabilities
          </p>
          <div className="grid grid-cols-2 gap-2">
            {agent.tools.map((tool) => (
              <AgentToolCard
                key={tool.id}
                tool={tool}
                isExpanded={expandedToolId === tool.id}
                onToggle={() =>
                  setExpandedToolId((prev) => (prev === tool.id ? null : tool.id))
                }
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
