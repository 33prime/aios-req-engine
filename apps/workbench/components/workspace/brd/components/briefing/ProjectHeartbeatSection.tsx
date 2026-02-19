'use client'

import { useState } from 'react'
import { ChevronDown, Activity } from 'lucide-react'
import type { ProjectHeartbeat } from '@/types/workspace'

interface ProjectHeartbeatSectionProps {
  heartbeat: ProjectHeartbeat
}

export function ProjectHeartbeatSection({ heartbeat }: ProjectHeartbeatSectionProps) {
  const [expanded, setExpanded] = useState(false) // collapsed by default

  return (
    <div className="border-b border-[#E5E5E5]">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2.5 flex items-center justify-between hover:bg-[#FAFAFA] transition-colors"
      >
        <div className="flex items-center gap-2">
          <Activity className="w-3.5 h-3.5 text-[#666666]" />
          <span className="text-[11px] font-semibold text-[#666666] uppercase tracking-wide">
            Heartbeat
          </span>
          {/* Quick pulse indicator */}
          <span
            className="w-2 h-2 rounded-full"
            style={{
              backgroundColor:
                heartbeat.completeness_pct >= 70
                  ? '#3FAF7A'
                  : heartbeat.completeness_pct >= 40
                  ? '#666666'
                  : '#999999',
            }}
          />
        </div>
        <ChevronDown
          className={`w-3.5 h-3.5 text-[#999999] transition-transform duration-200 ${
            expanded ? 'rotate-180' : ''
          }`}
        />
      </button>

      {expanded && (
        <div className="px-4 pb-3">
          {/* 2x2 grid */}
          <div className="grid grid-cols-2 gap-2">
            <HeartbeatStat
              label="Completeness"
              value={`${Math.round(heartbeat.completeness_pct)}%`}
              progress={heartbeat.completeness_pct}
            />
            <HeartbeatStat
              label="Confirmed"
              value={`${Math.round(heartbeat.confirmation_pct)}%`}
              progress={heartbeat.confirmation_pct}
            />
            <HeartbeatStat
              label="Memory Depth"
              value={String(heartbeat.memory_depth)}
              subtitle="nodes"
            />
            <HeartbeatStat
              label="Last Signal"
              value={
                heartbeat.days_since_last_signal != null
                  ? heartbeat.days_since_last_signal === 0
                    ? 'Today'
                    : `${heartbeat.days_since_last_signal}d ago`
                  : 'Never'
              }
            />
          </div>

          {/* Scope alerts */}
          {heartbeat.scope_alerts.length > 0 && (
            <div className="mt-2 space-y-1">
              {heartbeat.scope_alerts.map((alert) => (
                <div key={alert} className="flex items-center gap-2 py-1 px-2 bg-[#F0F0F0] rounded-lg">
                  <span className="text-[10px] text-[#666666]">
                    {alert === 'scope_creep' && 'Many low-priority features — possible scope creep'}
                    {alert === 'workflow_complexity' && 'High workflow complexity (>15 steps)'}
                    {alert === 'overloaded_persona' && 'A persona owns too many features'}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Stale entities */}
          {heartbeat.stale_entity_count > 0 && (
            <div className="mt-2 py-1 px-2 bg-[#F0F0F0] rounded-lg">
              <span className="text-[10px] text-[#666666]">
                {heartbeat.stale_entity_count} stale entit{heartbeat.stale_entity_count === 1 ? 'y' : 'ies'}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function HeartbeatStat({
  label,
  value,
  subtitle,
  progress,
}: {
  label: string
  value: string
  subtitle?: string
  progress?: number
}) {
  return (
    <div className="p-2.5 bg-[#F4F4F4] rounded-xl">
      <span className="text-[10px] text-[#999999] uppercase tracking-wide">{label}</span>
      <div className="flex items-baseline gap-1 mt-1">
        <span className="text-[16px] font-semibold text-[#333333]">{value}</span>
        {subtitle && <span className="text-[10px] text-[#999999]">{subtitle}</span>}
      </div>
      {progress != null && (
        <div className="mt-1.5 h-1 bg-[#E5E5E5] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${Math.min(100, progress)}%`,
              backgroundColor: progress >= 70 ? '#3FAF7A' : progress >= 40 ? '#666666' : '#999999',
            }}
          />
        </div>
      )}
    </div>
  )
}
