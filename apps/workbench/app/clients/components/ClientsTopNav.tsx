'use client'

import { Search, RefreshCw, Plus } from 'lucide-react'

interface ClientsTopNavProps {
  searchQuery: string
  industryFilter: string
  onSearchChange: (value: string) => void
  onIndustryFilterChange: (value: string) => void
  onRefresh: () => void
  onCreateClient: () => void
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

export function ClientsTopNav({
  searchQuery,
  industryFilter,
  onSearchChange,
  onIndustryFilterChange,
  onRefresh,
  onCreateClient,
}: ClientsTopNavProps) {
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
            className="w-full pl-9 pr-3 py-2 text-[13px] bg-white border border-[#E5E5E5] rounded-xl focus:outline-none focus:border-[#3FAF7A] focus:ring-1 focus:ring-[#3FAF7A]/20 transition-colors"
          />
        </div>

        {/* Industry filter */}
        <select
          value={industryFilter}
          onChange={(e) => onIndustryFilterChange(e.target.value)}
          className="px-3 py-2 text-[13px] bg-white border border-[#E5E5E5] rounded-xl focus:outline-none focus:border-[#3FAF7A] transition-colors appearance-none cursor-pointer"
        >
          {INDUSTRIES.map((ind) => (
            <option key={ind} value={ind === 'All Industries' ? 'all' : ind}>
              {ind}
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

      {/* Add Client */}
      <button
        onClick={onCreateClient}
        className="inline-flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
      >
        <Plus className="w-3.5 h-3.5" />
        Add Client
      </button>
    </div>
  )
}
