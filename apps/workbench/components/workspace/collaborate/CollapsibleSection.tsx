'use client'

import { useState, type ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'

interface CollapsibleSectionProps {
  title: string
  icon: ReactNode
  summary?: string
  defaultOpen?: boolean
  children: ReactNode
}

export function CollapsibleSection({
  title,
  icon,
  summary,
  defaultOpen = true,
  children,
}: CollapsibleSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-page transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-text-placeholder [&>svg]:w-[14px] [&>svg]:h-[14px]">{icon}</span>
          <span className="text-[11px] font-semibold text-text-placeholder uppercase tracking-wider">
            {title}
          </span>
          {summary && !isOpen && (
            <span className="text-[11px] text-text-placeholder font-normal ml-1">
              — {summary}
            </span>
          )}
        </div>
        <ChevronDown
          className={`w-4 h-4 text-text-placeholder transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>
      {isOpen && (
        <div className="px-5 pb-5">
          {children}
        </div>
      )}
    </div>
  )
}
