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
}

export function TaskTimeGroup({
  title,
  count,
  tasks,
  defaultCollapsed = false,
  accentColor,
  onToggleComplete,
}: TaskTimeGroupProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed)

  if (count === 0) return null

  return (
    <div className="mb-2">
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 w-full px-3 py-2 hover:bg-[#FAFAFA] rounded-lg transition-colors"
      >
        {collapsed ? (
          <ChevronRight className="w-3.5 h-3.5 text-[#999]" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5 text-[#999]" />
        )}
        <span
          className="text-[12px] font-semibold uppercase tracking-wide"
          style={{ color: accentColor || '#999' }}
        >
          {title}
        </span>
        <span className="text-[11px] text-[#CCC]">{count}</span>
      </button>

      {/* Tasks */}
      {!collapsed && (
        <div className="ml-1">
          {tasks.map((task) => (
            <TaskRow key={task.id} task={task} onToggleComplete={onToggleComplete} />
          ))}
        </div>
      )}
    </div>
  )
}
