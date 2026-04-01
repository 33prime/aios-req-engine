'use client'

import { Search, RefreshCw, Plus, List, LayoutGrid } from 'lucide-react'

interface ClientsTopNavProps {
  searchQuery: string
  industryFilter: string
  viewMode: 'cards' | 'table'
  sortField: string
  onSearchChange: (value: string) => void
  onIndustryFilterChange: (value: string) => void
  onRefresh: () => void
  onCreateClient: () => void
  onViewModeChange: (mode: 'cards' | 'table') => void
  onSortChange: (field: string) => void
}

const INDUSTRIES = [
  'All Industries',
  'Technology',
  'Healthcare',
  'Finance',
  'Manufacturing',
  'Retail',
  'Education',
  'Real Estate',
  'Construction',
  'Professional Services',
  'Government',
  'Non-Profit',
]

const SORT_OPTIONS = [
  { value: 'name', label: 'Name' },
  { value: 'project_count', label: 'Projects' },
  { value: 'stakeholder_count', label: 'Stakeholders' },
  { value: 'profile_completeness', label: 'Completeness' },
]

export function ClientsTopNav({
  searchQuery,
  industryFilter,
  viewMode,
  sortField,
  onSearchChange,
  onIndustryFilterChange,
  onRefresh,
  onCreateClient,
  onViewModeChange,
  onSortChange,
}: ClientsTopNavProps) {
  const currentSort = SORT_OPTIONS.find(o => o.value === sortField)

  return (
    <div className="flex items-center justify-between gap-3 mb-4">
      <div className="flex items-center gap-3 flex-1">
        {/* Search */}
        <div className="relative flex-1 max-w-[320px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[#999]" />
          <input
            type="text"
            placeholder="Search clients..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-[13px] bg-white border border-border rounded-xl focus:outline-none focus:border-brand-primary focus:ring-1 focus:ring-brand-primary/20 transition-colors"
          />
        </div>

        {/* Industry filter */}
        <select
          value={industryFilter}
          onChange={(e) => onIndustryFilterChange(e.target.value)}
          className="px-3 py-2 text-[13px] bg-white border border-border rounded-xl focus:outline-none focus:border-brand-primary transition-colors appearance-none cursor-pointer"
        >
          {INDUSTRIES.map((ind) => (
            <option key={ind} value={ind === 'All Industries' ? 'all' : ind}>
              {ind}
            </option>
          ))}
        </select>

        {/* Sort */}
        <select
          value={sortField}
          onChange={(e) => onSortChange(e.target.value)}
          className="px-3 py-2 text-[13px] bg-white border border-border rounded-xl focus:outline-none focus:border-brand-primary transition-colors appearance-none cursor-pointer"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* Refresh */}
        <button
          onClick={onRefresh}
          className="p-2 text-[#999] hover:text-[#666] hover:bg-[#F0F0F0] rounded-xl transition-colors"
          title="Refresh"
        >
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex items-center gap-2">
        {/* View toggle */}
        <div className="flex items-center bg-[#F0F0F0] rounded-lg p-0.5">
          <button
            onClick={() => onViewModeChange('table')}
            className={`p-1.5 rounded-md transition-all ${viewMode === 'table' ? 'bg-white shadow-sm' : 'hover:bg-white/50'}`}
            title="Table view"
          >
            <List className="w-3.5 h-3.5 text-[#666]" />
          </button>
          <button
            onClick={() => onViewModeChange('cards')}
            className={`p-1.5 rounded-md transition-all ${viewMode === 'cards' ? 'bg-white shadow-sm' : 'hover:bg-white/50'}`}
            title="Cards view"
          >
            <LayoutGrid className="w-3.5 h-3.5 text-[#666]" />
          </button>
        </div>

        {/* Add Client */}
        <button
          onClick={onCreateClient}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-white bg-brand-primary rounded-xl hover:bg-[#25785A] transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Add Client
        </button>
      </div>
    </div>
  )
}
