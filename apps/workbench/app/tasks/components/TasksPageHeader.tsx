'use client'

import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Plus } from 'lucide-react'

interface TasksPageHeaderProps {
  view: 'assigned_to_me' | 'created_by_me' | 'all'
  counts: Record<string, number>
  onViewChange: (view: 'assigned_to_me' | 'created_by_me' | 'all') => void
  onAddTask: () => void
}

const VIEW_LABELS: Record<string, string> = {
  assigned_to_me: 'Assigned to me',
  created_by_me: 'Created by me',
  all: 'All tasks',
}

export function TasksPageHeader({ view, counts, onViewChange, onAddTask }: TasksPageHeaderProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setShowDropdown(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const totalActive = (counts.pending || 0) + (counts.in_progress || 0)

  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-3">
        <h1 className="text-[22px] font-semibold text-[#0A1E2F]">Tasks</h1>

        {/* View dropdown pill */}
        <div ref={ref} className="relative">
          <button
            onClick={() => setShowDropdown(!showDropdown)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#F4F4F4] text-[13px] text-[#333] hover:bg-[#EEEEEE] transition-colors"
          >
            <span>{VIEW_LABELS[view]}</span>
            {totalActive > 0 && (
              <span className="text-[11px] font-medium text-[#3FAF7A]">{totalActive}</span>
            )}
            <ChevronDown className="w-3 h-3 text-[#999]" />
          </button>

          {showDropdown && (
            <div className="absolute z-50 top-full mt-1 left-0 w-48 bg-white border border-[#E5E5E5] rounded-lg shadow-lg py-1">
              {Object.entries(VIEW_LABELS).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => { onViewChange(key as typeof view); setShowDropdown(false) }}
                  className={`w-full text-left px-3 py-2 text-[13px] hover:bg-[#F4F4F4] transition-colors ${
                    key === view ? 'text-[#3FAF7A] font-medium' : 'text-[#333]'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Add task button */}
      <button
        onClick={onAddTask}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#3FAF7A] text-white text-[13px] font-medium hover:bg-[#25785A] transition-colors"
      >
        <Plus className="w-3.5 h-3.5" />
        Add task
      </button>
    </div>
  )
}
