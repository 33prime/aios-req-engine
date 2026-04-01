'use client'

import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { Calendar, User, Bell, Eye, Send, Package, Pen, FileText } from 'lucide-react'
import Image from 'next/image'
import type { TaskWithProject } from '@/lib/api'

const TYPE_CONFIG: Record<string, { icon: typeof FileText; label: string; bg: string; text: string }> = {
  signal_review: { icon: FileText, label: 'Signal Review', bg: 'bg-brand-primary-light', text: 'text-brand-primary' },
  action_item: { icon: Send, label: 'Action Item', bg: 'bg-[#0A1E2F]/10', text: 'text-[#0A1E2F]' },
  meeting_prep: { icon: Calendar, label: 'Meeting Prep', bg: 'bg-brand-primary-light', text: 'text-[#25785A]' },
  book_meeting: { icon: Calendar, label: 'Book Meeting', bg: 'bg-brand-primary-light', text: 'text-[#25785A]' },
  reminder: { icon: Bell, label: 'Reminder', bg: 'bg-gray-100', text: 'text-[#666]' },
  review_request: { icon: Eye, label: 'Review', bg: 'bg-brand-primary-light', text: 'text-brand-primary' },
  deliverable: { icon: Package, label: 'Deliverable', bg: 'bg-[#0A1E2F]/10', text: 'text-[#0A1E2F]' },
  custom: { icon: Pen, label: 'Custom', bg: 'bg-gray-100', text: 'text-[#666]' },
}

const PRIORITY_COLORS: Record<string, string> = {
  high: '#25785A',
  medium: '#3FAF7A',
  low: '#E5E5E5',
  none: '#E5E5E5',
}

interface TaskKanbanCardProps {
  task: TaskWithProject
  isDragOverlay?: boolean
  isSelected?: boolean
  onClick?: (task: TaskWithProject) => void
}

export function TaskKanbanCard({ task, isDragOverlay, isSelected, onClick }: TaskKanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: task.id,
    data: { task },
  })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  }

  // Handle click — only fire if pointer didn't move (drag didn't activate)
  const handlePointerUp = (e: React.PointerEvent) => {
    if (!isDragging && onClick) {
      onClick(task)
    }
  }

  const typeConfig = TYPE_CONFIG[task.task_type] || TYPE_CONFIG.custom
  const TypeIcon = typeConfig.icon
  const dueDate = task.due_date ? new Date(task.due_date) : null
  const isOverdue = dueDate && task.status !== 'completed' && task.status !== 'dismissed' && dueDate < new Date()

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onPointerUp={handlePointerUp}
      className={`bg-white border rounded-xl p-3.5 cursor-grab active:cursor-grabbing transition-all
        ${isDragging ? 'opacity-50' : ''}
        ${isDragOverlay ? 'shadow-lg rotate-1' : 'hover:shadow-md'}
        ${isSelected ? 'border-brand-primary bg-brand-primary-light' : 'border-border'}
      `}
    >
      {/* Type badge + priority dot */}
      <div className="flex items-center justify-between mb-2.5">
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-medium ${typeConfig.bg} ${typeConfig.text}`}>
          <TypeIcon className="w-3 h-3" />
          {typeConfig.label}
        </span>
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: PRIORITY_COLORS[task.priority || 'none'] }}
          title={`${task.priority || 'none'} priority`}
        />
      </div>

      {/* Title */}
      <p className="text-[13px] font-medium text-[#333] line-clamp-3 mb-2.5 leading-snug">{task.title}</p>

      {/* Footer: project + due + assignee */}
      <div className="flex items-center justify-between pt-2 border-t border-border/50">
        <span className="text-[10px] text-[#999] truncate max-w-[140px]">{task.project_name}</span>
        <div className="flex items-center gap-1.5">
          {dueDate && (
            <span className={`text-[10px] ${isOverdue ? 'text-[#D32F2F] font-medium' : 'text-[#999]'}`}>
              {dueDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          )}
          <div
            className={`w-5 h-5 rounded-full flex items-center justify-center overflow-hidden flex-shrink-0 ${
              task.assigned_to ? 'bg-[#E8F5E9]' : 'bg-[#F4F4F4]'
            }`}
            title={task.assigned_to_name || 'Unassigned'}
          >
            {task.assigned_to_photo_url ? (
              <Image src={task.assigned_to_photo_url} alt="" width={20} height={20} className="w-full h-full object-cover" />
            ) : task.assigned_to ? (
              <User className="w-2.5 h-2.5 text-brand-primary" />
            ) : (
              <User className="w-2.5 h-2.5 text-[#CCC]" />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
