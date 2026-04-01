'use client'

import { List, LayoutGrid } from 'lucide-react'

interface ViewToggleProps {
  viewMode: 'list' | 'kanban'
  onViewModeChange: (mode: 'list' | 'kanban') => void
}

export function ViewToggle({ viewMode, onViewModeChange }: ViewToggleProps) {
  return (
    <div className="flex items-center gap-0.5 p-0.5 bg-gray-100 rounded-lg">
      <button
        onClick={() => onViewModeChange('list')}
        className={`p-1.5 rounded-md transition-colors ${
          viewMode === 'list' ? 'bg-white text-brand-primary shadow-sm' : 'text-text-placeholder hover:text-text-body'
        }`}
        title="List view"
      >
        <List className="w-4 h-4" />
      </button>
      <button
        onClick={() => onViewModeChange('kanban')}
        className={`p-1.5 rounded-md transition-colors ${
          viewMode === 'kanban' ? 'bg-white text-brand-primary shadow-sm' : 'text-text-placeholder hover:text-text-body'
        }`}
        title="Board view"
      >
        <LayoutGrid className="w-4 h-4" />
      </button>
    </div>
  )
}
