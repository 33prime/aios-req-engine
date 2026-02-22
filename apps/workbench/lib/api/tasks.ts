import { apiRequest } from './core'

// ============================================
// Task Types
// ============================================

export type TaskTypeValue =
  | 'signal_review'
  | 'action_item'
  | 'meeting_prep'
  | 'reminder'
  | 'review_request'
  | 'book_meeting'
  | 'deliverable'
  | 'custom'

export type ReviewStatusValue =
  | 'pending_review'
  | 'in_review'
  | 'approved'
  | 'changes_requested'

export type MeetingTypeValue =
  | 'discovery'
  | 'event_modeling'
  | 'proposal'
  | 'prototype_review'
  | 'kickoff'
  | 'stakeholder_interview'
  | 'technical_deep_dive'
  | 'internal_strategy'
  | 'introduction'
  | 'monthly_check_in'
  | 'hand_off'

export type ActionVerbValue =
  | 'send'
  | 'email'
  | 'schedule'
  | 'prepare'
  | 'review'
  | 'follow_up'
  | 'share'
  | 'create'

// ============================================
// Task Interfaces
// ============================================

export interface Task {
  id: string
  project_id: string
  title: string
  description?: string
  task_type: TaskTypeValue
  anchored_entity_type?: string
  anchored_entity_id?: string
  priority_score: number
  status: 'pending' | 'in_progress' | 'completed' | 'dismissed'
  requires_client_input: boolean
  source_type: string
  source_id?: string
  source_context?: Record<string, unknown>
  completed_at?: string
  completed_by?: string
  completion_method?: string
  completion_notes?: string
  assigned_to?: string
  due_date?: string
  created_by?: string
  priority?: 'none' | 'low' | 'medium' | 'high'
  review_status?: ReviewStatusValue | null
  remind_at?: string | null
  meeting_type?: MeetingTypeValue | null
  meeting_date?: string | null
  signal_id?: string | null
  patches_snapshot?: Record<string, unknown> | null
  action_verb?: ActionVerbValue | null
  created_at: string
  updated_at: string
}

export interface TaskWithProject extends Omit<Task, 'source_context' | 'completed_at' | 'completed_by' | 'completion_method' | 'completion_notes' | 'source_type' | 'source_id'> {
  project_name: string
  assigned_to_name?: string
  assigned_to_photo_url?: string
}

export interface MyTasksResponse {
  tasks: TaskWithProject[]
  total: number
  counts: Record<string, number>
}

export interface TaskComment {
  id: string
  task_id: string
  project_id: string
  author_id: string
  body: string
  author_name?: string
  author_photo_url?: string
  created_at: string
  updated_at: string
}

export interface TaskCommentListResponse {
  comments: TaskComment[]
  total: number
}

export interface TaskListResponse {
  tasks: Task[]
  total: number
  has_more: boolean
}

export interface TaskStatsResponse {
  total: number
  by_status: Record<string, number>
  by_type: Record<string, number>
  client_relevant: number
  avg_priority: number
}

export interface TaskActivity {
  id: string
  task_id: string
  action: 'created' | 'started' | 'updated' | 'completed' | 'dismissed' | 'reopened' | 'priority_changed' | 'assigned' | 'commented' | 'due_date_changed' | 'review_status_changed' | 'reminder_sent'
  actor_id?: string
  actor_type: 'user' | 'system' | 'ai_assistant'
  changes?: Record<string, unknown>
  note?: string
  created_at: string
}

export interface TaskActivityListResponse {
  activities: TaskActivity[]
  total: number
}

// ============================================
// Task APIs
// ============================================

export const listTasks = (
  projectId: string,
  params?: {
    status?: string
    task_type?: string
    requires_client_input?: boolean
    limit?: number
    offset?: number
    sort_by?: string
    sort_order?: 'asc' | 'desc'
  }
) => {
  const queryParams = new URLSearchParams()
  if (params?.status) queryParams.set('status', params.status)
  if (params?.task_type) queryParams.set('task_type', params.task_type)
  if (params?.requires_client_input !== undefined) {
    queryParams.set('requires_client_input', params.requires_client_input.toString())
  }
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.offset) queryParams.set('offset', params.offset.toString())
  if (params?.sort_by) queryParams.set('sort_by', params.sort_by)
  if (params?.sort_order) queryParams.set('sort_order', params.sort_order)

  const query = queryParams.toString()
  return apiRequest<TaskListResponse>(
    `/projects/${projectId}/tasks${query ? `?${query}` : ''}`
  )
}

export const getTask = (projectId: string, taskId: string) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}`)

export const getTaskStats = (projectId: string) =>
  apiRequest<TaskStatsResponse>(`/projects/${projectId}/tasks/stats`)

export const createTask = (
  projectId: string,
  data: {
    title: string
    description?: string
    task_type?: TaskTypeValue
    anchored_entity_type?: string
    anchored_entity_id?: string
    requires_client_input?: boolean
    metadata?: Record<string, unknown>
    assigned_to?: string
    due_date?: string
    priority?: string
    remind_at?: string
    meeting_type?: MeetingTypeValue
    meeting_date?: string
    action_verb?: ActionVerbValue
  }
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks`, {
    method: 'POST',
    body: JSON.stringify(data),
  })

export const updateTask = (
  projectId: string,
  taskId: string,
  data: {
    title?: string
    description?: string
    status?: string
    requires_client_input?: boolean
    priority_score?: number
    assigned_to?: string
    due_date?: string
    priority?: string
    review_status?: string
    remind_at?: string
    meeting_type?: string
    meeting_date?: string
    action_verb?: string
  }
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })

export const completeTask = (
  projectId: string,
  taskId: string,
  data?: {
    completion_method?: string
    completion_notes?: string
  }
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}/complete`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  })

export const dismissTask = (
  projectId: string,
  taskId: string,
  reason?: string
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}/dismiss`, {
    method: 'POST',
    body: JSON.stringify({ reason }),
  })

export const updateReviewStatus = (
  projectId: string,
  taskId: string,
  reviewStatus: ReviewStatusValue
) =>
  apiRequest<Task>(`/projects/${projectId}/tasks/${taskId}/review-status`, {
    method: 'POST',
    body: JSON.stringify({ review_status: reviewStatus }),
  })

export const bulkCompleteTasks = (
  projectId: string,
  taskIds: string[],
  completionMethod?: string
) =>
  apiRequest<{ processed: number; tasks: Task[] }>(
    `/projects/${projectId}/tasks/bulk/complete`,
    {
      method: 'POST',
      body: JSON.stringify({
        task_ids: taskIds,
        completion_method: completionMethod || 'chat_approval',
      }),
    }
  )

export const bulkDismissTasks = (
  projectId: string,
  taskIds: string[],
  reason?: string
) =>
  apiRequest<{ processed: number; tasks: Task[] }>(
    `/projects/${projectId}/tasks/bulk/dismiss`,
    {
      method: 'POST',
      body: JSON.stringify({ task_ids: taskIds, reason }),
    }
  )

export const getProjectTaskActivity = (
  projectId: string,
  params?: { limit?: number; offset?: number }
) => {
  const queryParams = new URLSearchParams()
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.offset) queryParams.set('offset', params.offset.toString())
  const query = queryParams.toString()
  return apiRequest<TaskActivityListResponse>(
    `/projects/${projectId}/tasks/activity${query ? `?${query}` : ''}`
  )
}

// ============================================
// Cross-Project Task APIs
// ============================================

export const listMyTasks = (params?: {
  view?: 'assigned_to_me' | 'created_by_me' | 'all'
  status?: string
  limit?: number
  offset?: number
}) => {
  const queryParams = new URLSearchParams()
  if (params?.view) queryParams.set('view', params.view)
  if (params?.status) queryParams.set('status', params.status)
  if (params?.limit) queryParams.set('limit', params.limit.toString())
  if (params?.offset) queryParams.set('offset', params.offset.toString())
  const query = queryParams.toString()
  return apiRequest<MyTasksResponse>(`/tasks/my${query ? `?${query}` : ''}`)
}

export const getTaskById = (taskId: string) =>
  apiRequest<TaskWithProject>(`/tasks/${taskId}`)

export const listTaskComments = (taskId: string) =>
  apiRequest<TaskCommentListResponse>(`/tasks/${taskId}/comments`)

export const createTaskComment = (taskId: string, body: string) =>
  apiRequest<TaskComment>(`/tasks/${taskId}/comments`, {
    method: 'POST',
    body: JSON.stringify({ body }),
  })

export const deleteTaskComment = (taskId: string, commentId: string) =>
  apiRequest<{ deleted: boolean }>(`/tasks/${taskId}/comments/${commentId}`, {
    method: 'DELETE',
  })
