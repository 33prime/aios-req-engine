'use client'

import { MessageCircle, FileText, CheckSquare, Users, Clock } from 'lucide-react'
import { useCollaborationCurrent } from '@/lib/hooks/use-api'

interface ClientResponsesCardProps {
  projectId: string
}

export function ClientResponsesCard({ projectId }: ClientResponsesCardProps) {
  const { data: collab } = useCollaborationCurrent(projectId)
  const sync = collab?.portal_sync

  if (!sync?.portal_enabled) return null

  const rows = [
    {
      icon: MessageCircle,
      label: 'Questions',
      completed: sync.questions?.completed ?? 0,
      total: sync.questions?.sent ?? 0,
    },
    {
      icon: FileText,
      label: 'Documents',
      completed: sync.documents?.completed ?? 0,
      total: sync.documents?.sent ?? 0,
    },
    {
      icon: Users,
      label: 'Clients',
      completed: sync.clients_active ?? 0,
      total: sync.clients_invited ?? 0,
      suffix: { completed: 'active', total: 'invited' },
    },
  ]

  const hasAnyActivity = rows.some(r => r.total > 0 || r.completed > 0)
  if (!hasAnyActivity && !sync.last_client_activity) return null

  return (
    <div className="bg-white rounded-2xl border border-border shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-border/50">
        <div className="flex items-center gap-2.5">
          <CheckSquare className="w-4 h-4 text-[#0A1E2F]" />
          <span className="text-[13px] font-semibold text-text-body">Client Responses</span>
        </div>
      </div>

      <div className="px-5 py-3 space-y-2">
        {rows.map(row => {
          const Icon = row.icon
          const completedLabel = row.suffix?.completed ?? 'answered'
          const totalLabel = row.suffix?.total ?? 'sent'

          return (
            <div key={row.label} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Icon className="w-3.5 h-3.5 text-text-placeholder" />
                <span className="text-[12px] text-text-body">{row.label}</span>
              </div>
              <div className="flex items-center gap-2">
                {row.completed > 0 && (
                  <span className="text-[12px] font-medium text-brand-primary">
                    {row.completed} {completedLabel}
                  </span>
                )}
                {row.total > 0 && (
                  <span className="text-[11px] text-text-placeholder">
                    / {row.total} {totalLabel}
                  </span>
                )}
                {row.total === 0 && row.completed === 0 && (
                  <span className="text-[11px] text-text-placeholder">--</span>
                )}
              </div>
            </div>
          )
        })}

        {/* Last activity */}
        {sync.last_client_activity && (
          <div className="flex items-center gap-1.5 pt-1 border-t border-border/50">
            <Clock className="w-3 h-3 text-text-placeholder" />
            <span className="text-[11px] text-text-placeholder">
              Last activity: {formatRelativeTime(sync.last_client_activity)}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHrs = Math.floor(diffMin / 60)
  const diffDays = Math.floor(diffHrs / 24)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHrs < 24) return `${diffHrs}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}
