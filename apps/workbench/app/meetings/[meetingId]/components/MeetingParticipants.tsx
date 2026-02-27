'use client'

import { Plus } from 'lucide-react'
import type { StakeholderDetail, StakeholderType } from '@/types/workspace'

const AVATAR_COLORS = ['#044159', '#25785A', '#3FAF7A', '#88BABF', '#0A1E2F']

const ROLE_BADGE_CONFIG: Record<string, { bg: string; text: string }> = {
  champion: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  sponsor: { bg: 'bg-[#E8F5E9]', text: 'text-[#25785A]' },
  blocker: { bg: 'bg-[#0A1E2F]', text: 'text-white' },
  influencer: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  end_user: { bg: 'bg-[#F0F0F0]', text: 'text-[#666]' },
  consultant: { bg: 'bg-[#E0EFF3]', text: 'text-accent' },
}

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

function getRoleBadge(type?: StakeholderType | null) {
  if (!type) return null
  const config = ROLE_BADGE_CONFIG[type] || ROLE_BADGE_CONFIG.end_user
  const label = type.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-[1px] rounded ${config.bg} ${config.text}`}>
      {label}
    </span>
  )
}

interface MeetingParticipantsProps {
  participants: StakeholderDetail[]
  onAddParticipant: () => void
}

export function MeetingParticipants({ participants, onAddParticipant }: MeetingParticipantsProps) {
  return (
    <div className="mt-7">
      <div className="flex items-center justify-between mb-3.5">
        <div className="text-[15px] font-semibold text-text-primary flex items-center gap-2">
          Participants
          <span className="text-[12px] font-medium text-text-muted bg-[#F0F0F0] px-[7px] py-[1px] rounded-lg">
            {participants.length}
          </span>
        </div>
        <button
          onClick={onAddParticipant}
          className="w-7 h-7 rounded-md border border-dashed border-[#D0D0D0] flex items-center justify-center text-text-muted hover:border-accent hover:text-accent hover:bg-[#f0f7fa] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex gap-2.5 flex-wrap">
        {participants.map((p, i) => (
          <div
            key={p.id}
            className="flex items-center gap-2.5 px-3.5 py-2 bg-white border border-border rounded-lg min-w-[180px] hover:border-[#D0D0D0] hover:shadow-[0_2px_4px_rgba(0,0,0,0.04)] transition-all"
          >
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-bold text-white flex-shrink-0"
              style={{
                background: `linear-gradient(135deg, ${AVATAR_COLORS[i % AVATAR_COLORS.length]}, ${AVATAR_COLORS[(i + 2) % AVATAR_COLORS.length]})`,
              }}
            >
              {getInitials(p.name)}
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold text-text-primary truncate">
                {p.name}
              </div>
              <div className="flex items-center gap-1 text-[11px] text-text-muted">
                {getRoleBadge(p.stakeholder_type)}
                {p.organization && <span className="truncate">{p.organization}</span>}
              </div>
            </div>
          </div>
        ))}

        {participants.length === 0 && (
          <div className="text-[13px] text-text-muted py-2">
            No participants added yet
          </div>
        )}
      </div>
    </div>
  )
}
