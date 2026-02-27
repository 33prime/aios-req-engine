'use client'

import { useState, useMemo } from 'react'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { useMyTasks } from '@/lib/hooks/use-api'
import { completeTask } from '@/lib/api'
import type { TaskWithProject } from '@/lib/api'
import { TasksPageHeader } from './components/TasksPageHeader'
import { TaskTimeGroup } from './components/TaskTimeGroup'
import { AddTaskModal } from './components/AddTaskModal'

type View = 'assigned_to_me' | 'created_by_me' | 'all'

function groupByDue(tasks: TaskWithProject[]) {
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const tomorrow = new Date(today.getTime() + 86400000)
  const nextWeek = new Date(today.getTime() + 7 * 86400000)

  const groups = {
    overdue: [] as TaskWithProject[],
    today: [] as TaskWithProject[],
    next: [] as TaskWithProject[],
    later: [] as TaskWithProject[],
    completed: [] as TaskWithProject[],
  }

  for (const task of tasks) {
    if (task.status === 'completed' || task.status === 'dismissed') {
      groups.completed.push(task)
      continue
    }

    if (!task.due_date) {
      groups.later.push(task)
      continue
    }

    const due = new Date(task.due_date)
    const dueDay = new Date(due.getFullYear(), due.getMonth(), due.getDate())

    if (dueDay < today) groups.overdue.push(task)
    else if (dueDay.getTime() === today.getTime()) groups.today.push(task)
    else if (dueDay < nextWeek) groups.next.push(task)
    else groups.later.push(task)
  }

  return groups
}

export default function TasksPage() {
  const [view, setView] = useState<View>('all')
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)

  const { data, mutate, isLoading } = useMyTasks(view)

  const groups = useMemo(
    () => groupByDue(data?.tasks || []),
    [data?.tasks]
  )

  const handleToggleComplete = async (task: TaskWithProject) => {
    try {
      await completeTask(task.project_id, task.id, { completion_method: 'task_board' })
      mutate()
    } catch (err) {
      console.error('Failed to complete task:', err)
    }
  }

  const sidebarWidth = sidebarCollapsed ? 64 : 224

  return (
    <>
      <AppSidebar
        isCollapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <div
        className="min-h-screen bg-surface-page transition-all duration-300"
        style={{ marginLeft: sidebarWidth }}
      >
        <div className="max-w-[900px] mx-auto px-4 py-4">
          <TasksPageHeader
            view={view}
            counts={data?.counts || {}}
            onViewChange={setView}
            onAddTask={() => setShowAddModal(true)}
          />

          {isLoading && !data ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary" />
            </div>
          ) : (data?.tasks.length || 0) === 0 ? (
            <div className="text-center py-20">
              <p className="text-[14px] text-[#999] mb-2">No tasks yet</p>
              <p className="text-[12px] text-[#CCC]">
                Tasks you create or are assigned to will appear here.
              </p>
            </div>
          ) : (
            <>
              <TaskTimeGroup
                title="Overdue"
                count={groups.overdue.length}
                tasks={groups.overdue}
                accentColor="#D32F2F"
                onToggleComplete={handleToggleComplete}
              />
              <TaskTimeGroup
                title="Today"
                count={groups.today.length}
                tasks={groups.today}
                accentColor="#0A1E2F"
                onToggleComplete={handleToggleComplete}
              />
              <TaskTimeGroup
                title="Next 7 days"
                count={groups.next.length}
                tasks={groups.next}
                accentColor="#666"
                onToggleComplete={handleToggleComplete}
              />
              <TaskTimeGroup
                title="Later"
                count={groups.later.length}
                tasks={groups.later}
                onToggleComplete={handleToggleComplete}
              />
              <TaskTimeGroup
                title="Completed"
                count={groups.completed.length}
                tasks={groups.completed}
                defaultCollapsed
                onToggleComplete={handleToggleComplete}
              />
            </>
          )}
        </div>
      </div>

      <AddTaskModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onCreated={() => mutate()}
      />
    </>
  )
}
