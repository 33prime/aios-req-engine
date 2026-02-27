'use client'

import { useState } from 'react'
import { ChevronRight, FileText } from 'lucide-react'
import { BRDStatusBadge } from './StatusBadge'
import { ConfirmActions } from './ConfirmActions'
import { ImportanceDots } from './ImportanceDots'
import type { BusinessDriver } from '@/types/workspace'

type DriverType = 'pain' | 'goal' | 'kpi'

interface DriverItemRowProps {
  driver: BusinessDriver
  driverType: DriverType
  isExpanded: boolean
  onToggle: () => void
  onDrawerOpen: () => void
  onConfirm: () => void
  onNeedsReview: () => void
  onStatusClick?: () => void
}

function truncateToWords(text: string, maxWords: number): string {
  const words = text.split(/\s+/)
  if (words.length <= maxWords) return text
  return words.slice(0, maxWords).join(' ') + '...'
}

function getDisplayTitle(driver: BusinessDriver): string {
  const raw = driver.title || driver.description || ''
  return truncateToWords(raw, 10)
}

export function DriverItemRow({
  driver,
  driverType,
  isExpanded,
  onToggle,
  onDrawerOpen,
  onConfirm,
  onNeedsReview,
  onStatusClick,
}: DriverItemRowProps) {
  const [hasBeenExpanded, setHasBeenExpanded] = useState(false)

  const evidenceCount = driver.evidence?.length ?? 0
  const displayTitle = getDisplayTitle(driver)

  const handleToggle = () => {
    if (!isExpanded && !hasBeenExpanded) setHasBeenExpanded(true)
    onToggle()
  }

  return (
    <div className={`${driver.is_stale ? 'border-l-2 border-orange-300' : ''}`}>
      {/* Collapsed row */}
      <button
        onClick={handleToggle}
        className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-page transition-colors cursor-pointer border-b border-[#F0F0F0] last:border-b-0 text-left ${
          isExpanded ? 'bg-surface-page' : ''
        }`}
      >
        <ChevronRight
          className={`w-3.5 h-3.5 text-text-placeholder flex-shrink-0 transition-transform duration-200 ${
            isExpanded ? 'rotate-90' : ''
          }`}
        />
        <span className="text-[13px] font-medium text-text-body truncate flex-1 min-w-0">
          {displayTitle}
        </span>
        {evidenceCount > 0 ? (
          <span className="flex items-center gap-1 text-[11px] text-[#25785A] flex-shrink-0">
            <FileText className="w-3 h-3" />
            {evidenceCount} src
          </span>
        ) : (
          <span className="text-[10px] text-text-placeholder/60 flex-shrink-0 italic">No signal evidence</span>
        )}
        <span onClick={(e) => e.stopPropagation()} className="flex-shrink-0">
          <BRDStatusBadge status={driver.confirmation_status} onClick={onStatusClick} />
        </span>
        <ImportanceDots driver={driver} />
      </button>

      {/* Inline expanded view */}
      {hasBeenExpanded && (
        <div
          className={`overflow-hidden transition-all duration-200 ${
            isExpanded ? 'max-h-[400px] opacity-100' : 'max-h-0 opacity-0'
          }`}
        >
          <div className="px-4 pb-3 bg-surface-page border-b border-[#F0F0F0]">
            <div className="pl-6">
              {/* Description */}
              <p className="text-[12px] text-[#666666] leading-relaxed mb-2">
                {driver.description}
              </p>

              {/* Key fields (type-specific) */}
              <KeyFields driver={driver} driverType={driverType} />

              {/* Actions row */}
              <div className="flex items-center justify-between pt-2 mt-2 border-t border-border">
                <ConfirmActions
                  status={driver.confirmation_status}
                  onConfirm={onConfirm}
                  onNeedsReview={onNeedsReview}
                />
                <button
                  onClick={(e) => { e.stopPropagation(); onDrawerOpen() }}
                  className="text-[11px] text-text-placeholder hover:text-brand-primary transition-colors"
                >
                  Open detail →
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function KeyFields({ driver, driverType }: { driver: BusinessDriver; driverType: DriverType }) {
  const parts: { label: string; value: string }[] = []

  if (driverType === 'pain') {
    if (driver.severity) parts.push({ label: 'Severity', value: driver.severity })
    if (driver.business_impact) parts.push({ label: 'Impact', value: driver.business_impact })
  } else if (driverType === 'goal') {
    if (driver.goal_timeframe) parts.push({ label: 'Timeframe', value: driver.goal_timeframe })
    if (driver.owner) parts.push({ label: 'Owner', value: driver.owner })
  } else if (driverType === 'kpi') {
    if (driver.baseline_value && driver.target_value) parts.push({ label: 'Target', value: `${driver.baseline_value} → ${driver.target_value}` })
    else if (driver.target_value) parts.push({ label: 'Target', value: driver.target_value })
    if (driver.measurement_method) parts.push({ label: 'Method', value: driver.measurement_method })
  }

  if (parts.length === 0) return null

  return (
    <div className="text-[11px] text-text-placeholder mb-2">
      {parts.map((p, i) => (
        <span key={p.label}>
          {i > 0 && <span className="mx-1.5">·</span>}
          {p.label}: {p.value}
        </span>
      ))}
    </div>
  )
}
