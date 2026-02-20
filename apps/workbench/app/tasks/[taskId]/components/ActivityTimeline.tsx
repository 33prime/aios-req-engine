'use client'

import Image from 'next/image'
import { User, MessageSquare, Play, CheckCircle2, XCircle, RotateCcw, Pencil, Flag, UserPlus, Calendar } from 'lucide-react'
import type { TaskComment, TaskActivity } from '@/lib/api'

type TimelineItem =
  | { type: 'comment'; data: TaskComment; date: string }
  | { type: 'activity'; data: TaskActivity; date: string }

interface ActivityTimelineProps {
  comments: TaskComment[]
  activities: TaskActivity[]
  onDeleteComment?: (commentId: string) => void
  currentUserId?: string
}

const ACTION_CONFIG: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  created: { icon: <Play className="w-3 h-3" />, label: 'created this task', color: '#3FAF7A' },
  started: { icon: <Play className="w-3 h-3" />, label: 'started working', color: '#3FAF7A' },
  completed: { icon: <CheckCircle2 className="w-3 h-3" />, label: 'completed this task', color: '#3FAF7A' },
  dismissed: { icon: <XCircle className="w-3 h-3" />, label: 'dismissed this task', color: '#999' },
  reopened: { icon: <RotateCcw className="w-3 h-3" />, label: 'reopened this task', color: '#F59E0B' },
  updated: { icon: <Pencil className="w-3 h-3" />, label: 'updated this task', color: '#666' },
  priority_changed: { icon: <Flag className="w-3 h-3" />, label: 'changed priority', color: '#25785A' },
  assigned: { icon: <UserPlus className="w-3 h-3" />, label: 'assigned this task', color: '#3FAF7A' },
  commented: { icon: <MessageSquare className="w-3 h-3" />, label: 'commented', color: '#3FAF7A' },
  due_date_changed: { icon: <Calendar className="w-3 h-3" />, label: 'changed due date', color: '#666' },
}

export function ActivityTimeline({ comments, activities, onDeleteComment, currentUserId }: ActivityTimelineProps) {
  // Merge and sort chronologically
  const items: TimelineItem[] = [
    ...comments.map((c) => ({ type: 'comment' as const, data: c, date: c.created_at })),
    // Filter out 'commented' activities since we show the actual comment
    ...activities
      .filter((a) => a.action !== 'commented')
      .map((a) => ({ type: 'activity' as const, data: a, date: a.created_at })),
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

  if (items.length === 0) {
    return (
      <div className="py-6 text-center text-[12px] text-[#CCC]">
        No activity yet
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {items.map((item, i) => {
        if (item.type === 'comment') {
          const c = item.data as TaskComment
          return (
            <div key={`c-${c.id}`} className="flex items-start gap-3 py-3 group">
              <div className="w-7 h-7 rounded-full bg-[#E8F5E9] flex items-center justify-center overflow-hidden flex-shrink-0">
                {c.author_photo_url ? (
                  <Image src={c.author_photo_url} alt="" width={28} height={28} className="w-full h-full object-cover" />
                ) : (
                  <User className="w-3.5 h-3.5 text-[#3FAF7A]" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[13px] font-medium text-[#333]">{c.author_name || 'User'}</span>
                  <span className="text-[11px] text-[#CCC]">{formatTime(c.created_at)}</span>
                  {currentUserId === c.author_id && onDeleteComment && (
                    <button
                      onClick={() => onDeleteComment(c.id)}
                      className="text-[11px] text-[#CCC] hover:text-[#D32F2F] opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      Delete
                    </button>
                  )}
                </div>
                <p className="text-[13px] text-[#333] whitespace-pre-wrap">{c.body}</p>
              </div>
            </div>
          )
        }

        // Activity
        const a = item.data as TaskActivity
        const config = ACTION_CONFIG[a.action] || ACTION_CONFIG.updated
        return (
          <div key={`a-${a.id}`} className="flex items-center gap-3 py-2">
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: `${config.color}15`, color: config.color }}
            >
              {config.icon}
            </div>
            <span className="text-[12px] text-[#999]">
              {config.label}
            </span>
            <span className="text-[11px] text-[#CCC]">{formatTime(a.created_at)}</span>
          </div>
        )
      })}
    </div>
  )
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays < 7) return `${diffDays}d ago`
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
