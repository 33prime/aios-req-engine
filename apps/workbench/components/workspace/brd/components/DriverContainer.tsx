'use client'

import { useState, type ReactNode } from 'react'
import { ChevronDown, ChevronRight, CheckCircle2 } from 'lucide-react'

interface DriverContainerProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  count: number
  confirmedCount: number
  onConfirmAll?: () => void
  children: ReactNode
}

export function DriverContainer({
  icon: Icon,
  title,
  count,
  confirmedCount,
  onConfirmAll,
  children,
}: DriverContainerProps) {
  const [isOpen, setIsOpen] = useState(true)

  const allConfirmed = count > 0 && confirmedCount === count

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-[0_1px_2px_rgba(0,0,0,0.04)] overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-[#FAFAFA] transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="w-4 h-4 text-[#3FAF7A]" />
          <span className="text-[11px] uppercase tracking-wider text-[#999999] font-semibold">
            {title}
          </span>
          {count > 0 && (
            <span className="px-1.5 py-0.5 bg-[#3FAF7A]/10 text-[#25785A] text-[10px] font-bold rounded-full min-w-[18px] text-center">
              {count}
            </span>
          )}
          {confirmedCount > 0 && !allConfirmed && (
            <span className="flex items-center gap-1 text-[10px] text-[#999999]">
              <CheckCircle2 className="w-3 h-3 text-[#3FAF7A]" />
              {confirmedCount}/{count}
            </span>
          )}
          {allConfirmed && (
            <span className="flex items-center gap-1 text-[10px] text-[#3FAF7A]">
              <CheckCircle2 className="w-3 h-3" />
              All confirmed
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onConfirmAll && !allConfirmed && count > 0 && (
            <span
              onClick={(e) => { e.stopPropagation(); onConfirmAll() }}
              className="text-[11px] text-[#999999] hover:text-[#3FAF7A] transition-colors cursor-pointer"
            >
              Confirm all
            </span>
          )}
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-[#999999]" />
          ) : (
            <ChevronRight className="w-4 h-4 text-[#999999]" />
          )}
        </div>
      </button>

      {isOpen && (
        <div>
          {children}
        </div>
      )}
    </div>
  )
}
