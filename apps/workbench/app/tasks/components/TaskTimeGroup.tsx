'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { TaskWithProject } from '@/lib/api'
import { TaskRow } from './TaskRow'

interface TaskTimeGroupProps {
  title: string
  count: number
  tasks: TaskWithProject[]
  defaultCollapsed?: boolean
  accentColor?: string
  onToggleComplete: (task: TaskWithProject) => void
  selectedTaskId?: string | null
  onTaskClick?: (task: TaskWithProject) => void
}

export function TaskTimeGroup({
  title,
  count,
  tasks,
  defaultCollapsed = false,
  accentColor,
  onToggleComplete,
  selectedTaskId,
  onTaskClick,
}: TaskTimeGroupProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed)

  if (count === 0) return null

  return (
    <div className="mb-2 mt-3 first:mt-0">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2.5 w-full px-4 py-2.5 hover:bg-[#F8F9FB] rounded-lg transition-colors"
      >
        <div
          className="w-1.5 h-1.5 rounded-full flex-shrink-0"
          style={{ backgroundColor: accentColor || '#CCC' }}
        />
        <span className="text-[13px] font-medium text-[#333]">
          {title}
        </span>
        <span className="text-[11px] text-[#999] bg-[#F4F4F4] px-1.5 py-0.5 rounded-full min-w-[20px] text-center">{count}</span>
        <span className="ml-auto text-[10px] text-[#CCC]">
          {collapsed ? '▸' : '▾'}
        </span>
      </button>

      {/* Tasks */}
      {!collapsed && (
        <div>
          {tasks.map((task) => (
            <TaskRow key={task.id} task={task} accentColor={accentColor} onToggleComplete={onToggleComplete} isSelected={selectedTaskId ? task.id === selectedTaskId : undefined} onClick={onTaskClick} />
          ))}
        </div>
      )}
    </div>
  )
}
