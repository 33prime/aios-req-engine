'use client'

import Link from 'next/link'
import Image from 'next/image'
import { User } from 'lucide-react'

interface UserCardProps {
  user: {
    user_id: string
    email: string
    first_name?: string | null
    last_name?: string | null
    photo_url?: string | null
    platform_role: string
    enrichment_status?: string | null
    profile_completeness: number
    project_count: number
    signal_count: number
    total_cost_usd: number
    total_tokens: number
  }
}

export function UserCard({ user }: UserCardProps) {
  const displayName = [user.first_name, user.last_name].filter(Boolean).join(' ') || user.email.split('@')[0]
  const completeness = Math.min(100, Math.max(0, user.profile_completeness))

  return (
    <Link
      href={`/admin/users/${user.user_id}`}
      className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5 hover:shadow-lg transition-shadow block"
    >
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#3FAF7A] to-[#25785A] flex items-center justify-center overflow-hidden flex-shrink-0">
          {user.photo_url ? (
            <Image src={user.photo_url} alt={displayName} width={40} height={40} className="w-full h-full object-cover" />
          ) : (
            <User className="w-5 h-5 text-white" />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[14px] font-medium text-[#333333] truncate">{displayName}</p>
          <p className="text-[12px] text-[#999999] truncate">{user.email}</p>
        </div>
        <span className="px-2 py-0.5 text-[11px] rounded-full bg-[#F0F0F0] text-[#666666] flex-shrink-0">
          {user.platform_role}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3 mb-3">
        <div className="text-center">
          <div className="text-[16px] font-semibold text-[#333333]">{user.project_count}</div>
          <div className="text-[11px] text-[#999999]">Projects</div>
        </div>
        <div className="text-center">
          <div className="text-[16px] font-semibold text-[#333333]">{user.signal_count}</div>
          <div className="text-[11px] text-[#999999]">Signals</div>
        </div>
        <div className="text-center">
          <div className="text-[16px] font-semibold text-[#333333]">{completeness}%</div>
          <div className="text-[11px] text-[#999999]">Profile</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
        <div
          className="h-full bg-[#3FAF7A] rounded-full transition-all"
          style={{ width: `${completeness}%` }}
        />
      </div>

      {/* Bottom row */}
      <div className="flex items-center justify-between mt-3">
        <span className={`px-2 py-0.5 text-[11px] rounded-full ${
          user.enrichment_status === 'completed'
            ? 'bg-[#E8F5E9] text-[#25785A]'
            : 'bg-[#F0F0F0] text-[#666666]'
        }`}>
          {user.enrichment_status === 'completed' ? 'Enriched' : 'Pending'}
        </span>
        {user.total_cost_usd > 0 && (
          <span className="text-[11px] text-[#999999]">${user.total_cost_usd.toFixed(2)}</span>
        )}
      </div>
    </Link>
  )
}
