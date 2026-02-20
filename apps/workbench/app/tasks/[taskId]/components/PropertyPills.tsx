'use client'

import { useState, useRef, useEffect } from 'react'
import { Circle, CheckCircle2, Calendar, Flag, User } from 'lucide-react'
import { updateTask } from '@/lib/api'
import { AssigneePicker } from '@/components/tasks/AssigneePicker'
import type { TaskWithProject } from '@/lib/api'
import type { OrganizationMemberPublic } from '@/types/api'

const STATUSES = [
  { value: 'pending', label: 'Pending', icon: Circle },
  { value: 'in_progress', label: 'In progress', icon: Circle },
  { value: 'completed', label: 'Completed', icon: CheckCircle2 },
]

const PRIORITIES = [
  { value: 'none', label: 'None', color: '#E5E5E5' },
  { value: 'low', label: 'Low', color: '#E5E5E5' },
  { value: 'medium', label: 'Medium', color: '#3FAF7A' },
  { value: 'high', label: 'High', color: '#25785A' },
]

interface PropertyPillsProps {
  task: TaskWithProject
  members: OrganizationMemberPublic[]
  onUpdate: () => void
}

export function PropertyPills({ task, members, onUpdate }: PropertyPillsProps) {
  const [editingField, setEditingField] = useState<string | null>(null)

  const handleUpdate = async (data: Record<string, string | undefined>) => {
    try {
      await updateTask(task.project_id, task.id, data)
      onUpdate()
    } catch (err) {
      console.error('Failed to update task:', err)
    }
    setEditingField(null)
  }

  return (
    <div className="flex flex-wrap items-center gap-2 mb-6">
      {/* Status pill */}
      <PillDropdown
        label={task.status.replace('_', ' ')}
        icon={task.status === 'completed' ? <CheckCircle2 className="w-3.5 h-3.5 text-[#3FAF7A]" /> : <Circle className="w-3.5 h-3.5 text-[#999]" />}
        isOpen={editingField === 'status'}
        onToggle={() => setEditingField(editingField === 'status' ? null : 'status')}
        onClose={() => setEditingField(null)}
      >
        {STATUSES.map((s) => (
          <button
            key={s.value}
            onClick={() => handleUpdate({ status: s.value })}
            className={`w-full text-left px-3 py-2 text-[13px] hover:bg-[#F4F4F4] ${
              s.value === task.status ? 'text-[#3FAF7A] font-medium' : 'text-[#333]'
            }`}
          >
            {s.label}
          </button>
        ))}
      </PillDropdown>

      {/* Priority pill */}
      <PillDropdown
        label={task.priority || 'None'}
        icon={<Flag className="w-3.5 h-3.5" style={{ color: PRIORITIES.find(p => p.value === task.priority)?.color || '#E5E5E5' }} />}
        isOpen={editingField === 'priority'}
        onToggle={() => setEditingField(editingField === 'priority' ? null : 'priority')}
        onClose={() => setEditingField(null)}
      >
        {PRIORITIES.map((p) => (
          <button
            key={p.value}
            onClick={() => handleUpdate({ priority: p.value })}
            className={`w-full text-left px-3 py-2 text-[13px] hover:bg-[#F4F4F4] flex items-center gap-2 ${
              p.value === task.priority ? 'text-[#3FAF7A] font-medium' : 'text-[#333]'
            }`}
          >
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            {p.label}
          </button>
        ))}
      </PillDropdown>

      {/* Assignee pill */}
      <AssigneePicker
        members={members}
        selectedUserId={task.assigned_to}
        onChange={(userId) => handleUpdate({ assigned_to: userId })}
        compact
      />

      {/* Due date pill */}
      <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#E5E5E5] bg-white text-[13px]">
        <Calendar className="w-3.5 h-3.5 text-[#999]" />
        <input
          type="date"
          value={task.due_date ? new Date(task.due_date).toISOString().split('T')[0] : ''}
          onChange={(e) => handleUpdate({ due_date: e.target.value ? new Date(e.target.value).toISOString() : undefined })}
          className="outline-none bg-transparent text-[#333] text-[13px]"
        />
      </div>

      {/* Project badge (read-only) */}
      <span className="px-2.5 py-1 text-[12px] bg-[#F4F4F4] text-[#666] rounded-md">
        {task.project_name}
      </span>
    </div>
  )
}

// --- Pill Dropdown Primitive ---

function PillDropdown({
  label,
  icon,
  isOpen,
  onToggle,
  onClose,
  children,
}: {
  label: string
  icon: React.ReactNode
  isOpen: boolean
  onToggle: () => void
  onClose: () => void
  children: React.ReactNode
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    if (isOpen) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isOpen, onClose])

  return (
    <div ref={ref} className="relative">
      <button
        onClick={onToggle}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-[#E5E5E5] bg-white hover:border-[#3FAF7A] transition-colors text-[13px] text-[#333] capitalize"
      >
        {icon}
        {label}
      </button>
      {isOpen && (
        <div className="absolute z-50 top-full mt-1 left-0 w-40 bg-white border border-[#E5E5E5] rounded-lg shadow-lg py-1">
          {children}
        </div>
      )}
    </div>
  )
}
