'use client'

import { Target } from 'lucide-react'

interface ICPProfileCardProps {
  profile: {
    id: string
    name: string
    description?: string | null
    is_active: boolean
    signal_patterns?: any
    scoring_criteria?: any
  }
  onToggleActive?: (id: string, active: boolean) => void
}

export function ICPProfileCard({ profile, onToggleActive }: ICPProfileCardProps) {
  const patternCount = Array.isArray(profile.signal_patterns) ? profile.signal_patterns.length : 0

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-xl bg-[#3FAF7A]/10">
            <Target className="w-4 h-4 text-[#3FAF7A]" />
          </div>
          <div>
            <h3 className="text-[14px] font-medium text-[#333333]">{profile.name}</h3>
            {profile.description && (
              <p className="text-[12px] text-[#666666] mt-0.5 line-clamp-2">{profile.description}</p>
            )}
          </div>
        </div>
        <button
          onClick={() => onToggleActive?.(profile.id, !profile.is_active)}
          className={`px-2.5 py-1 text-[11px] rounded-full transition-colors ${
            profile.is_active
              ? 'bg-[#E8F5E9] text-[#25785A]'
              : 'bg-[#F0F0F0] text-[#666666]'
          }`}
        >
          {profile.is_active ? 'Active' : 'Inactive'}
        </button>
      </div>

      <div className="flex items-center gap-4 text-[12px] text-[#999999]">
        <span>{patternCount} signal patterns</span>
      </div>
    </div>
  )
}
