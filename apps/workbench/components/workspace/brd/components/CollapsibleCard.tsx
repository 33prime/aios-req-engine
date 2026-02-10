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
  children: ReactNode
  actions?: ReactNode
  dragHandle?: ReactNode
}

function getCardBg(status: string | null | undefined, isStale?: boolean): string {
  if (isStale) {
    return 'bg-orange-50/30 border-orange-200'
  }
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
  isStale,
  staleReason,
  onRefresh,
  defaultExpanded = false,
  onConfirm,
  onNeedsReview,
  onDetailClick,
  children,
  actions,
  dragHandle,
}: CollapsibleCardProps) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const bgClass = getCardBg(status, isStale)

  return (
    <div
      className={`group/card border rounded-[3px] shadow-[0_1px_3px_rgba(0,0,0,0.05)] transition-all duration-150 ${bgClass}`}
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
            {isStale && (
              <span className="w-2 h-2 rounded-full bg-orange-400 flex-shrink-0" title="Stale — may need refresh" />
            )}
            <BRDStatusBadge status={status} />
            {onDetailClick && (
              <button
                onClick={(e) => { e.stopPropagation(); onDetailClick() }}
                className="p-1 rounded text-gray-300 hover:text-[#009b87] hover:bg-teal-50 transition-colors opacity-0 group-hover/card:opacity-100"
                title="View details"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            )}
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
          {/* Stale indicator */}
          {isStale && (
            <div className="mb-3">
              <StaleIndicator reason={staleReason} onRefresh={onRefresh} />
            </div>
          )}

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
