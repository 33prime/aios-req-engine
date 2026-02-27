'use client'

import { Search, RefreshCw, Plus, Calendar } from 'lucide-react'

export type MeetingTab = 'upcoming' | 'past' | 'recorded'

interface MeetingsTopNavProps {
  activeTab: MeetingTab
  counts: { upcoming: number; past: number; recorded: number }
  searchQuery: string
  typeFilter: string
  projectFilter: string
  projects: { id: string; name: string }[]
  viewMode: 'table' | 'cards'
  onTabChange: (tab: MeetingTab) => void
  onSearchChange: (value: string) => void
  onTypeFilterChange: (value: string) => void
  onProjectFilterChange: (value: string) => void
  onViewModeChange: (mode: 'table' | 'cards') => void
  onRefresh: () => void
  onCreateMeeting: () => void
}

export function MeetingsTopNav({
  activeTab,
  counts,
  searchQuery,
  typeFilter,
  projectFilter,
  projects,
  viewMode,
  onTabChange,
  onSearchChange,
  onTypeFilterChange,
  onProjectFilterChange,
  onViewModeChange,
  onRefresh,
  onCreateMeeting,
}: MeetingsTopNavProps) {
  const tabs: { key: MeetingTab; label: string; count: number; dot?: boolean }[] = [
    { key: 'upcoming', label: 'Upcoming', count: counts.upcoming },
    { key: 'past', label: 'Past', count: counts.past },
    { key: 'recorded', label: 'Recorded', count: counts.recorded, dot: true },
  ]

  return (
    <div className="mb-4">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-[22px] font-bold text-[#37352f]">Meetings</h1>
          <p className="text-[13px] text-text-placeholder mt-0.5">
            Discovery sessions, reviews, and stakeholder calls
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
            onClick={onCreateMeeting}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-white bg-brand-primary rounded-md hover:bg-[#25785A] transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            New Meeting
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center justify-between border-b border-gray-200 mb-4">
        <div className="flex gap-0">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => onTabChange(tab.key)}
              className={`
                flex items-center gap-2 px-4 py-2.5 text-[13px] font-medium border-b-2 transition-colors
                ${activeTab === tab.key
                  ? 'text-text-primary border-brand-primary'
                  : 'text-text-placeholder border-transparent hover:text-[#666]'
                }
              `}
            >
              {tab.dot && (
                <span className="w-[6px] h-[6px] rounded-full bg-brand-primary" />
              )}
              {tab.label}
              <span
                className={`text-[11px] font-semibold px-1.5 py-0.5 rounded-full ${
                  activeTab === tab.key
                    ? 'bg-[#E8F5E9] text-[#25785A]'
                    : 'bg-gray-100 text-text-placeholder'
                }`}
              >
                {tab.count}
              </span>
            </button>
          ))}
        </div>

        {/* View toggle */}
        <div className="flex items-center gap-1 bg-gray-100 p-0.5 rounded-md mb-0.5">
          <button
            onClick={() => onViewModeChange('table')}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              viewMode === 'table'
                ? 'bg-white text-text-primary shadow-[0_1px_2px_rgba(0,0,0,0.06)]'
                : 'text-text-placeholder hover:text-[#666]'
            }`}
          >
            Table
          </button>
          <button
            onClick={() => onViewModeChange('cards')}
            className={`px-2.5 py-1 rounded text-[11px] font-medium transition-colors ${
              viewMode === 'cards'
                ? 'bg-white text-text-primary shadow-[0_1px_2px_rgba(0,0,0,0.06)]'
                : 'text-text-placeholder hover:text-[#666]'
            }`}
          >
            Cards
          </button>
        </div>
      </div>

      {/* Filters row */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px] max-w-[320px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
          <input
            type="text"
            placeholder="Search meetings..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-primary focus:border-brand-primary"
          />
        </div>

        <select
          value={typeFilter}
          onChange={(e) => onTypeFilterChange(e.target.value)}
          className="px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-primary"
        >
          <option value="all">All Types</option>
          <option value="discovery">Discovery</option>
          <option value="validation">Validation</option>
          <option value="review">Review</option>
          <option value="other">Other</option>
        </select>

        <select
          value={projectFilter}
          onChange={(e) => onProjectFilterChange(e.target.value)}
          className="px-3 py-1.5 text-[13px] bg-white border border-gray-200 rounded-md focus:outline-none focus:ring-1 focus:ring-brand-primary"
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
