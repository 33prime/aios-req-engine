'use client'

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { createTask, listProjects, listOrganizations, listOrganizationMembers } from '@/lib/api'
import { AssigneePicker } from '@/components/tasks/AssigneePicker'
import type { TaskTypeValue, MeetingTypeValue, ActionVerbValue } from '@/lib/api/tasks'
import type { OrganizationMemberPublic } from '@/types/api'

interface AddTaskModalProps {
  open: boolean
  onClose: () => void
  onCreated: () => void
}

const PRIORITIES = [
  { value: 'none', label: 'None', color: '#E5E5E5' },
  { value: 'low', label: 'Low', color: '#E5E5E5' },
  { value: 'medium', label: 'Medium', color: '#3FAF7A' },
  { value: 'high', label: 'High', color: '#25785A' },
]

const TASK_TYPES: { value: TaskTypeValue; label: string }[] = [
  { value: 'custom', label: 'Custom' },
  { value: 'action_item', label: 'Action Item' },
  { value: 'meeting_prep', label: 'Meeting Prep' },
  { value: 'book_meeting', label: 'Book Meeting' },
  { value: 'reminder', label: 'Reminder' },
  { value: 'review_request', label: 'Review Request' },
  { value: 'deliverable', label: 'Deliverable' },
]

const MEETING_TYPES = [
  { value: 'discovery', label: 'Discovery' },
  { value: 'event_modeling', label: 'Event Modeling' },
  { value: 'proposal', label: 'Proposal' },
  { value: 'prototype_review', label: 'Prototype Review' },
  { value: 'kickoff', label: 'Kickoff' },
  { value: 'stakeholder_interview', label: 'Stakeholder Interview' },
  { value: 'technical_deep_dive', label: 'Technical Deep Dive' },
  { value: 'internal_strategy', label: 'Internal Strategy' },
  { value: 'introduction', label: 'Introduction' },
  { value: 'monthly_check_in', label: 'Monthly Check-in' },
  { value: 'hand_off', label: 'Hand Off' },
]

const ACTION_VERBS = [
  { value: 'send', label: 'Send' },
  { value: 'email', label: 'Email' },
  { value: 'schedule', label: 'Schedule' },
  { value: 'prepare', label: 'Prepare' },
  { value: 'review', label: 'Review' },
  { value: 'follow_up', label: 'Follow Up' },
  { value: 'share', label: 'Share' },
  { value: 'create', label: 'Create' },
]

const selectClass = 'text-[13px] px-3 py-1.5 rounded-md border border-[#E5E5E5] bg-white text-[#333] outline-none focus:border-[#3FAF7A] transition-colors'

export function AddTaskModal({ open, onClose, onCreated }: AddTaskModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [taskType, setTaskType] = useState<TaskTypeValue>('custom')
  const [priority, setPriority] = useState('none')
  const [assignedTo, setAssignedTo] = useState<string | undefined>()
  const [dueDate, setDueDate] = useState('')
  const [projectId, setProjectId] = useState('')
  const [meetingType, setMeetingType] = useState('')
  const [meetingDate, setMeetingDate] = useState('')
  const [remindAt, setRemindAt] = useState('')
  const [actionVerb, setActionVerb] = useState('')
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([])
  const [members, setMembers] = useState<OrganizationMemberPublic[]>([])
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (open) {
      listProjects('active')
        .then((res) => {
          const list = res.projects.map((p) => ({ id: p.id, name: p.name }))
          setProjects(list)
          if (list.length === 1) setProjectId(list[0].id)
        })
        .catch(() => {})

      // Load org members for assignee picker
      listOrganizations()
        .then((orgs) => {
          if (orgs.length > 0) {
            return listOrganizationMembers(orgs[0].id)
          }
          return []
        })
        .then(setMembers)
        .catch(() => {})
    }
  }, [open])

  const resetForm = () => {
    setTitle('')
    setDescription('')
    setTaskType('custom')
    setPriority('none')
    setAssignedTo(undefined)
    setDueDate('')
    setMeetingType('')
    setMeetingDate('')
    setRemindAt('')
    setActionVerb('')
  }

  const handleSubmit = async () => {
    if (!title.trim() || !projectId) return
    setSaving(true)
    try {
      await createTask(projectId, {
        title: title.trim(),
        description: description.trim() || undefined,
        task_type: taskType,
        priority,
        assigned_to: assignedTo,
        due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
        meeting_type: (taskType === 'meeting_prep' || taskType === 'book_meeting') && meetingType ? meetingType as MeetingTypeValue : undefined,
        meeting_date: (taskType === 'meeting_prep' || taskType === 'book_meeting') && meetingDate ? new Date(meetingDate).toISOString() : undefined,
        remind_at: taskType === 'reminder' && remindAt ? new Date(remindAt).toISOString() : undefined,
        action_verb: taskType === 'action_item' && actionVerb ? actionVerb as ActionVerbValue : undefined,
      })
      resetForm()
      onCreated()
      onClose()
    } catch (err) {
      console.error('Failed to create task:', err)
    } finally {
      setSaving(false)
    }
  }

  const showMeetingFields = taskType === 'meeting_prep' || taskType === 'book_meeting'
  const showRemindAt = taskType === 'reminder'
  const showActionVerb = taskType === 'action_item'

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#E5E5E5]">
          <h2 className="text-[15px] font-semibold text-[#0A1E2F]">Add task</h2>
          <button onClick={onClose} className="text-[#999] hover:text-[#333] transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          {/* Type selector */}
          <div className="flex flex-wrap gap-1.5">
            {TASK_TYPES.map((t) => (
              <button
                key={t.value}
                onClick={() => setTaskType(t.value)}
                className={`px-2.5 py-1 text-[12px] rounded-md font-medium transition-colors ${
                  taskType === t.value
                    ? 'bg-[#3FAF7A]/10 text-[#25785A] border border-[#3FAF7A]/30'
                    : 'bg-[#F4F4F4] text-[#666] border border-transparent hover:border-[#E5E5E5]'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {/* Title */}
          <input
            autoFocus
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Task title"
            className="w-full text-[15px] text-[#333] placeholder-[#CCC] outline-none border-b border-[#E5E5E5] pb-2 focus:border-[#3FAF7A] transition-colors"
          />

          {/* Description */}
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Add description..."
            rows={3}
            className="w-full text-[13px] text-[#333] placeholder-[#CCC] outline-none border border-[#E5E5E5] rounded-lg p-2.5 resize-none focus:border-[#3FAF7A] transition-colors"
          />

          {/* Type-specific fields */}
          {showMeetingFields && (
            <div className="flex gap-2">
              <select value={meetingType} onChange={(e) => setMeetingType(e.target.value)} className={selectClass}>
                <option value="">Meeting type...</option>
                {MEETING_TYPES.map((m) => (
                  <option key={m.value} value={m.value}>{m.label}</option>
                ))}
              </select>
              <input
                type="datetime-local"
                value={meetingDate}
                onChange={(e) => setMeetingDate(e.target.value)}
                className={selectClass}
                placeholder="Meeting date"
              />
            </div>
          )}

          {showRemindAt && (
            <div>
              <label className="block text-[12px] text-[#999] mb-1">Remind at</label>
              <input
                type="datetime-local"
                value={remindAt}
                onChange={(e) => setRemindAt(e.target.value)}
                className={selectClass}
              />
            </div>
          )}

          {showActionVerb && (
            <select value={actionVerb} onChange={(e) => setActionVerb(e.target.value)} className={selectClass}>
              <option value="">Action verb...</option>
              {ACTION_VERBS.map((v) => (
                <option key={v.value} value={v.value}>{v.label}</option>
              ))}
            </select>
          )}

          {/* Property pills */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Project picker */}
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className={selectClass}
            >
              <option value="">Select project...</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>

            {/* Priority */}
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className={selectClass}
            >
              {PRIORITIES.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </select>

            {/* Assignee */}
            <AssigneePicker
              members={members}
              selectedUserId={assignedTo}
              onChange={setAssignedTo}
              compact
            />

            {/* Due date */}
            <input
              type="date"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
              className={selectClass}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 px-5 py-3 border-t border-[#E5E5E5]">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-[13px] text-[#666] hover:text-[#333] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || !projectId || saving}
            className="px-4 py-1.5 text-[13px] font-medium rounded-lg bg-[#3FAF7A] text-white hover:bg-[#25785A] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? 'Adding...' : 'Add'}
          </button>
        </div>
      </div>
    </div>
  )
}
