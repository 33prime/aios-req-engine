'use client'

import type { CallRecordingStatus } from '@/types/call-intelligence'
import { STATUS_STYLES, STATUS_LABELS } from './constants'

export function StatusBadge({ status }: { status: CallRecordingStatus }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${STATUS_STYLES[status]}`}>
      {STATUS_LABELS[status]}
    </span>
  )
}
