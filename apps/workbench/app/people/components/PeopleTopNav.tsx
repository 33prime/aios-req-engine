'use client'

import { Search, Filter, Plus, RefreshCw } from 'lucide-react'

interface PeopleTopNavProps {
  searchQuery: string
  typeFilter: string
  influenceFilter: string
  projectFilter: string
  projects: { id: string; name: string }[]
  onSearchChange: (value: string) => void
  onTypeFilterChange: (value: string) => void
  onInfluenceFilterChange: (value: string) => void
  onProjectFilterChange: (value: string) => void
  onRefresh: () => void
  onCreatePerson: () => void
}

export function PeopleTopNav({
  searchQuery,
  typeFilter,
  influenceFilter,
  projectFilter,
  projects,
  onSearchChange,
  onTypeFilterChange,
  onInfluenceFilterChange,
  onProjectFilterChange,
  onRefresh,
  onCreatePerson,
}: PeopleTopNavProps) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-[22px] font-bold text-[#37352f]">People</h1>
          <p className="text-[13px] text-[#999999] mt-0.5">
            Stakeholders across all projects
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-gray-500 bg-white border border-gray-200 rounded-md hover:bg-gray-50 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button
            onClick={onCreatePerson}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-white bg-[#009b87] rounded-md hover:bg-[#008474] transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Person
          </button>
        </div>
      </div>

      {/* Filters row */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px] max-w-[320px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name or email..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87] focus:border-[#009b87]"
          />
        </div>

        {/* Type filter */}
        <select
          value={typeFilter}
          onChange={(e) => onTypeFilterChange(e.target.value)}
          className="px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
        >
          <option value="all">All Types</option>
          <option value="champion">Champion</option>
          <option value="sponsor">Sponsor</option>
          <option value="blocker">Blocker</option>
          <option value="influencer">Influencer</option>
          <option value="end_user">End User</option>
        </select>

        {/* Influence filter */}
        <select
          value={influenceFilter}
          onChange={(e) => onInfluenceFilterChange(e.target.value)}
          className="px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
        >
          <option value="all">All Influence</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>

        {/* Project filter */}
        <select
          value={projectFilter}
          onChange={(e) => onProjectFilterChange(e.target.value)}
          className="px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-[#009b87]"
        >
          <option value="all">All Projects</option>
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>
    </div>
  )
}
