'use client'

import { useState } from 'react'
import { Activity, ChevronDown, ChevronRight } from 'lucide-react'
import { useClientActivity } from '@/lib/hooks/use-api'

interface ClientActivitySectionProps {
  projectId: string
}

export function ClientActivitySection({ projectId }: ClientActivitySectionProps) {
  const [isOpen, setIsOpen] = useState(true)
  const { data, isLoading } = useClientActivity(projectId)

  const items = data?.items ?? []

  const dotColor = (type: string) => {
    switch (type) {
      case 'answer': return 'bg-[#3FAF7A]'
      case 'upload': return 'bg-[#0A1E2F]'
      case 'package_sent': return 'bg-[#0A1E2F]'
      case 'prototype_view': return 'bg-[#25785A]'
      case 'confirmation': return 'bg-[#25785A]'
      default: return 'bg-[#E5E5E5]'
    }
  }

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-[0_1px_2px_rgba(0,0,0,0.04)] overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-[#FAFAFA] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Activity className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[11px] uppercase tracking-wider text-[#999999] font-semibold">
            Client Activity
          </span>
          {items.length > 0 && (
            <span className="px-1.5 py-0.5 bg-[#3FAF7A]/10 text-[#25785A] text-[10px] font-bold rounded-full min-w-[18px] text-center">
              {items.length}
            </span>
          )}
        </div>
        {isOpen ? <ChevronDown className="w-4 h-4 text-[#999999]" /> : <ChevronRight className="w-4 h-4 text-[#999999]" />}
      </button>

      {isOpen && (
        <div className="px-5 pb-4">
          {isLoading ? (
            <div className="flex justify-center py-4">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-[#3FAF7A] border-t-transparent" />
            </div>
          ) : items.length === 0 ? (
            <div className="text-center py-4">
              <Activity className="w-8 h-8 mx-auto mb-2 text-[#E5E5E5]" />
              <p className="text-[12px] text-[#999999]">No client activity yet</p>
              <p className="text-[11px] text-[#CCCCCC] mt-1">
                Activity will appear as clients interact with the portal
              </p>
            </div>
          ) : (
            <div className="relative border-l-2 border-[#E5E5E5] ml-3 pl-4 space-y-4">
              {items.map(item => (
                <div key={item.id} className="relative">
                  {/* Timeline dot */}
                  <span className={`w-2.5 h-2.5 rounded-full absolute -left-[21px] top-0.5 ${dotColor(item.type)}`} />
                  <div>
                    <p className="text-sm text-[#333333]">
                      <span className="font-medium">{item.actor_name}</span>{' '}
                      {item.description}
                    </p>
                    <p className="text-[11px] text-[#999999] mt-0.5">
                      {formatRelativeTime(item.timestamp)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHrs = Math.floor(diffMin / 60)
  const diffDays = Math.floor(diffHrs / 24)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHrs < 24) return `${diffHrs}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}
