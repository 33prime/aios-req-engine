'use client'

import type { TaskWithProject } from '@/lib/api'
import { TaskListPanel } from './TaskListPanel'
import { TaskDetailPanel } from './TaskDetailPanel'

interface TaskMasterDetailProps {
  groups: { overdue: TaskWithProject[]; today: TaskWithProject[]; next: TaskWithProject[]; later: TaskWithProject[]; completed: TaskWithProject[]; dismissed: TaskWithProject[] }
  selectedTaskId: string | null
  onSelectTask: (task: TaskWithProject) => void
  onToggleComplete: (task: TaskWithProject) => void
  onTaskUpdated: () => void
}

export function TaskMasterDetail({ groups, selectedTaskId, onSelectTask, onToggleComplete, onTaskUpdated }: TaskMasterDetailProps) {
  return (
    <div className="flex gap-6">
      {/* Left: task list */}
      <div className="w-full md:w-[55%] flex-shrink-0 bg-white border border-border rounded-xl overflow-hidden">
        <TaskListPanel
          groups={groups}
          selectedTaskId={selectedTaskId}
          onSelectTask={onSelectTask}
          onToggleComplete={onToggleComplete}
        />
      </div>
      {/* Right: detail panel — hidden on mobile */}
      <div className="flex-1 hidden md:block bg-white border border-border rounded-xl overflow-y-auto h-[calc(100vh-180px)]">
        <TaskDetailPanel taskId={selectedTaskId} onTaskUpdated={onTaskUpdated} />
      </div>
    </div>
  )
}
