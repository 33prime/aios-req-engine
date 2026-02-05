'use client'

import { useState, type ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'

interface CollapsibleCardProps {
  title: string
  subtitle?: string
  icon?: ReactNode
  status?: string | null
  defaultExpanded?: boolean
  onConfirm?: () => void
  onNeedsReview?: () => void
  children: ReactNode
  actions?: ReactNode
  dragHandle?: ReactNode
}

function getCardBg(status: string | null | undefined): string {
  if (status === 'confirmed_consultant' || status === 'confirmed_client') {
    return 'bg-teal-50/40 border-teal-100'
  }
  if (status === 'needs_client' || status === 'needs_confirmation') {
    return 'bg-yellow-50/40 border-yellow-100'
  }
  return 'bg-white border-[#e9e9e7]'
}

export function CollapsibleCard({
  title,
  subtitle,
  icon,
  status,
  defaultExpanded = false,
  onConfirm,
  onNeedsReview,
  children,
  actions,
  dragHandle,
}: CollapsibleCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const bgClass = getCardBg(status)

  return (
    <div
      className={`border rounded-[3px] shadow-[0_1px_3px_rgba(0,0,0,0.05)] transition-all duration-150 ${bgClass}`}
    >
      {/* Header */}
      <div
        className="flex items-center gap-2 px-4 py-3 cursor-pointer hover:bg-[rgba(55,53,47,0.03)] transition-colors rounded-[3px]"
        onClick={() => setExpanded(!expanded)}
      >
        {dragHandle}
        <ChevronRight
          className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform duration-150 ${
            expanded ? 'rotate-90' : ''
          }`}
        />
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-medium text-[#37352f] truncate">{title}</span>
            <BRDStatusBadge status={status} />
          </div>
          {subtitle && (
            <p className="text-[13px] text-[rgba(55,53,47,0.65)] mt-0.5 truncate">
              {subtitle}
            </p>
          )}
        </div>
        {actions && (
          <div className="flex-shrink-0 ml-2" onClick={(e) => e.stopPropagation()}>
            {actions}
          </div>
        )}
      </div>

      {/* Expandable body */}
      <div
        className={`overflow-hidden transition-all duration-200 ${
          expanded ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-4 pb-4 pt-1">
          {children}

          {/* Confirm/Review actions */}
          {(onConfirm || onNeedsReview) && (
            <div className="mt-3 pt-3 border-t border-gray-100">
              <ConfirmActions
                status={status}
                onConfirm={onConfirm || (() => {})}
                onNeedsReview={onNeedsReview || (() => {})}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
