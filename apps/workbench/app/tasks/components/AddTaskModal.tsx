'use client'

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { createTask, listProjects, listOrganizations, listOrganizationMembers } from '@/lib/api'
import { AssigneePicker } from '@/components/tasks/AssigneePicker'
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

export function AddTaskModal({ open, onClose, onCreated }: AddTaskModalProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('none')
  const [assignedTo, setAssignedTo] = useState<string | undefined>()
  const [dueDate, setDueDate] = useState('')
  const [projectId, setProjectId] = useState('')
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

  const handleSubmit = async () => {
    if (!title.trim() || !projectId) return
    setSaving(true)
    try {
      await createTask(projectId, {
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
        assigned_to: assignedTo,
        due_date: dueDate ? new Date(dueDate).toISOString() : undefined,
      })
      // Reset form
      setTitle('')
      setDescription('')
      setPriority('none')
      setAssignedTo(undefined)
      setDueDate('')
      onCreated()
      onClose()
    } catch (err) {
      console.error('Failed to create task:', err)
    } finally {
      setSaving(false)
    }
  }

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

          {/* Property pills */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Project picker */}
            <select
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="text-[13px] px-3 py-1.5 rounded-md border border-[#E5E5E5] bg-white text-[#333] outline-none focus:border-[#3FAF7A] transition-colors"
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
              className="text-[13px] px-3 py-1.5 rounded-md border border-[#E5E5E5] bg-white text-[#333] outline-none focus:border-[#3FAF7A] transition-colors"
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
              className="text-[13px] px-3 py-1.5 rounded-md border border-[#E5E5E5] bg-white text-[#333] outline-none focus:border-[#3FAF7A] transition-colors"
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
