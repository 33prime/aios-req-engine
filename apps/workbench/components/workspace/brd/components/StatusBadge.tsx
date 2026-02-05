'use client'

interface BRDStatusBadgeProps {
  status: string | null | undefined
  className?: string
}

const STATUS_CONFIG: Record<string, { label: string; bg: string; text: string }> = {
  ai_generated: { label: 'AI Draft', bg: '#f3f4f6', text: '#6b7280' },
  confirmed_consultant: { label: 'Confirmed', bg: '#f0fdfa', text: '#0f766e' },
  confirmed_client: { label: 'Client Confirmed', bg: '#ecfdf5', text: '#047857' },
  needs_client: { label: 'Needs Review', bg: '#fefce8', text: '#a16207' },
  needs_confirmation: { label: 'Needs Review', bg: '#fefce8', text: '#a16207' },
}

const DEFAULT_CONFIG = { label: 'Draft', bg: '#f3f4f6', text: '#6b7280' }

export function BRDStatusBadge({ status, className = '' }: BRDStatusBadgeProps) {
  const config = STATUS_CONFIG[status || ''] || DEFAULT_CONFIG

  return (
    <span
      className={`inline-flex items-center rounded-xl px-2.5 py-1 text-[11px] font-medium leading-none ${className}`}
      style={{ backgroundColor: config.bg, color: config.text }}
    >
      {config.label}
    </span>
  )
}
