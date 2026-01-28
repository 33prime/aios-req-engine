/**
 * SourcesHeader Component
 *
 * Header for the Sources tab with:
 * - Title and description
 * - Global search input
 * - Evidence quality badge
 * - Upload button
 */

'use client'

import { useState } from 'react'
import { Search, Upload } from 'lucide-react'
import { EvidencePercentageBadge } from './shared/EvidenceBadge'

interface SourcesHeaderProps {
  /** Evidence strength percentage (0-100) */
  evidencePercentage: number
  /** Search query value */
  searchQuery: string
  /** Search query change handler */
  onSearchChange: (query: string) => void
  /** Search submit handler */
  onSearchSubmit: () => void
  /** Upload button click handler */
  onUploadClick: () => void
  /** Evidence badge click handler (navigates to Intelligence tab) */
  onEvidenceClick?: () => void
}

export function SourcesHeader({
  evidencePercentage,
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  onUploadClick,
  onEvidenceClick,
}: SourcesHeaderProps) {
  const [isFocused, setIsFocused] = useState(false)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      onSearchSubmit()
    }
  }

  return (
    <div className="space-y-4">
      {/* Title and description */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900">Sources</h2>
        <p className="text-sm text-gray-500 mt-0.5">
          Everything that informed this project
        </p>
      </div>

      {/* Controls row */}
      <div className="flex items-center gap-4">
        {/* Search input */}
        <div className="flex-1 max-w-md">
          <div
            className={`
              relative flex items-center rounded-lg border transition-colors
              ${isFocused
                ? 'border-brand-primary ring-2 ring-brand-primary/20'
                : 'border-gray-300 hover:border-gray-400'
              }
            `}
          >
            <Search className="absolute left-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Search across all sources..."
              className="w-full pl-10 pr-4 py-2 text-sm bg-transparent rounded-lg focus:outline-none"
            />
          </div>
        </div>

        {/* Evidence badge */}
        <EvidencePercentageBadge
          percentage={evidencePercentage}
          onClick={onEvidenceClick}
        />

        {/* Upload button */}
        <button
          onClick={onUploadClick}
          className="flex items-center gap-2 px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-primaryHover transition-colors text-sm font-medium"
        >
          <Upload className="w-4 h-4" />
          Upload
        </button>
      </div>
    </div>
  )
}
