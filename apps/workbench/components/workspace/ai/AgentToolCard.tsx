'use client'

import type { AgentTool } from '@/types/workspace'

interface Props {
  tool: AgentTool
  isExpanded: boolean
  onToggle: () => void
}

export function AgentToolCard({ tool, isExpanded, onToggle }: Props) {
  return (
    <div
      className={`rounded-lg cursor-pointer transition-all duration-200 ${isExpanded ? 'col-span-2' : ''}`}
      style={{
        background: '#fff',
        border: `1px solid ${isExpanded ? '#3FAF7A' : 'rgba(10,30,47,0.10)'}`,
      }}
      onClick={onToggle}
    >
      {/* Collapsed header — always visible */}
      <div className="flex items-center gap-2 px-3 py-2.5">
        <span className="text-sm flex-shrink-0">{tool.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] font-semibold truncate" style={{ color: '#0A1E2F' }}>
            {tool.name}
          </p>
          {!isExpanded && (
            <p
              className="text-[10px] truncate"
              style={{ color: '#718096' }}
            >
              {tool.description}
            </p>
          )}
        </div>
        <span
          className="flex-shrink-0 text-[10px] transition-transform duration-200"
          style={{ color: '#A0AEC0', transform: isExpanded ? 'rotate(180deg)' : 'none' }}
        >
          &#9662;
        </span>
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="px-3 pb-3 space-y-3" style={{ borderTop: '1px solid rgba(10,30,47,0.06)' }}>
          {/* Description */}
          <p className="text-[11px] leading-relaxed pt-2" style={{ color: '#4A5568' }}>
            {tool.description}
          </p>

          {/* Example narrative */}
          {tool.example && (
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wide mb-1" style={{ color: '#A0AEC0' }}>
                Example
              </p>
              <p
                className="text-[11px] leading-relaxed rounded-lg px-2.5 py-2"
                style={{ color: '#4A5568', background: 'rgba(63,175,122,0.04)' }}
              >
                {tool.example}
              </p>
            </div>
          )}

          {/* Data touches */}
          {tool.data_touches.length > 0 && (
            <div>
              <p className="text-[10px] font-medium uppercase tracking-wide mb-1" style={{ color: '#A0AEC0' }}>
                Data Touches
              </p>
              <div className="flex flex-wrap gap-1">
                {tool.data_touches.map((touch, i) => (
                  <span
                    key={i}
                    className="px-2 py-0.5 rounded text-[10px]"
                    style={{ color: '#044159', background: 'rgba(4,65,89,0.06)' }}
                  >
                    {touch}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Reliability bar */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-medium uppercase tracking-wide" style={{ color: '#A0AEC0' }}>
                Reliability
              </p>
              <span className="text-[10px] font-medium" style={{ color: '#3FAF7A' }}>
                {tool.reliability}%
              </span>
            </div>
            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(0,0,0,0.04)' }}>
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${tool.reliability}%`, background: '#3FAF7A' }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
