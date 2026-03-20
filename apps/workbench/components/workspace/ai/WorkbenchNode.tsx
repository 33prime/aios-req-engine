'use client'

/**
 * WorkbenchNode — Agent card for the Intelligence Workbench canvas.
 *
 * Supports both DerivedAgent (legacy) and IntelLayerAgent (DB-backed).
 * DB-backed agents show: tool pills, autonomy bar, validation badge, human partner.
 */

import type { DerivedAgent, IntelLayerAgent, FlowLayoutPosition, FlowCardSize, AgentTechnique } from '@/types/workspace'

type AgentLike = DerivedAgent | IntelLayerAgent

interface Props {
  agent: AgentLike
  position: FlowLayoutPosition
  sizeClass: FlowCardSize
  isSelected: boolean
  isDimmed: boolean
  isConnected: boolean
  onClick: () => void
  onHover: (id: string | null) => void
}

const TECHNIQUE_LABELS: Record<string, { label: string; color: string; bg: string }> = {
  llm: { label: 'LLM', color: '#5B21B6', bg: 'rgba(91,33,182,0.08)' },
  classification: { label: 'Classification', color: '#044159', bg: 'rgba(4,65,89,0.08)' },
  embeddings: { label: 'Embeddings', color: '#1B6B3A', bg: 'rgba(63,175,122,0.08)' },
  rules: { label: 'Rules', color: '#8B6914', bg: 'rgba(212,160,23,0.08)' },
  hybrid: { label: 'Hybrid', color: '#0A1E2F', bg: 'rgba(10,30,47,0.08)' },
}

function isDbAgent(a: AgentLike): a is IntelLayerAgent {
  return 'tools' in a && 'autonomy_level' in a
}

export function WorkbenchNode({
  agent,
  position,
  sizeClass,
  isSelected,
  isDimmed,
  isConnected,
  onClick,
  onHover,
}: Props) {
  const db = isDbAgent(agent)
  const technique = TECHNIQUE_LABELS[(db ? agent.technique : agent.technique) || 'llm']
  const isHero = sizeClass === 'size-hero'
  const isValidated = db && agent.validation_status === 'validated'

  const role = db ? agent.role_description : agent.role
  const name = agent.name
  const icon = agent.icon
  const automationRate = db ? agent.automation_rate : agent.automationRate

  return (
    <div
      className="absolute cursor-pointer transition-all duration-200"
      style={{
        left: position.x,
        top: position.y,
        width: position.w,
        opacity: isDimmed ? 0.25 : 1,
        transform: isSelected ? 'translateY(-2px)' : isConnected ? 'translateY(-1px)' : 'none',
        zIndex: isSelected ? 10 : isConnected ? 5 : 1,
      }}
      onClick={onClick}
      onMouseEnter={() => onHover(agent.id)}
      onMouseLeave={() => onHover(null)}
    >
      <div
        className="rounded-xl p-4 h-full transition-all duration-200"
        style={{
          background: '#fff',
          borderLeft: isValidated ? '3px solid #3FAF7A' : undefined,
          border: `1.5px solid ${
            isSelected ? '#3FAF7A'
            : isConnected ? 'rgba(63,175,122,0.4)'
            : 'rgba(10,30,47,0.10)'
          }`,
          boxShadow: isSelected
            ? '0 4px 20px rgba(63,175,122,0.15)'
            : isConnected ? '0 2px 12px rgba(0,0,0,0.06)'
            : '0 1px 4px rgba(0,0,0,0.04)',
        }}
      >
        {/* Header: Icon + Name + Validation/Technique */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-lg flex-shrink-0">{icon}</span>
            <p
              className="text-[12px] font-semibold text-[#0A1E2F] truncate"
              style={{ maxWidth: position.w - 90 }}
            >
              {name}
            </p>
          </div>
          <div className="flex items-center gap-1.5 flex-shrink-0">
            {isValidated && (
              <div className="w-4 h-4 rounded-full flex items-center justify-center text-[8px] text-white" style={{ background: '#3FAF7A' }}>
                &#x2713;
              </div>
            )}
            <span
              className="px-1.5 py-0.5 rounded text-[9px] font-medium"
              style={{ color: technique.color, background: technique.bg }}
            >
              {technique.label}
            </span>
          </div>
        </div>

        {/* Role description */}
        <p
          className="text-[11px] text-[#4A5568] leading-snug mb-2"
          style={{
            display: '-webkit-box',
            WebkitLineClamp: isHero ? 3 : 2,
            WebkitBoxOrient: 'vertical',
            overflow: 'hidden',
          }}
        >
          {role}
        </p>

        {/* Tool pills (DB agents only) */}
        {db && agent.tools.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-2">
            {agent.tools.slice(0, 3).map((t) => (
              <span
                key={t.id}
                className="text-[8px] px-1.5 py-0.5 rounded"
                style={{ background: 'rgba(0,0,0,0.03)', color: '#718096', border: '1px solid rgba(10,30,47,0.06)' }}
              >
                {t.icon} {t.name}
              </span>
            ))}
            {agent.tools.length > 3 && (
              <span className="text-[8px] px-1.5 py-0.5 rounded" style={{ color: '#A0AEC0' }}>
                +{agent.tools.length - 3}
              </span>
            )}
          </div>
        )}

        {/* I/O columns (derived agents) */}
        {!db && (
          <div className="flex gap-3 mb-2">
            <div className="flex-1 min-w-0">
              <p className="text-[9px] font-medium text-[#D4A017] uppercase tracking-wide mb-0.5">In</p>
              <div className="space-y-0.5">
                {agent.dataNeeds.slice(0, isHero ? 3 : 2).map((d, i) => (
                  <p key={i} className="text-[10px] text-[#718096] truncate">{d.source}</p>
                ))}
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[9px] font-medium text-[#3FAF7A] uppercase tracking-wide mb-0.5">Out</p>
              <div className="space-y-0.5">
                {agent.produces.slice(0, isHero ? 3 : 2).map((p, i) => (
                  <p key={i} className="text-[10px] text-[#718096] truncate">{p}</p>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Autonomy bar (DB agents) */}
        {db && (
          <div className="mb-2">
            <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(0,0,0,0.04)' }}>
              <div className="h-full rounded-full" style={{ width: `${agent.autonomy_level}%`, background: '#3FAF7A' }} />
            </div>
            <div className="flex justify-between mt-0.5">
              <span className="text-[8px] text-[#A0AEC0]">Autonomy</span>
              <span className="text-[8px] text-[#A0AEC0]">{agent.autonomy_level}%</span>
            </div>
          </div>
        )}

        {/* Confidence bar (derived agents) */}
        {!db && agent.confidenceTiers && (
          <div className="mb-2">
            <div className="flex h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(0,0,0,0.04)' }}>
              {agent.confidenceTiers.high > 0 && <div className="h-full" style={{ width: `${agent.confidenceTiers.high}%`, background: '#3FAF7A' }} />}
              {agent.confidenceTiers.medium > 0 && <div className="h-full" style={{ width: `${agent.confidenceTiers.medium}%`, background: '#D4A017' }} />}
              {agent.confidenceTiers.low > 0 && <div className="h-full" style={{ width: `${agent.confidenceTiers.low}%`, background: 'rgba(10,30,47,0.15)' }} />}
            </div>
          </div>
        )}

        {/* Footer: Partner + Maturity */}
        <div className="flex items-center justify-between">
          {db && agent.partner_role ? (
            <div className="flex items-center gap-1.5">
              {agent.partner_initials && (
                <div
                  className="w-4 h-4 rounded-full flex items-center justify-center text-[6px] font-bold text-white"
                  style={{ background: agent.partner_color || '#044159' }}
                >
                  {agent.partner_initials}
                </div>
              )}
              <span className="text-[8px] text-[#718096]">{agent.partner_role}</span>
            </div>
          ) : (
            <span className="text-[9px] text-[#718096]">{automationRate}% auto</span>
          )}
          <span
            className="px-1.5 py-0.5 rounded text-[9px] font-medium"
            style={{
              color: agent.maturity === 'expert' ? '#1B6B3A' : agent.maturity === 'reliable' ? '#044159' : '#8B6914',
              background: agent.maturity === 'expert' ? 'rgba(63,175,122,0.10)' : agent.maturity === 'reliable' ? 'rgba(4,65,89,0.08)' : 'rgba(212,160,23,0.10)',
            }}
          >
            {agent.maturity}
          </span>
        </div>
      </div>
    </div>
  )
}
