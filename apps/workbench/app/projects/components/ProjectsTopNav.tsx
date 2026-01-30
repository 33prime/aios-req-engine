/**
 * ProjectsTopNav - Compact icon-based navigation bar
 *
 * Features:
 * - FilterDropdown (stage, client, date range filters)
 * - SortDropdown (created_at, updated_at, readiness)
 * - Expandable search input
 * - View toggle (table/kanban)
 */

'use client'

import React, { useState, useRef, useEffect } from 'react'
import {
  SlidersHorizontal,
  Search,
  X,
  LayoutGrid,
  List,
  ChevronDown,
  RefreshCw,
} from 'lucide-react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

interface ProjectsTopNavProps {
  viewMode: 'table' | 'kanban'
  searchQuery: string
  stageFilter: string
  clientFilter: string
  uniqueClients: string[]
  sortField: 'name' | 'updated_at' | 'readiness_score'
  sortOrder: 'asc' | 'desc'
  onViewModeChange: (mode: 'table' | 'kanban') => void
  onSearchChange: (query: string) => void
  onStageFilterChange: (stage: string) => void
  onClientFilterChange: (client: string) => void
  onSortFieldChange: (field: 'name' | 'updated_at' | 'readiness_score') => void
  onRefresh: () => void
}

const STAGES = [
  { id: 'discovery', label: 'Discovery' },
  { id: 'validation', label: 'Validation' },
  { id: 'prototype', label: 'Prototype' },
  { id: 'proposal', label: 'Proposal' },
  { id: 'build', label: 'Build' },
  { id: 'live', label: 'Live' },
]

type SortField = 'name' | 'updated_at' | 'readiness_score'

const SORT_OPTIONS: Array<{ id: SortField; label: string }> = [
  { id: 'updated_at', label: 'Last Updated' },
  { id: 'name', label: 'Name' },
  { id: 'readiness_score', label: 'Readiness Score' },
]

export function ProjectsTopNav({
  viewMode,
  searchQuery,
  stageFilter,
  clientFilter,
  uniqueClients,
  sortField,
  onViewModeChange,
  onSearchChange,
  onStageFilterChange,
  onClientFilterChange,
  onSortFieldChange,
  onRefresh,
}: ProjectsTopNavProps) {
  const [searchExpanded, setSearchExpanded] = useState(false)
  const [filterOpen, setFilterOpen] = useState(false)
  const [sortOpen, setSortOpen] = useState(false)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // Auto-focus search input when expanded
  useEffect(() => {
    if (searchExpanded && searchInputRef.current) {
      searchInputRef.current.focus()
    }
  }, [searchExpanded])

  // Collapse search if empty and blurred
  const handleSearchBlur = () => {
    if (!searchQuery) {
      setSearchExpanded(false)
    }
  }

  // Count active filters
  const filterCount =
    (stageFilter !== 'all' ? 1 : 0) +
    (clientFilter !== 'all' ? 1 : 0)

  return (
    <div className="flex items-center justify-between mb-4 pb-3 border-b border-ui-cardBorder">
      {/* Left: Filter + Sort + Refresh */}
      <div className="flex items-center gap-2">
        {/* Filter Dropdown */}
        <Popover open={filterOpen} onOpenChange={setFilterOpen}>
          <PopoverTrigger asChild>
            <button className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-ui-bodyText border border-ui-cardBorder rounded-lg hover:bg-gray-50 transition-colors">
              <SlidersHorizontal className="w-4 h-4" />
              <span>Filter</span>
              {filterCount > 0 && (
                <span className="px-1.5 py-0.5 text-[10px] bg-brand-teal/10 text-brand-teal rounded-full font-medium">
                  {filterCount}
                </span>
              )}
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-64 p-3" align="start">
            <div className="space-y-3">
              {/* Stage Filter */}
              <div>
                <label className="text-xs font-semibold text-ui-headingDark mb-1.5 block">
                  Stage
                </label>
                <div className="space-y-1">
                  <label className="flex items-center gap-2 cursor-pointer group">
                    <input
                      type="radio"
                      checked={stageFilter === 'all'}
                      onChange={() => onStageFilterChange('all')}
                      className="w-3.5 h-3.5 text-brand-teal focus:ring-brand-teal/20"
                    />
                    <span className="text-xs text-ui-bodyText group-hover:text-ui-headingDark">
                      All Stages
                    </span>
                  </label>
                  {STAGES.map((stage) => (
                    <label
                      key={stage.id}
                      className="flex items-center gap-2 cursor-pointer group"
                    >
                      <input
                        type="radio"
                        checked={stageFilter === stage.id}
                        onChange={() => onStageFilterChange(stage.id)}
                        className="w-3.5 h-3.5 text-brand-teal focus:ring-brand-teal/20"
                      />
                      <span className="text-xs text-ui-bodyText group-hover:text-ui-headingDark">
                        {stage.label}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Client Filter */}
              {uniqueClients.length > 0 && (
                <div>
                  <label className="text-xs font-semibold text-ui-headingDark mb-1.5 block">
                    Client
                  </label>
                  <select
                    value={clientFilter}
                    onChange={(e) => onClientFilterChange(e.target.value)}
                    className="w-full px-2 py-1.5 text-xs border border-ui-cardBorder rounded-lg bg-white text-ui-bodyText focus:outline-none focus:ring-2 focus:ring-brand-teal/20"
                  >
                    <option value="all">All Clients</option>
                    {uniqueClients.map((client) => (
                      <option key={client} value={client}>
                        {client}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Clear Filters */}
              {filterCount > 0 && (
                <button
                  onClick={() => {
                    onStageFilterChange('all')
                    onClientFilterChange('all')
                  }}
                  className="w-full px-2 py-1.5 text-xs text-ui-supportText hover:text-ui-headingDark border border-ui-cardBorder rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Clear Filters
                </button>
              )}
            </div>
          </PopoverContent>
        </Popover>

        {/* Sort Dropdown */}
        <Popover open={sortOpen} onOpenChange={setSortOpen}>
          <PopoverTrigger asChild>
            <button className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-ui-bodyText border border-ui-cardBorder rounded-lg hover:bg-gray-50 transition-colors">
              <span>
                {SORT_OPTIONS.find((opt) => opt.id === sortField)?.label || 'Sort'}
              </span>
              <ChevronDown className="w-3 h-3" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-48 p-2" align="start">
            <div className="space-y-0.5">
              {SORT_OPTIONS.map((option) => (
                <button
                  key={option.id}
                  onClick={() => {
                    onSortFieldChange(option.id)
                    setSortOpen(false)
                  }}
                  className={`w-full text-left px-2 py-1.5 text-xs rounded-md transition-colors ${
                    sortField === option.id
                      ? 'bg-brand-teal/10 text-brand-teal font-medium'
                      : 'text-ui-bodyText hover:bg-gray-50 hover:text-ui-headingDark'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </PopoverContent>
        </Popover>

        {/* Refresh Button */}
        <button
          onClick={onRefresh}
          className="p-1.5 text-ui-supportText hover:text-ui-headingDark hover:bg-gray-50 rounded-lg transition-colors"
          title="Refresh projects"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Right: Search + View Toggle */}
      <div className="flex items-center gap-2">
        {/* Expandable Search */}
        <div className="flex items-center">
          {searchExpanded ? (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 border border-ui-cardBorder rounded-lg bg-white">
              <Search className="w-4 h-4 text-ui-supportText flex-shrink-0" />
              <input
                ref={searchInputRef}
                type="text"
                value={searchQuery}
                onChange={(e) => onSearchChange(e.target.value)}
                onBlur={handleSearchBlur}
                placeholder="Search projects..."
                className="w-48 text-xs text-ui-bodyText placeholder:text-ui-supportText focus:outline-none bg-transparent"
              />
              {searchQuery && (
                <button
                  onClick={() => onSearchChange('')}
                  className="text-ui-supportText hover:text-ui-headingDark"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          ) : (
            <button
              onClick={() => setSearchExpanded(true)}
              className="p-1.5 text-ui-supportText hover:text-ui-headingDark hover:bg-gray-50 rounded-lg transition-colors"
              title="Search projects"
            >
              <Search className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* View Toggle */}
        <div className="flex items-center gap-0.5 p-0.5 bg-gray-100 rounded-lg">
          <button
            onClick={() => onViewModeChange('table')}
            className={`p-1.5 rounded-md transition-colors ${
              viewMode === 'table'
                ? 'bg-white text-brand-teal shadow-sm'
                : 'text-ui-supportText hover:text-ui-headingDark'
            }`}
            title="Table view"
          >
            <List className="w-4 h-4" />
          </button>
          <button
            onClick={() => onViewModeChange('kanban')}
            className={`p-1.5 rounded-md transition-colors ${
              viewMode === 'kanban'
                ? 'bg-white text-brand-teal shadow-sm'
                : 'text-ui-supportText hover:text-ui-headingDark'
            }`}
            title="Kanban view"
          >
            <LayoutGrid className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
