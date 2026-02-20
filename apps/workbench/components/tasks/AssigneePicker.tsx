'use client'

import { useState, useRef, useEffect } from 'react'
import Image from 'next/image'
import { User, X, ChevronDown } from 'lucide-react'
import type { OrganizationMemberPublic } from '@/types/api'

interface AssigneePickerProps {
  members: OrganizationMemberPublic[]
  selectedUserId?: string
  onChange: (userId: string | undefined) => void
  compact?: boolean
}

export function AssigneePicker({ members, selectedUserId, onChange, compact }: AssigneePickerProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const selected = members.find((m) => m.user_id === selectedUserId)

  const displayName = (m: OrganizationMemberPublic) =>
    [m.first_name, m.last_name].filter(Boolean).join(' ') || m.email

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className={`
          flex items-center gap-1.5 rounded-md border border-[#E5E5E5] bg-white
          hover:border-[#3FAF7A] transition-colors text-[13px]
          ${compact ? 'px-2 py-1' : 'px-3 py-1.5'}
        `}
      >
        {selected ? (
          <>
            <div className="w-5 h-5 rounded-full bg-[#E8F5E9] flex items-center justify-center overflow-hidden flex-shrink-0">
              {selected.photo_url ? (
                <Image src={selected.photo_url} alt="" width={20} height={20} className="w-full h-full object-cover" />
              ) : (
                <User className="w-3 h-3 text-[#3FAF7A]" />
              )}
            </div>
            <span className="text-[#333] truncate max-w-[120px]">{displayName(selected)}</span>
            <button
              onClick={(e) => { e.stopPropagation(); onChange(undefined); setOpen(false) }}
              className="text-[#999] hover:text-[#333] ml-0.5"
            >
              <X className="w-3 h-3" />
            </button>
          </>
        ) : (
          <>
            <User className="w-3.5 h-3.5 text-[#999]" />
            <span className="text-[#999]">Assignee</span>
            <ChevronDown className="w-3 h-3 text-[#999]" />
          </>
        )}
      </button>

      {open && (
        <div className="absolute z-50 top-full mt-1 left-0 w-56 bg-white border border-[#E5E5E5] rounded-lg shadow-lg py-1 max-h-60 overflow-y-auto">
          {members.map((m) => (
            <button
              key={m.user_id}
              onClick={() => { onChange(m.user_id); setOpen(false) }}
              className={`
                w-full flex items-center gap-2 px-3 py-2 text-left text-[13px] hover:bg-[#F4F4F4] transition-colors
                ${m.user_id === selectedUserId ? 'bg-[#E8F5E9]' : ''}
              `}
            >
              <div className="w-6 h-6 rounded-full bg-[#E8F5E9] flex items-center justify-center overflow-hidden flex-shrink-0">
                {m.photo_url ? (
                  <Image src={m.photo_url} alt="" width={24} height={24} className="w-full h-full object-cover" />
                ) : (
                  <User className="w-3 h-3 text-[#3FAF7A]" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[#333] truncate">{displayName(m)}</div>
                {m.first_name && <div className="text-[11px] text-[#999] truncate">{m.email}</div>}
              </div>
            </button>
          ))}
          {members.length === 0 && (
            <div className="px-3 py-4 text-[12px] text-[#999] text-center">No team members found</div>
          )}
        </div>
      )}
    </div>
  )
}
