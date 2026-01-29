/**
 * DocumentsTab Component
 *
 * Container for the Documents sub-tab.
 * Shows all uploaded documents with filtering and search.
 */

'use client'

import { useState, useMemo } from 'react'
import { FileUp } from 'lucide-react'
import { DocumentCard } from './DocumentCard'
import type { DocumentSummaryItem } from '@/lib/api'

interface DocumentsTabProps {
  documents: DocumentSummaryItem[]
  isLoading: boolean
  onUploadClick: () => void
  onRefresh?: () => void
}

type FilterType = 'all' | 'pdf' | 'docx' | 'xlsx' | 'pptx' | 'image'
type SortType = 'recent' | 'most_used' | 'name'

export function DocumentsTab({ documents, isLoading, onUploadClick, onRefresh }: DocumentsTabProps) {
  const [filter, setFilter] = useState<FilterType>('all')
  const [sort, setSort] = useState<SortType>('recent')

  // Filter and sort documents
  const filteredDocuments = useMemo(() => {
    let result = [...documents]

    // Apply type filter
    if (filter !== 'all') {
      result = result.filter(doc => doc.file_type.toLowerCase() === filter)
    }

    // Apply sort
    switch (sort) {
      case 'recent':
        result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        break
      case 'most_used':
        result.sort((a, b) => b.usage_count - a.usage_count)
        break
      case 'name':
        result.sort((a, b) => a.original_filename.localeCompare(b.original_filename))
        break
    }

    return result
  }, [documents, filter, sort])

  // Get unique file types for filter
  const fileTypes = useMemo(() => {
    const types = new Set(documents.map(d => d.file_type.toLowerCase()))
    return Array.from(types)
  }, [documents])

  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Skeleton cards */}
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-gray-50 border border-gray-200 rounded-xl p-4 animate-pulse">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-gray-200 rounded" />
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
                <div className="h-3 bg-gray-100 rounded w-1/4" />
              </div>
            </div>
            <div className="h-12 bg-gray-100 rounded mt-3" />
          </div>
        ))}
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
          <FileUp className="w-8 h-8 text-gray-400" />
        </div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">No documents yet</h3>
        <p className="text-sm text-gray-500 mb-6 max-w-sm">
          Upload documents to provide evidence and context for your project.
          Supported: PDF, Word, Excel, PowerPoint, and images.
        </p>
        <button
          onClick={onUploadClick}
          className="px-4 py-2 bg-brand-primary text-white rounded-lg hover:bg-brand-primaryHover transition-colors text-sm font-medium"
        >
          Upload Document
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Filter:</span>
          <div className="flex items-center gap-1">
            <FilterButton
              active={filter === 'all'}
              onClick={() => setFilter('all')}
            >
              All
            </FilterButton>
            {fileTypes.includes('pdf') && (
              <FilterButton
                active={filter === 'pdf'}
                onClick={() => setFilter('pdf')}
              >
                PDF
              </FilterButton>
            )}
            {fileTypes.includes('docx') && (
              <FilterButton
                active={filter === 'docx'}
                onClick={() => setFilter('docx')}
              >
                Word
              </FilterButton>
            )}
            {fileTypes.includes('xlsx') && (
              <FilterButton
                active={filter === 'xlsx'}
                onClick={() => setFilter('xlsx')}
              >
                Excel
              </FilterButton>
            )}
            {fileTypes.includes('pptx') && (
              <FilterButton
                active={filter === 'pptx'}
                onClick={() => setFilter('pptx')}
              >
                PowerPoint
              </FilterButton>
            )}
            {fileTypes.includes('image') && (
              <FilterButton
                active={filter === 'image'}
                onClick={() => setFilter('image')}
              >
                Images
              </FilterButton>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">Sort:</span>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortType)}
            className="text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
          >
            <option value="recent">Most Recent</option>
            <option value="most_used">Most Used</option>
            <option value="name">Name</option>
          </select>
        </div>
      </div>

      {/* Document grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {filteredDocuments.map(doc => (
          <DocumentCard key={doc.id} document={doc} onWithdraw={onRefresh} />
        ))}
      </div>

      {filteredDocuments.length === 0 && (
        <div className="py-8 text-center text-sm text-gray-500">
          No documents match the selected filter.
        </div>
      )}
    </div>
  )
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      className={`
        px-3 py-1 text-xs font-medium rounded-full transition-colors
        ${active
          ? 'bg-brand-primary text-white'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
        }
      `}
    >
      {children}
    </button>
  )
}
