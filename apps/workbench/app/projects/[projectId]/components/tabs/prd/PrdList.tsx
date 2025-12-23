/**
 * PrdList Component
 *
 * Left column: Selectable list of PRD sections
 * - Shows section type, label, status
 * - Filterable by status
 * - Enrichment indicator
 */

'use client'

import React, { useState } from 'react'
import { ListItem, EmptyState } from '@/components/ui'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { FileText, Users, Target, Zap, Filter } from 'lucide-react'
import type { PrdSection } from '@/types/api'

interface PrdListProps {
  sections: PrdSection[]
  selectedId: string | null
  onSelect: (section: PrdSection) => void
}

const SECTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  personas: Users,
  key_features: Target,
  happy_path: Zap,
}

const SECTION_DESCRIPTIONS: Record<string, string> = {
  personas: 'User personas and characteristics',
  key_features: 'Core product features',
  happy_path: 'Ideal user journey',
  constraints: 'Scope and limitations',
  features_must_have: 'Must-have features',
  features_nice_to_have: 'Nice-to-have features',
}

export function PrdList({ sections, selectedId, onSelect }: PrdListProps) {
  const [statusFilter, setStatusFilter] = useState<string | null>(null)

  // Filter sections
  const filteredSections = statusFilter
    ? sections.filter(s => s.status === statusFilter)
    : sections

  // Count by status
  const statusCounts = sections.reduce((acc, s) => {
    acc[s.status] = (acc[s.status] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  if (sections.length === 0) {
    return (
      <EmptyState
        icon={<FileText className="h-12 w-12" />}
        title="No PRD Sections"
        description="Run the Build State agent to extract PRD sections from your signals."
      />
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with filter */}
      <div>
        <h2 className="heading-2 mb-2">PRD Sections</h2>
        <p className="text-support text-ui-supportText mb-4">
          {filteredSections.length} of {sections.length} sections
        </p>

        {/* Status Filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setStatusFilter(null)}
            className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              statusFilter === null
                ? 'bg-brand-primary text-white'
                : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
            }`}
          >
            All ({sections.length})
          </button>
          {Object.entries(statusCounts).map(([status, count]) => (
            <button
              key={status}
              onClick={() => setStatusFilter(statusFilter === status ? null : status)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                statusFilter === status
                  ? 'bg-brand-primary text-white'
                  : 'bg-ui-buttonGray text-ui-bodyText hover:bg-ui-buttonGrayHover'
              }`}
            >
              {status.replace(/_/g, ' ')} ({count})
            </button>
          ))}
        </div>
      </div>

      {/* Sections List */}
      <div className="space-y-2">
        {filteredSections.map((section) => {
          const Icon = SECTION_ICONS[section.slug] || FileText
          const description = SECTION_DESCRIPTIONS[section.slug] || section.slug.replace(/_/g, ' ')
          const isEnriched = !!section.enrichment

          return (
            <ListItem
              key={section.id}
              title={
                <div className="flex items-center gap-2">
                  <Icon className="h-4 w-4 flex-shrink-0 text-brand-primary" />
                  <span>{section.label}</span>
                  {isEnriched && (
                    <span className="text-xs text-brand-accent">✨</span>
                  )}
                </div>
              }
              subtitle={description}
              meta={
                section.required && (
                  <span className="text-xs font-medium text-red-600">Required</span>
                )
              }
              badge={<StatusBadge status={section.status} />}
              active={section.id === selectedId}
              onClick={() => onSelect(section)}
            />
          )
        })}
      </div>

      {filteredSections.length === 0 && (
        <div className="text-center py-8">
          <Filter className="h-8 w-8 text-ui-supportText mx-auto mb-2" />
          <p className="text-support text-ui-supportText">
            No sections match the selected filter
          </p>
        </div>
      )}
    </div>
  )
}
