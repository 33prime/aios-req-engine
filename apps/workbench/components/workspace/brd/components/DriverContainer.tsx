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
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-page transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Icon className="w-4 h-4 text-brand-primary" />
          <span className="text-[11px] uppercase tracking-wider text-text-placeholder font-semibold">
            {title}
          </span>
          {count > 0 && (
            <span className="px-1.5 py-0.5 bg-brand-primary-light text-[#25785A] text-[10px] font-bold rounded-full min-w-[18px] text-center">
              {count}
            </span>
          )}
          {confirmedCount > 0 && !allConfirmed && (
            <span className="flex items-center gap-1 text-[10px] text-text-placeholder">
              <CheckCircle2 className="w-3 h-3 text-brand-primary" />
              {confirmedCount}/{count}
            </span>
          )}
          {allConfirmed && (
            <span className="flex items-center gap-1 text-[10px] text-brand-primary">
              <CheckCircle2 className="w-3 h-3" />
              All confirmed
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {onConfirmAll && !allConfirmed && count > 0 && (
            <span
              onClick={(e) => { e.stopPropagation(); onConfirmAll() }}
              className="text-[11px] text-text-placeholder hover:text-brand-primary transition-colors cursor-pointer"
            >
              Confirm all
            </span>
          )}
          {isOpen ? (
            <ChevronDown className="w-4 h-4 text-text-placeholder" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-placeholder" />
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
