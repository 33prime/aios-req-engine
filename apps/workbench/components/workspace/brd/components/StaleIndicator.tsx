'use client'

import { AlertTriangle, RefreshCw } from 'lucide-react'

interface StaleIndicatorProps {
  reason?: string | null
  onRefresh?: () => void
}

export function StaleIndicator({ reason, onRefresh }: StaleIndicatorProps) {
  return (
    <div className="bg-orange-50 border-l-2 border-orange-300 px-3 py-1.5 rounded-r-sm flex items-center justify-between gap-2">
      <div className="flex items-center gap-1.5 min-w-0">
        <AlertTriangle className="w-3.5 h-3.5 text-orange-500 flex-shrink-0" />
        <span className="text-[12px] text-orange-700 truncate">
          {reason || 'This item may be outdated due to upstream changes'}
        </span>
      </div>
      {onRefresh && (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onRefresh()
          }}
          className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium text-orange-700 bg-orange-100 rounded hover:bg-orange-200 transition-colors flex-shrink-0"
        >
          <RefreshCw className="w-3 h-3" />
          Refresh
        </button>
      )}
    </div>
  )
}
