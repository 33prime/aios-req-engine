/**
 * TaskList Component
 *
 * Displays a filterable list of tasks with bulk actions.
 * Supports filtering by status, type, and client-relevance.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  CheckCircle,
  Filter,
  RefreshCw,
  ChevronDown,
  Inbox,
  CheckSquare,
} from 'lucide-react'
import { TaskCard, TaskCardSkeleton } from './TaskCard'
import { TaskDetailModal } from './TaskDetailModal'
import type { Task } from '@/lib/api'
import {
  listTasks,
  completeTask,
  dismissTask,
  bulkCompleteTasks,
} from '@/lib/api'

export type TaskFilter = 'all' | 'pending' | 'in_progress' | 'proposals' | 'client'
export type TaskTypeFilter = 'all' | 'proposal' | 'gap' | 'manual' | 'enrichment' | 'validation' | 'research' | 'collaboration'

interface TaskListProps {
  projectId: string
  initialFilter?: TaskFilter
  showFilters?: boolean
  showBulkActions?: boolean
  compact?: boolean
  maxItems?: number
  onNavigateToEntity?: (entityType: string, entityId: string) => void
  onTasksChange?: () => void
  /** External refresh trigger */
  refreshKey?: number
}

const filterOptions: { value: TaskFilter; label: string }[] = [
  { value: 'all', label: 'All Tasks' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'proposals', label: 'Proposals' },
  { value: 'client', label: 'Client Input' },
]

const typeFilterOptions: { value: TaskTypeFilter; label: string }[] = [
  { value: 'all', label: 'All Types' },
  { value: 'proposal', label: 'Proposals' },
  { value: 'gap', label: 'Gaps' },
  { value: 'manual', label: 'Manual' },
  { value: 'enrichment', label: 'Enrichment' },
  { value: 'validation', label: 'Validation' },
  { value: 'research', label: 'Research' },
  { value: 'collaboration', label: 'Collaboration' },
]

export function TaskList({
  projectId,
  initialFilter = 'pending',
  showFilters = true,
  showBulkActions = true,
  compact = false,
  maxItems,
  onNavigateToEntity,
  onTasksChange,
  refreshKey,
}: TaskListProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [filter, setFilter] = useState<TaskFilter>(initialFilter)
  const [typeFilter, setTypeFilter] = useState<TaskTypeFilter>('all')
  const [selectedTaskIds, setSelectedTaskIds] = useState<Set<string>>(new Set())
  const [bulkActionLoading, setBulkActionLoading] = useState(false)
  const [showFilterDropdown, setShowFilterDropdown] = useState(false)
  const [showTypeDropdown, setShowTypeDropdown] = useState(false)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const handleViewDetails = (task: Task) => {
    setSelectedTask(task)
    setIsModalOpen(true)
  }

  const handleCloseModal = () => {
    setIsModalOpen(false)
    setSelectedTask(null)
  }

  const loadTasks = useCallback(async (showLoader = true) => {
    try {
      if (showLoader) setLoading(true)
      else setRefreshing(true)

      // Build filter params
      const params: Parameters<typeof listTasks>[1] = {
        sort_by: 'priority_score',
        sort_order: 'desc',
        limit: maxItems || 50,
      }

      // Apply status filter
      if (filter === 'pending') {
        params.status = 'pending'
      } else if (filter === 'in_progress') {
        params.status = 'in_progress'
      } else if (filter === 'proposals') {
        params.task_type = 'proposal'
        params.status = 'pending'
      } else if (filter === 'client') {
        params.requires_client_input = true
        params.status = 'pending'
      }

      // Apply type filter (unless status filter already sets it)
      if (typeFilter !== 'all' && filter !== 'proposals') {
        params.task_type = typeFilter
      }

      const result = await listTasks(projectId, params)
      setTasks(result.tasks)
    } catch (error) {
      console.error('Failed to load tasks:', error)
      setTasks([])
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [projectId, filter, typeFilter, maxItems])

  useEffect(() => {
    loadTasks()
  }, [loadTasks, refreshKey])

  const handleComplete = async (taskId: string, notes?: string) => {
    try {
      await completeTask(projectId, taskId, { completion_notes: notes })
      setTasks(prev => prev.filter(t => t.id !== taskId))
      setSelectedTaskIds(prev => {
        const next = new Set(prev)
        next.delete(taskId)
        return next
      })
      onTasksChange?.()
    } catch (error) {
      console.error('Failed to complete task:', error)
      throw error
    }
  }

  const handleDismiss = async (taskId: string, reason?: string) => {
    try {
      await dismissTask(projectId, taskId, reason)
      setTasks(prev => prev.filter(t => t.id !== taskId))
      setSelectedTaskIds(prev => {
        const next = new Set(prev)
        next.delete(taskId)
        return next
      })
      onTasksChange?.()
    } catch (error) {
      console.error('Failed to dismiss task:', error)
      throw error
    }
  }

  const handleBulkComplete = async () => {
    if (selectedTaskIds.size === 0) return

    try {
      setBulkActionLoading(true)
      await bulkCompleteTasks(projectId, Array.from(selectedTaskIds))
      setTasks(prev => prev.filter(t => !selectedTaskIds.has(t.id)))
      setSelectedTaskIds(new Set())
      onTasksChange?.()
    } catch (error) {
      console.error('Failed to bulk complete tasks:', error)
    } finally {
      setBulkActionLoading(false)
    }
  }

  const toggleTaskSelection = (taskId: string) => {
    setSelectedTaskIds(prev => {
      const next = new Set(prev)
      if (next.has(taskId)) {
        next.delete(taskId)
      } else {
        next.add(taskId)
      }
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedTaskIds.size === tasks.length) {
      setSelectedTaskIds(new Set())
    } else {
      setSelectedTaskIds(new Set(tasks.map(t => t.id)))
    }
  }

  const currentFilterLabel = filterOptions.find(f => f.value === filter)?.label || 'All Tasks'

  if (loading) {
    return (
      <div className="space-y-3">
        {compact ? (
          <>
            <TaskCardSkeleton compact />
            <TaskCardSkeleton compact />
            <TaskCardSkeleton compact />
          </>
        ) : (
          <>
            <TaskCardSkeleton />
            <TaskCardSkeleton />
          </>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with filters and bulk actions */}
      {(showFilters || showBulkActions) && (
        <div className="flex items-center justify-between gap-4">
          {/* Filters */}
          {showFilters && (
            <div className="flex items-center gap-2">
              {/* Status filter */}
              <div className="relative">
                <button
                  onClick={() => {
                    setShowFilterDropdown(!showFilterDropdown)
                    setShowTypeDropdown(false)
                  }}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Filter className="w-4 h-4 text-gray-500" />
                  {currentFilterLabel}
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                </button>

                {showFilterDropdown && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowFilterDropdown(false)}
                    />
                    <div className="absolute top-full left-0 mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
                      {filterOptions.map(option => (
                        <button
                          key={option.value}
                          onClick={() => {
                            setFilter(option.value)
                            setShowFilterDropdown(false)
                          }}
                          className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg ${
                            filter === option.value ? 'text-[#009b87] font-medium' : 'text-gray-700'
                          }`}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>

              {/* Type filter */}
              <div className="relative">
                <button
                  onClick={() => {
                    setShowTypeDropdown(!showTypeDropdown)
                    setShowFilterDropdown(false)
                  }}
                  className={`flex items-center gap-2 px-3 py-1.5 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors ${
                    typeFilter !== 'all' ? 'border-[#009b87]' : ''
                  }`}
                >
                  {typeFilterOptions.find(t => t.value === typeFilter)?.label || 'All Types'}
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                </button>

                {showTypeDropdown && (
                  <>
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setShowTypeDropdown(false)}
                    />
                    <div className="absolute top-full left-0 mt-1 w-40 bg-white border border-gray-200 rounded-lg shadow-lg z-20">
                      {typeFilterOptions.map(option => (
                        <button
                          key={option.value}
                          onClick={() => {
                            setTypeFilter(option.value)
                            setShowTypeDropdown(false)
                          }}
                          className={`w-full text-left px-3 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg ${
                            typeFilter === option.value ? 'text-[#009b87] font-medium' : 'text-gray-700'
                          }`}
                        >
                          {option.label}
                        </button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* Bulk actions and refresh */}
          <div className="flex items-center gap-2">
            {showBulkActions && selectedTaskIds.size > 0 && (
              <button
                onClick={handleBulkComplete}
                disabled={bulkActionLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-[#009b87] hover:bg-[#007a6a] rounded-lg transition-colors disabled:opacity-50"
              >
                {bulkActionLoading ? (
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                ) : (
                  <CheckSquare className="w-4 h-4" />
                )}
                Complete ({selectedTaskIds.size})
              </button>
            )}

            <button
              onClick={() => loadTasks(false)}
              disabled={refreshing}
              className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
              title="Refresh tasks"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      )}

      {/* Select all for bulk actions */}
      {showBulkActions && tasks.length > 0 && !compact && (
        <div className="flex items-center gap-2 pb-2 border-b border-gray-100">
          <button
            onClick={toggleSelectAll}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
          >
            <div className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
              selectedTaskIds.size === tasks.length
                ? 'bg-[#009b87] border-[#009b87]'
                : selectedTaskIds.size > 0
                ? 'bg-[#009b87]/30 border-[#009b87]'
                : 'border-gray-300'
            }`}>
              {selectedTaskIds.size > 0 && (
                <CheckCircle className="w-3 h-3 text-white" />
              )}
            </div>
            {selectedTaskIds.size === tasks.length ? 'Deselect all' : 'Select all'}
          </button>
          <span className="text-xs text-gray-400">
            {tasks.length} {tasks.length === 1 ? 'task' : 'tasks'}
          </span>
        </div>
      )}

      {/* Task list */}
      {tasks.length > 0 ? (
        <div className="space-y-3">
          {tasks.map(task => (
            <div key={task.id} className="flex items-start gap-2">
              {showBulkActions && !compact && (
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    toggleTaskSelection(task.id)
                  }}
                  className={`mt-4 w-5 h-5 rounded border-2 flex-shrink-0 flex items-center justify-center transition-colors ${
                    selectedTaskIds.has(task.id)
                      ? 'bg-[#009b87] border-[#009b87]'
                      : 'border-gray-300 hover:border-gray-400'
                  }`}
                >
                  {selectedTaskIds.has(task.id) && (
                    <CheckCircle className="w-3 h-3 text-white" />
                  )}
                </button>
              )}
              <div className="flex-1">
                <TaskCard
                  task={task}
                  onComplete={handleComplete}
                  onDismiss={handleDismiss}
                  onNavigate={onNavigateToEntity}
                  onViewDetails={handleViewDetails}
                  compact={compact}
                />
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyTaskState filter={filter} />
      )}

      {/* Task Detail Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          projectId={projectId}
          isOpen={isModalOpen}
          onClose={handleCloseModal}
          onComplete={handleComplete}
          onDismiss={handleDismiss}
        />
      )}
    </div>
  )
}

function EmptyTaskState({ filter }: { filter: TaskFilter }) {
  const messages: Record<TaskFilter, { title: string; description: string }> = {
    all: {
      title: 'No tasks',
      description: 'Tasks are created automatically from signal processing, gap detection, and enrichment triggers.',
    },
    pending: {
      title: 'All caught up!',
      description: 'No pending tasks. Tasks will appear here when signals are processed or gaps are detected.',
    },
    in_progress: {
      title: 'No tasks in progress',
      description: 'Tasks move here when you start working on them.',
    },
    proposals: {
      title: 'No proposal tasks',
      description: 'Proposal tasks are created when signals are processed. Upload a transcript to get started.',
    },
    client: {
      title: 'No client input needed',
      description: 'Tasks requiring client validation will appear here.',
    },
  }

  const { title, description } = messages[filter]

  return (
    <div className="text-center py-8">
      <Inbox className="w-10 h-10 text-gray-300 mx-auto mb-3" />
      <h3 className="text-sm font-medium text-gray-900 mb-1">{title}</h3>
      <p className="text-xs text-gray-500 max-w-xs mx-auto">{description}</p>
    </div>
  )
}

/**
 * TaskListCompact - Simplified version for dashboards
 */
export function TaskListCompact({
  projectId,
  maxItems = 5,
  filter = 'pending',
  onNavigateToEntity,
  onTasksChange,
  refreshKey,
}: {
  projectId: string
  maxItems?: number
  filter?: TaskFilter
  onNavigateToEntity?: (entityType: string, entityId: string) => void
  onTasksChange?: () => void
  refreshKey?: number
}) {
  return (
    <TaskList
      projectId={projectId}
      initialFilter={filter}
      showFilters={false}
      showBulkActions={false}
      compact={true}
      maxItems={maxItems}
      onNavigateToEntity={onNavigateToEntity}
      onTasksChange={onTasksChange}
      refreshKey={refreshKey}
    />
  )
}
