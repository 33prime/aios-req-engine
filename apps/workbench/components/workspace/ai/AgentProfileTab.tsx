'use client'

import { useState } from 'react'
import type { IntelLayerAgent } from '@/types/workspace'
import { AgentToolCard } from './AgentToolCard'

interface Props {
  agent: IntelLayerAgent
  agents: IntelLayerAgent[]
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <p className="text-[10px] font-medium uppercase tracking-wide mb-2" style={{ color: '#A0AEC0' }}>
        {title}
      </p>
      {children}
    </div>
  )
}

/** Show first N items with a subtle "show more" toggle */
function LimitedPills({
  items,
  limit = 3,
}: {
  items: string[]
  limit?: number
}) {
  const [expanded, setExpanded] = useState(false)
  const visible = expanded ? items : items.slice(0, limit)
  const hasMore = items.length > limit

  return (
    <div className="flex flex-wrap gap-1">
      {visible.map((item, i) => (
        <span
          key={i}
          className="px-2 py-0.5 rounded text-[10px]"
          style={{ color: '#4A5568', background: 'rgba(10,30,47,0.04)' }}
        >
          {item}
        </span>
      ))}
      {hasMore && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="px-2 py-0.5 rounded text-[10px] font-medium transition-colors"
          style={{ color: '#3FAF7A' }}
        >
          {expanded ? 'Show less' : `+${items.length - limit} more`}
        </button>
      )}
    </div>
  )
}

export function AgentProfileTab({ agent, agents }: Props) {
  const [expandedToolId, setExpandedToolId] = useState<string | null>(null)

  const upstreamAgents = agents.filter((a) => agent.depends_on_agent_ids.includes(a.id))
  const downstreamAgents = agents.filter((a) => agent.feeds_agent_ids.includes(a.id))

  // Partner display — use role as primary, name as secondary
  const hasPartner = agent.partner_role || agent.partner_name
  const partnerLabel = agent.partner_role || agent.partner_name || ''
  const partnerInitials = agent.partner_initials
    || (partnerLabel ? partnerLabel.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase() : '??')

  return (
    <div className="px-5 py-4 space-y-0">
      {/* What this agent does */}
      <Section title={`What ${agent.name} does`}>
        <p className="text-[12px] leading-relaxed" style={{ color: '#4A5568' }}>
          {agent.role_description}
        </p>
      </Section>

      {/* Tools & Capabilities */}
      {agent.tools.length > 0 && (
        <Section title="Tools & Capabilities">
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
        </Section>
      )}

      {/* Data Access */}
      {agent.data_sources.length > 0 && (
        <Section title="Data access">
          <div className="space-y-1">
            {agent.data_sources.map((ds, i) => (
              <div key={i} className="flex items-center justify-between py-0.5">
                <div className="flex items-center gap-2">
                  <div
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ background: '#3FAF7A' }}
                  />
                  <span className="text-[11px]" style={{ color: '#4A5568' }}>
                    {ds.name}
                  </span>
                </div>
                <span className="text-[9px] font-medium" style={{ color: '#A0AEC0' }}>
                  {ds.access}
                </span>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* Autonomy Level */}
      <Section title={`Autonomy — ${agent.autonomy_level}%`}>
        <div className="mb-3">
          <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(10,30,47,0.06)' }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{ width: `${agent.autonomy_level}%`, background: '#3FAF7A' }}
            />
          </div>
        </div>

        {agent.can_do.length > 0 && (
          <div className="mb-3">
            <p className="text-[9px] font-medium mb-1.5" style={{ color: '#718096' }}>
              Acts alone on
            </p>
            <LimitedPills items={agent.can_do} limit={3} />
          </div>
        )}

        {agent.needs_approval.length > 0 && (
          <div className="mb-3">
            <p className="text-[9px] font-medium mb-1.5" style={{ color: '#718096' }}>
              Escalates for
            </p>
            <LimitedPills items={agent.needs_approval} limit={3} />
          </div>
        )}

        {agent.cannot_do.length > 0 && (
          <div>
            <p className="text-[9px] font-medium mb-1.5" style={{ color: '#718096' }}>
              Won{"'"}t do
            </p>
            <LimitedPills items={agent.cannot_do} limit={3} />
          </div>
        )}
      </Section>

      {/* Human Partner — always show if partner_role exists */}
      {hasPartner && (
        <Section title="Human partner">
          <div
            className="rounded-lg p-3 flex items-start gap-3"
            style={{ background: 'rgba(4,65,89,0.03)', border: '1px solid rgba(10,30,47,0.06)' }}
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-semibold text-white flex-shrink-0 mt-0.5"
              style={{ background: agent.partner_color || '#044159' }}
            >
              {partnerInitials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[12px] font-semibold" style={{ color: '#0A1E2F' }}>
                {partnerLabel}
              </p>
              {agent.partner_relationship && (
                <p className="text-[11px] leading-relaxed mt-1" style={{ color: '#4A5568' }}>
                  {agent.partner_relationship}
                </p>
              )}
              {agent.partner_escalations && (
                <p className="text-[10px] leading-relaxed mt-1.5 pt-1.5" style={{ color: '#718096', borderTop: '1px solid rgba(10,30,47,0.06)' }}>
                  <span className="font-medium" style={{ color: '#0A1E2F' }}>Escalates when: </span>
                  {agent.partner_escalations}
                </p>
              )}
            </div>
          </div>
        </Section>
      )}

      {/* Pipeline Connections */}
      {(upstreamAgents.length > 0 || downstreamAgents.length > 0) && (
        <Section title="Pipeline connections">
          <div className="space-y-1.5">
            {upstreamAgents.map((a) => (
              <div key={a.id} className="flex items-center gap-2 text-[10px]" style={{ color: '#4A5568' }}>
                <span className="font-medium" style={{ color: '#A0AEC0' }}>← from</span>
                <span>{a.icon} {a.name}</span>
              </div>
            ))}
            {downstreamAgents.map((a) => (
              <div key={a.id} className="flex items-center gap-2 text-[10px]" style={{ color: '#4A5568' }}>
                <span className="font-medium" style={{ color: '#3FAF7A' }}>feeds →</span>
                <span>{a.icon} {a.name}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  )
}
