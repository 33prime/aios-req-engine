'use client'

import { useRouter } from 'next/navigation'
import Image from 'next/image'
import { Circle, CheckCircle2, User } from 'lucide-react'
import type { TaskWithProject } from '@/lib/api'

const PRIORITY_COLORS: Record<string, string> = {
  high: '#25785A',
  medium: '#3FAF7A',
  low: '#E5E5E5',
  none: '#E5E5E5',
}

interface TaskRowProps {
  task: TaskWithProject
  onToggleComplete: (task: TaskWithProject) => void
}

export function TaskRow({ task, onToggleComplete }: TaskRowProps) {
  const router = useRouter()
  const isCompleted = task.status === 'completed' || task.status === 'dismissed'

  const dueText = task.due_date ? formatDue(task.due_date) : null
  const isOverdue = task.due_date && !isCompleted && new Date(task.due_date) < new Date()

  return (
    <div
      className="group flex items-center gap-3 px-3 py-2.5 hover:bg-[#FAFAFA] rounded-lg cursor-pointer transition-colors"
      onClick={() => router.push(`/tasks/${task.id}`)}
    >
      {/* Status circle */}
      <button
        onClick={(e) => { e.stopPropagation(); onToggleComplete(task) }}
        className="flex-shrink-0 text-[#CCC] hover:text-[#3FAF7A] transition-colors"
      >
        {isCompleted ? (
          <CheckCircle2 className="w-[18px] h-[18px] text-[#3FAF7A]" />
        ) : (
          <Circle className="w-[18px] h-[18px]" />
        )}
      </button>

      {/* Priority dot */}
      <div
        className="w-2 h-2 rounded-full flex-shrink-0"
        style={{ backgroundColor: PRIORITY_COLORS[task.priority || 'none'] }}
        title={`${task.priority || 'none'} priority`}
      />

      {/* Title */}
      <span className={`flex-1 text-[13px] truncate ${isCompleted ? 'line-through text-[#999]' : 'text-[#333]'}`}>
        {task.title}
      </span>

      {/* Project badge */}
      <span className="text-[11px] px-1.5 py-0.5 bg-[#F4F4F4] text-[#999] rounded flex-shrink-0 max-w-[120px] truncate">
        {task.project_name}
      </span>

      {/* Due date */}
      {dueText && (
        <span className={`text-[11px] flex-shrink-0 ${isOverdue ? 'text-[#D32F2F] font-medium' : 'text-[#999]'}`}>
          {dueText}
        </span>
      )}

      {/* Assignee avatar */}
      {task.assigned_to && (
        <div className="w-6 h-6 rounded-full bg-[#E8F5E9] flex items-center justify-center overflow-hidden flex-shrink-0" title={task.assigned_to_name || 'Assigned'}>
          {task.assigned_to_photo_url ? (
            <Image src={task.assigned_to_photo_url} alt="" width={24} height={24} className="w-full h-full object-cover" />
          ) : (
            <User className="w-3 h-3 text-[#3FAF7A]" />
          )}
        </div>
      )}
    </div>
  )
}

function formatDue(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const target = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  const diffDays = Math.round((target.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  if (diffDays === -1) return 'Yesterday'
  if (diffDays < 0) return `${Math.abs(diffDays)}d ago`
  if (diffDays <= 7) return `${diffDays}d`
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
