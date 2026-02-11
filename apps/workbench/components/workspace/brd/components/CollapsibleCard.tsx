'use client'

import { useState, type ReactNode } from 'react'
import { ChevronRight, ArrowRight } from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { StaleIndicator } from './StaleIndicator'

interface CollapsibleCardProps {
  title: string
  subtitle?: string
  icon?: ReactNode
  status?: string | null
  isStale?: boolean
  staleReason?: string | null
  onRefresh?: () => void
  defaultExpanded?: boolean
  onConfirm?: () => void
  onNeedsReview?: () => void
  onDetailClick?: () => void
  onStatusClick?: () => void
  children: ReactNode
  actions?: ReactNode
  dragHandle?: ReactNode
}

export function CollapsibleCard({
  title,
  subtitle,
  icon,
  status,
  isStale,
  staleReason,
  onRefresh,
  defaultExpanded = false,
  onConfirm,
  onNeedsReview,
  onDetailClick,
  onStatusClick,
  children,
  actions,
  dragHandle,
}: CollapsibleCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)

  return (
    <div
      className="group/card bg-white rounded-2xl shadow-md border border-[#E5E5E5] overflow-hidden"
    >
      {/* Header */}
      <div
        className="flex items-center gap-3 px-5 py-4 cursor-pointer hover:bg-gray-50/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        {dragHandle}
        <ChevronRight
          className={`w-4 h-4 text-[#999999] flex-shrink-0 transition-transform duration-200 ${
            expanded ? 'rotate-90' : ''
          }`}
        />
        {icon && <span className="flex-shrink-0">{icon}</span>}
        <span className="text-[14px] font-semibold text-[#333333] truncate">{title}</span>
        {subtitle && (
          <span className="text-[12px] text-[#999999] shrink-0">({subtitle})</span>
        )}
        {onDetailClick && (
          <button
            onClick={(e) => { e.stopPropagation(); onDetailClick() }}
            className="p-1 rounded text-[#999999] hover:text-[#3FAF7A] hover:bg-[#E8F5E9] transition-colors opacity-0 group-hover/card:opacity-100 shrink-0"
            title="View details"
          >
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
        {/* Right-aligned status badge */}
        <span className="ml-auto shrink-0" onClick={(e) => e.stopPropagation()}>
          <BRDStatusBadge status={status} onClick={onStatusClick} />
        </span>
        {isStale && (
          <span className="shrink-0">
            <span className="w-2 h-2 rounded-full bg-[#999999] inline-block" title="Stale — may need refresh" />
          </span>
        )}
        {actions && (
          <div className="flex-shrink-0" onClick={(e) => e.stopPropagation()}>
            {actions}
          </div>
        )}
      </div>

      {/* Expandable body */}
      <div
        className={`overflow-hidden transition-all duration-200 ${
          expanded ? 'max-h-[4000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-5 pb-5 pt-1">
          {/* Stale indicator */}
          {isStale && (
            <div className="mb-3">
              <StaleIndicator reason={staleReason} onRefresh={onRefresh} />
            </div>
          )}

          {children}

          {/* Confirm/Review actions */}
          {(onConfirm || onNeedsReview) && (
            <div className="mt-4 pt-3 border-t border-[#E5E5E5]">
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
