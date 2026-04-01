'use client'

import type { TaskWithProject } from '@/lib/api'
import { TaskTimeGroup } from './TaskTimeGroup'

interface TaskListPanelProps {
  groups: {
    overdue: TaskWithProject[]
    today: TaskWithProject[]
    next: TaskWithProject[]
    later: TaskWithProject[]
    completed: TaskWithProject[]
    dismissed: TaskWithProject[]
  }
  selectedTaskId: string | null
  onSelectTask: (task: TaskWithProject) => void
  onToggleComplete: (task: TaskWithProject) => void
}

export function TaskListPanel({ groups, selectedTaskId, onSelectTask, onToggleComplete }: TaskListPanelProps) {
  return (
    <div className="overflow-y-auto h-[calc(100vh-180px)] pt-2">
      <TaskTimeGroup title="Overdue" count={groups.overdue.length} tasks={groups.overdue} accentColor="#D32F2F" onToggleComplete={onToggleComplete} selectedTaskId={selectedTaskId} onTaskClick={onSelectTask} />
      <TaskTimeGroup title="Today" count={groups.today.length} tasks={groups.today} accentColor="#0A1E2F" onToggleComplete={onToggleComplete} selectedTaskId={selectedTaskId} onTaskClick={onSelectTask} />
      <TaskTimeGroup title="Next 7 days" count={groups.next.length} tasks={groups.next} accentColor="#666" onToggleComplete={onToggleComplete} selectedTaskId={selectedTaskId} onTaskClick={onSelectTask} />
      <TaskTimeGroup title="Later" count={groups.later.length} tasks={groups.later} onToggleComplete={onToggleComplete} selectedTaskId={selectedTaskId} onTaskClick={onSelectTask} />
      <TaskTimeGroup title="Completed" count={groups.completed.length} tasks={groups.completed} defaultCollapsed onToggleComplete={onToggleComplete} selectedTaskId={selectedTaskId} onTaskClick={onSelectTask} />
      <TaskTimeGroup title="Dismissed" count={groups.dismissed.length} tasks={groups.dismissed} defaultCollapsed accentColor="#CCC" onToggleComplete={onToggleComplete} selectedTaskId={selectedTaskId} onTaskClick={onSelectTask} />
    </div>
  )
}
