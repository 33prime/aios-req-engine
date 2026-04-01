'use client'

import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { TaskWithProject } from '@/lib/api'
import { TaskKanbanCard } from './TaskKanbanCard'

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pending: { label: 'Pending', color: '#3FAF7A' },
  in_progress: { label: 'In Progress', color: '#0A1E2F' },
  completed: { label: 'Completed', color: '#999' },
  dismissed: { label: 'Dismissed', color: '#CCC' },
}

interface TaskStatusColumnProps {
  status: string
  tasks: TaskWithProject[]
  selectedTaskId?: string | null
  onTaskClick?: (task: TaskWithProject) => void
}

export function TaskStatusColumn({ status, tasks, selectedTaskId, onTaskClick }: TaskStatusColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status })
  const config = STATUS_CONFIG[status] || { label: status, color: '#999' }

  return (
    <div className="flex-1 min-w-[240px] md:min-w-[220px]">
      {/* Column header */}
      <div className="flex items-center gap-2 mb-3 px-1">
        <div className="w-2 h-2 rounded-full" style={{ backgroundColor: config.color }} />
        <span className="text-[13px] font-semibold text-[#333]">{config.label}</span>
        <span className="text-[11px] text-[#999] bg-[#F4F4F4] px-1.5 py-0.5 rounded-full">{tasks.length}</span>
      </div>

      {/* Cards container */}
      <div
        ref={setNodeRef}
        className={`space-y-2 min-h-[200px] p-2 rounded-lg transition-colors ${
          isOver ? 'bg-brand-primary-light/50 border-2 border-dashed border-brand-primary' : 'bg-[#F8F9FB]'
        }`}
      >
        <SortableContext items={tasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
          {tasks.map(task => (
            <TaskKanbanCard key={task.id} task={task} isSelected={selectedTaskId === task.id} onClick={onTaskClick} />
          ))}
        </SortableContext>
        {tasks.length === 0 && !isOver && (
          <div className="flex items-center justify-center h-24 border-2 border-dashed border-border rounded-lg">
            <span className="text-[12px] text-[#CCC]">No tasks</span>
          </div>
        )}
      </div>
    </div>
  )
}
