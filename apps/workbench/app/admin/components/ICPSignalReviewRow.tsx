'use client'

import { Check, X } from 'lucide-react'

interface ICPSignalReviewRowProps {
  signal: {
    id: string
    user_id: string
    event_name: string
    event_properties?: any
    confidence_score?: number
    routing_status?: string
  }
  onApprove?: (id: string) => void
  onDismiss?: (id: string) => void
}

export function ICPSignalReviewRow({ signal, onApprove, onDismiss }: ICPSignalReviewRowProps) {
  const confidence = signal.confidence_score ?? 0
  const properties = signal.event_properties || {}

  return (
    <tr className="border-b border-border hover:bg-[#F4F4F4] transition-colors">
      <td className="py-3 px-4 text-[13px] text-[#666666]">
        {signal.user_id.slice(0, 8)}...
      </td>
      <td className="py-3 px-4 text-[13px] text-text-body font-medium">
        {signal.event_name}
      </td>
      <td className="py-3 px-4 text-[12px] text-[#666666] max-w-[200px] truncate">
        {JSON.stringify(properties).slice(0, 60)}...
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 bg-border rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-primary rounded-full"
              style={{ width: `${Math.min(100, confidence * 100)}%` }}
            />
          </div>
          <span className="text-[11px] text-text-placeholder">{(confidence * 100).toFixed(0)}%</span>
        </div>
      </td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-1">
          <button
            onClick={() => onApprove?.(signal.id)}
            className="p-1.5 rounded-lg hover:bg-[#E8F5E9] text-brand-primary transition-colors"
            title="Approve"
          >
            <Check className="w-4 h-4" />
          </button>
          <button
            onClick={() => onDismiss?.(signal.id)}
            className="p-1.5 rounded-lg hover:bg-[#FEE2E2] text-text-placeholder hover:text-red-500 transition-colors"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </td>
    </tr>
  )
}
