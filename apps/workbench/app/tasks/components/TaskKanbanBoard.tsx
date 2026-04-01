'use client'

import { useState, useMemo, useCallback } from 'react'
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragStartEvent,
  type DragEndEvent,
} from '@dnd-kit/core'
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable'
import { updateTask } from '@/lib/api'
import type { TaskWithProject } from '@/lib/api'
import { TaskStatusColumn } from './TaskStatusColumn'
import { TaskKanbanCard } from './TaskKanbanCard'

const STATUSES = ['pending', 'in_progress', 'completed'] as const

interface TaskKanbanBoardProps {
  tasks: TaskWithProject[]
  selectedTaskId?: string | null
  onTaskClick?: (task: TaskWithProject) => void
  onTaskUpdated: () => void
}

export function TaskKanbanBoard({ tasks, selectedTaskId, onTaskClick, onTaskUpdated }: TaskKanbanBoardProps) {
  const [activeTask, setActiveTask] = useState<TaskWithProject | null>(null)
  const [localOverrides, setLocalOverrides] = useState<Record<string, string>>({}) // taskId -> status

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

  // Group tasks by status, applying optimistic overrides
  const tasksByStatus = useMemo(() => {
    const groups: Record<string, TaskWithProject[]> = {
      pending: [],
      in_progress: [],
      completed: [],
    }
    for (const task of tasks) {
      if (task.status === 'dismissed' && !localOverrides[task.id]) continue // hide dismissed from board
      const status = localOverrides[task.id] || task.status
      if (groups[status]) groups[status].push(task)
    }
    return groups
  }, [tasks, localOverrides])

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const task = event.active.data.current?.task as TaskWithProject | undefined
    if (task) setActiveTask(task)
  }, [])

  const handleDragEnd = useCallback(async (event: DragEndEvent) => {
    setActiveTask(null)
    const { active, over } = event
    if (!over) return

    const taskId = active.id as string
    const task = active.data.current?.task as TaskWithProject | undefined
    if (!task) return

    // Determine target status -- over.id is either a column status or a card id
    let targetStatus = over.id as string
    if (!STATUSES.includes(targetStatus as (typeof STATUSES)[number])) {
      // Dropped on a card -- find which column that card is in
      for (const [status, statusTasks] of Object.entries(tasksByStatus)) {
        if (statusTasks.some(t => t.id === over.id)) {
          targetStatus = status
          break
        }
      }
    }

    const currentStatus = localOverrides[taskId] || task.status
    if (targetStatus === currentStatus) return

    // Optimistic update
    setLocalOverrides(prev => ({ ...prev, [taskId]: targetStatus }))

    try {
      await updateTask(task.project_id, taskId, { status: targetStatus })
      // Clear override and refresh from server
      setLocalOverrides(prev => {
        const next = { ...prev }
        delete next[taskId]
        return next
      })
      onTaskUpdated()
    } catch (err) {
      console.error('Failed to update task status:', err)
      // Revert optimistic update
      setLocalOverrides(prev => {
        const next = { ...prev }
        delete next[taskId]
        return next
      })
    }
  }, [tasksByStatus, localOverrides, onTaskUpdated])

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-3 pb-4 overflow-x-auto -mx-3 px-3 md:mx-0 md:px-0">
        {STATUSES.map(status => (
          <TaskStatusColumn
            key={status}
            status={status}
            tasks={tasksByStatus[status]}
            selectedTaskId={selectedTaskId}
            onTaskClick={onTaskClick}
          />
        ))}
      </div>

      <DragOverlay>
        {activeTask && <TaskKanbanCard task={activeTask} isDragOverlay />}
      </DragOverlay>
    </DndContext>
  )
}
