'use client'

import { useState, useMemo } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { AppSidebar } from '@/components/workspace/AppSidebar'
import { useMyTasks } from '@/lib/hooks/use-api'
import { completeTask } from '@/lib/api'
import type { TaskWithProject } from '@/lib/api'
import { TasksPageHeader } from './components/TasksPageHeader'
import { TaskMasterDetail } from './components/TaskMasterDetail'
import { TaskKanbanBoard } from './components/TaskKanbanBoard'
import { TaskDetailPanel } from './components/TaskDetailPanel'
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
    dismissed: [] as TaskWithProject[],
  }

  for (const task of tasks) {
    if (task.status === 'dismissed') {
      groups.dismissed.push(task)
      continue
    }
    if (task.status === 'completed') {
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
  const searchParams = useSearchParams()
  const router = useRouter()
  const initialView = (searchParams.get('view') as View) || 'all'
  const initialMode = (searchParams.get('mode') as 'list' | 'kanban') || 'list'
  const [view, setView] = useState<View>(initialView)
  const [viewMode, setViewMode] = useState<'list' | 'kanban'>(initialMode)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)

  const handleViewChange = (newView: View) => {
    setView(newView)
    const params = new URLSearchParams(searchParams.toString())
    if (newView === 'all') params.delete('view')
    else params.set('view', newView)
    const qs = params.toString()
    router.replace(`/tasks${qs ? `?${qs}` : ''}`, { scroll: false })
  }

  const handleViewModeChange = (mode: 'list' | 'kanban') => {
    setViewMode(mode)
    const params = new URLSearchParams(searchParams.toString())
    if (mode === 'list') params.delete('mode')
    else params.set('mode', mode)
    const qs = params.toString()
    router.replace(`/tasks${qs ? `?${qs}` : ''}`, { scroll: false })
  }

  const handleSelectTask = (task: TaskWithProject) => {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      router.push(`/tasks/${task.id}`)
    } else {
      setSelectedTaskId(task.id)
    }
  }

  const [filterType, setFilterType] = useState<string>('all')
  const [filterPriority, setFilterPriority] = useState<string>('all')
  const [filterProject, setFilterProject] = useState<string>('all')

  const { data, mutate, isLoading } = useMyTasks(view)

  const projectNames = useMemo(() => {
    const names = new Set((data?.tasks || []).map(t => t.project_name).filter(Boolean))
    return Array.from(names).sort()
  }, [data?.tasks])

  const filteredTasks = useMemo(() => {
    let tasks = data?.tasks || []
    if (filterType !== 'all') tasks = tasks.filter(t => t.task_type === filterType)
    if (filterPriority !== 'all') {
      if (filterPriority === 'high') tasks = tasks.filter(t => (t.priority_score || 0) >= 70)
      else if (filterPriority === 'medium') tasks = tasks.filter(t => (t.priority_score || 0) >= 40 && (t.priority_score || 0) < 70)
      else if (filterPriority === 'low') tasks = tasks.filter(t => (t.priority_score || 0) > 0 && (t.priority_score || 0) < 40)
    }
    if (filterProject !== 'all') tasks = tasks.filter(t => t.project_name === filterProject)
    return tasks
  }, [data?.tasks, filterType, filterPriority, filterProject])

  const groups = useMemo(
    () => groupByDue(filteredTasks),
    [filteredTasks]
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
        <div className="px-3 md:px-6 py-4">
          <TasksPageHeader
            view={view}
            counts={data?.counts || {}}
            onViewChange={handleViewChange}
            onAddTask={() => setShowAddModal(true)}
            viewMode={viewMode}
            onViewModeChange={handleViewModeChange}
          />

          {/* Toolbar: filters + stats */}
          <div className="flex items-center gap-3 mb-5 overflow-x-auto pb-1 -mx-3 px-3 md:mx-0 md:px-0 md:overflow-visible md:flex-wrap">
            <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="appearance-none px-3 py-1.5 pr-7 text-[12px] border border-border rounded-full bg-white text-[#666] hover:border-[#CCC] focus:outline-none focus:border-brand-primary cursor-pointer transition-colors" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'10\' height=\'6\' viewBox=\'0 0 10 6\'%3E%3Cpath d=\'M1 1l4 4 4-4\' stroke=\'%23999\' fill=\'none\' stroke-width=\'1.5\' stroke-linecap=\'round\'/%3E%3C/svg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center' }}>
              <option value="all">All Types</option>
              <option value="custom">Custom</option>
              <option value="action_item">Action Item</option>
              <option value="meeting_prep">Meeting Prep</option>
              <option value="book_meeting">Book Meeting</option>
              <option value="reminder">Reminder</option>
              <option value="review_request">Review Request</option>
              <option value="deliverable">Deliverable</option>
              <option value="signal_review">Signal Review</option>
            </select>
            <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)} className="appearance-none px-3 py-1.5 pr-7 text-[12px] border border-border rounded-full bg-white text-[#666] hover:border-[#CCC] focus:outline-none focus:border-brand-primary cursor-pointer transition-colors" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'10\' height=\'6\' viewBox=\'0 0 10 6\'%3E%3Cpath d=\'M1 1l4 4 4-4\' stroke=\'%23999\' fill=\'none\' stroke-width=\'1.5\' stroke-linecap=\'round\'/%3E%3C/svg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center' }}>
              <option value="all">All Priorities</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <select value={filterProject} onChange={(e) => setFilterProject(e.target.value)} className="appearance-none px-3 py-1.5 pr-7 text-[12px] border border-border rounded-full bg-white text-[#666] hover:border-[#CCC] focus:outline-none focus:border-brand-primary cursor-pointer transition-colors" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'10\' height=\'6\' viewBox=\'0 0 10 6\'%3E%3Cpath d=\'M1 1l4 4 4-4\' stroke=\'%23999\' fill=\'none\' stroke-width=\'1.5\' stroke-linecap=\'round\'/%3E%3C/svg%3E")', backgroundRepeat: 'no-repeat', backgroundPosition: 'right 10px center' }}>
              <option value="all">All Projects</option>
              {projectNames.map(name => (
                <option key={name} value={name}>{name}</option>
              ))}
            </select>
            {data && (
              <div className="ml-auto hidden md:flex items-center gap-3 text-[11px] text-[#BBB] flex-shrink-0">
                <span>{data.counts?.pending || 0} pending</span>
                <span>{data.counts?.in_progress || 0} active</span>
                <span>{data.counts?.completed || 0} done</span>
              </div>
            )}
          </div>

          {isLoading && !data ? (
            <div className="flex items-center justify-center py-20">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary" />
            </div>
          ) : (data?.tasks.length || 0) === 0 ? (
            <div className="text-center py-20">
              <p className="text-[14px] text-[#666] mb-1">No tasks yet</p>
              <p className="text-[12px] text-[#999] mb-4">
                Tasks are created when you process signals, or you can add one manually.
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-white bg-brand-primary rounded-lg hover:bg-brand-primary-hover transition-colors"
              >
                Add your first task
              </button>
            </div>
          ) : viewMode === 'list' ? (
            <TaskMasterDetail
              groups={groups}
              selectedTaskId={selectedTaskId}
              onSelectTask={handleSelectTask}
              onToggleComplete={handleToggleComplete}
              onTaskUpdated={() => mutate()}
            />
          ) : (
            <div className="flex gap-5">
              <div className="flex-1 min-w-0">
                <TaskKanbanBoard
                  tasks={filteredTasks}
                  selectedTaskId={selectedTaskId}
                  onTaskClick={handleSelectTask}
                  onTaskUpdated={() => mutate()}
                />
              </div>
              {selectedTaskId && (
                <div className="w-[360px] flex-shrink-0 hidden lg:block bg-white border border-border rounded-xl overflow-y-auto h-[calc(100vh-180px)]">
                  <TaskDetailPanel taskId={selectedTaskId} onTaskUpdated={() => mutate()} />
                </div>
              )}
            </div>
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
