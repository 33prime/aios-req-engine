'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Trash2, RotateCcw, CheckCircle2, ClipboardList, ExternalLink } from 'lucide-react'
import { useTaskDetail, useTaskComments, useProfile } from '@/lib/hooks/use-api'
import {
  updateTask,
  createTaskComment,
  deleteTaskComment,
  deleteTask,
  reopenTask,
  completeTask,
  getProjectTaskActivity,
  listOrganizations,
  listOrganizationMembers,
} from '@/lib/api'
import type { TaskActivity } from '@/lib/api'
import type { OrganizationMemberPublic } from '@/types/api'
import { PropertyPills } from '../[taskId]/components/PropertyPills'
import { CommentInput } from '../[taskId]/components/CommentInput'
import { ActivityTimeline } from '../[taskId]/components/ActivityTimeline'
import { SignalReviewPanel } from '../[taskId]/components/SignalReviewPanel'
import { ReviewStatusBar } from '../[taskId]/components/ReviewStatusBar'
import { ProcessingResultsCard } from '@/components/workspace/chat/ProcessingResultsCard'

interface TaskDetailPanelProps {
  taskId: string | null
  onTaskUpdated: () => void
}

export function TaskDetailPanel({ taskId, onTaskUpdated }: TaskDetailPanelProps) {
  const router = useRouter()
  const { data: profile } = useProfile()
  const { data: task, mutate: mutateTask } = useTaskDetail(taskId || '')
  const { data: commentsData, mutate: mutateComments } = useTaskComments(taskId || '')

  const [editingTitle, setEditingTitle] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')
  const [descDraft, setDescDraft] = useState('')
  const [descDirty, setDescDirty] = useState(false)
  const [activities, setActivities] = useState<TaskActivity[]>([])
  const [members, setMembers] = useState<OrganizationMemberPublic[]>([])
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)

  // Reset editing state when task changes
  useEffect(() => {
    setEditingTitle(false)
    setDescDirty(false)
    setShowDeleteConfirm(false)
  }, [taskId])

  // Load activities
  useEffect(() => {
    if (task && taskId) {
      getProjectTaskActivity(task.project_id, { limit: 50 })
        .then((res) => {
          setActivities(res.activities.filter((a) => a.task_id === taskId))
        })
        .catch(() => {})
    }
  }, [task, taskId])

  // Load org members
  useEffect(() => {
    listOrganizations()
      .then((orgs) => {
        if (orgs.length > 0) return listOrganizationMembers(orgs[0].id)
        return []
      })
      .then(setMembers)
      .catch(() => {})
  }, [])

  // Sync description
  useEffect(() => {
    if (task && !descDirty) {
      setDescDraft(task.description || '')
    }
  }, [task, descDirty])

  const saveTitle = useCallback(async () => {
    if (!task || !titleDraft.trim() || titleDraft === task.title) {
      setEditingTitle(false)
      return
    }
    await updateTask(task.project_id, task.id, { title: titleDraft.trim() })
    mutateTask()
    onTaskUpdated()
    setEditingTitle(false)
  }, [task, titleDraft, mutateTask, onTaskUpdated])

  const saveDescription = useCallback(async () => {
    if (!task || descDraft === (task.description || '')) {
      setDescDirty(false)
      return
    }
    await updateTask(task.project_id, task.id, { description: descDraft })
    mutateTask()
    onTaskUpdated()
    setDescDirty(false)
  }, [task, descDraft, mutateTask, onTaskUpdated])

  const handleComment = async (body: string) => {
    if (!taskId) return
    await createTaskComment(taskId, body)
    mutateComments()
    if (task) {
      getProjectTaskActivity(task.project_id, { limit: 50 })
        .then((res) => setActivities(res.activities.filter((a) => a.task_id === taskId)))
        .catch(() => {})
    }
  }

  const handleDeleteComment = async (commentId: string) => {
    if (!taskId) return
    await deleteTaskComment(taskId, commentId)
    mutateComments()
  }

  const handleDeleteTask = async () => {
    if (!task) return
    await deleteTask(task.project_id, task.id)
    onTaskUpdated()
  }

  const handleReopenTask = async () => {
    if (!task) return
    await reopenTask(task.project_id, task.id)
    mutateTask()
    onTaskUpdated()
  }

  const handleCompleteTask = async () => {
    if (!task) return
    await completeTask(task.project_id, task.id, { completion_method: 'task_board' })
    mutateTask()
    onTaskUpdated()
  }

  // Empty state — gentle prompt with subtle animation
  if (!taskId) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center px-8 py-20">
        {/* Animated rings */}
        <div className="relative w-16 h-16 mb-5">
          <div className="absolute inset-0 rounded-full border-2 border-brand-primary/10 animate-ping" style={{ animationDuration: '3s' }} />
          <div className="absolute inset-2 rounded-full border-2 border-brand-primary/15 animate-ping" style={{ animationDuration: '3s', animationDelay: '0.5s' }} />
          <div className="absolute inset-0 rounded-full bg-brand-primary-light flex items-center justify-center">
            <ClipboardList className="w-6 h-6 text-brand-primary" />
          </div>
        </div>
        <p className="text-[15px] font-medium text-[#333] mb-1">No task selected</p>
        <p className="text-[12px] text-[#999] max-w-[200px] leading-relaxed">
          Click a task on the left to view details, add comments, and manage properties
        </p>
      </div>
    )
  }

  // Loading state
  if (!task) {
    return (
      <div className="flex items-center justify-center h-full py-20">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-primary" />
      </div>
    )
  }

  return (
    <div className="px-5 py-4">
      {/* Action bar — icons left, complete/reopen right */}
      <div className="flex items-center gap-1 mb-3">
        <button
          onClick={() => setShowDeleteConfirm(true)}
          className="p-1.5 text-[#CCC] hover:text-red-500 hover:bg-red-50 rounded-md transition-colors"
          title="Delete task"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={() => router.push(`/tasks/${task.id}`)}
          className="p-1.5 text-[#CCC] hover:text-[#666] hover:bg-[#F4F4F4] rounded-md transition-colors"
          title="Open full page"
        >
          <ExternalLink className="w-3.5 h-3.5" />
        </button>
        <div className="flex-1" />
        {task.status !== 'completed' && task.status !== 'dismissed' && (
          <button
            onClick={handleCompleteTask}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-brand-primary hover:bg-brand-primary-light rounded-md transition-colors"
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            Mark complete
          </button>
        )}
        {(task.status === 'completed' || task.status === 'dismissed') && (
          <button
            onClick={handleReopenTask}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-[#999] hover:text-[#333] hover:bg-[#F4F4F4] rounded-md transition-colors"
          >
            <RotateCcw className="w-3 h-3" />
            Reopen
          </button>
        )}
      </div>

      {/* Editable title */}
      {editingTitle ? (
        <input
          autoFocus
          value={titleDraft}
          onChange={(e) => setTitleDraft(e.target.value)}
          onBlur={saveTitle}
          onKeyDown={(e) => { if (e.key === 'Enter') saveTitle(); if (e.key === 'Escape') setEditingTitle(false) }}
          className="text-[20px] font-semibold text-[#0A1E2F] w-full outline-none border-b-2 border-brand-primary bg-transparent mb-3 pb-1"
        />
      ) : (
        <h2
          onClick={() => { setTitleDraft(task.title); setEditingTitle(true) }}
          className="text-[20px] font-semibold text-[#0A1E2F] mb-3 cursor-text hover:text-[#25785A] transition-colors"
        >
          {task.title}
        </h2>
      )}

      {/* Property pills */}
      <PropertyPills
        task={task}
        members={members}
        onUpdate={() => { mutateTask(); onTaskUpdated() }}
      />

      {/* Description */}
      <div className="mb-5">
        <textarea
          value={descDraft}
          onChange={(e) => { setDescDraft(e.target.value); setDescDirty(true) }}
          onBlur={saveDescription}
          placeholder="Add a description..."
          rows={3}
          className="w-full text-[13px] text-[#333] placeholder-[#CCC] outline-none border border-border rounded-lg p-3 resize-none focus:border-brand-primary transition-colors"
        />
      </div>

      {/* Type-specific sections */}
      {task.task_type === 'signal_review' && task.signal_id && (
        <div className="mb-4">
          <ProcessingResultsCard
            signalId={task.signal_id}
            projectId={task.project_id}
            filename={task.title.replace(/^Review \d+ entities from /, '')}
            onConfirmed={() => { mutateTask(); onTaskUpdated() }}
          />
        </div>
      )}
      {task.task_type === 'signal_review' && !task.signal_id && task.patches_snapshot && (
        <SignalReviewPanel patches={task.patches_snapshot as Record<string, unknown>} />
      )}
      {task.task_type === 'review_request' && (
        <ReviewStatusBar
          status={task.review_status || null}
          projectId={task.project_id}
          taskId={task.id}
          onUpdate={() => { mutateTask(); onTaskUpdated() }}
        />
      )}
      {(task.task_type === 'meeting_prep' || task.task_type === 'book_meeting') && task.meeting_type && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-[12px] font-medium uppercase tracking-wide text-[#999]">Meeting Type</span>
          <span className="text-[13px] px-2 py-0.5 bg-[#0A1E2F]/5 text-[#0A1E2F] rounded capitalize">
            {task.meeting_type.replace(/_/g, ' ')}
          </span>
          {task.meeting_date && (
            <span className="text-[13px] text-[#666]">
              {new Date(task.meeting_date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
            </span>
          )}
        </div>
      )}
      {task.task_type === 'reminder' && task.remind_at && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-[12px] font-medium uppercase tracking-wide text-[#999]">Remind At</span>
          <span className="text-[13px] text-[#333]">
            {new Date(task.remind_at).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
          </span>
        </div>
      )}
      {task.task_type === 'action_item' && task.action_verb && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-[12px] font-medium uppercase tracking-wide text-[#999]">Action</span>
          <span className="text-[13px] px-2 py-0.5 bg-brand-primary-light text-[#25785A] rounded capitalize">
            {task.action_verb.replace(/_/g, ' ')}
          </span>
        </div>
      )}

      {/* Divider */}
      <div className="border-t border-border mb-4" />

      {/* Comment input */}
      <CommentInput
        avatarUrl={profile?.photo_url}
        onSubmit={handleComment}
      />

      {/* Activity timeline */}
      <div className="mt-2">
        <h3 className="text-[12px] font-semibold uppercase tracking-wide text-[#999] mb-3">Activity</h3>
        <ActivityTimeline
          comments={commentsData?.comments || []}
          activities={activities}
          onDeleteComment={handleDeleteComment}
          currentUserId={profile?.id}
        />
      </div>

      {/* Delete confirmation modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setShowDeleteConfirm(false)} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-sm mx-4 p-6">
            <h3 className="text-[16px] font-semibold text-[#333] mb-2">Delete this task?</h3>
            <p className="text-[13px] text-[#666] mb-6">This will permanently remove this task and its comments.</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setShowDeleteConfirm(false)} className="px-4 py-2 text-[13px] font-medium text-[#666] bg-[#F0F0F0] rounded-xl hover:bg-border transition-colors">Cancel</button>
              <button onClick={() => { setShowDeleteConfirm(false); handleDeleteTask() }} className="px-4 py-2 text-[13px] font-medium text-white bg-red-600 rounded-xl hover:bg-red-700 transition-colors">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
