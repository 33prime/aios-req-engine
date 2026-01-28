/**
 * MemoryTab Component
 *
 * Read-only display of project memory.
 * Shows decisions, learnings, and questions from the project.
 */

'use client'

import { Info, BookOpen } from 'lucide-react'
import { Markdown } from '@/components/ui/Markdown'

interface MemoryTabProps {
  /** Formatted memory content (markdown) */
  memoryContent: string | null
  /** Loading state */
  isLoading: boolean
  /** Last updated timestamp */
  lastUpdated?: string
}

export function MemoryTab({ memoryContent, isLoading, lastUpdated }: MemoryTabProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Warning banner skeleton */}
        <div className="h-14 bg-amber-50 rounded-lg animate-pulse" />

        {/* Content skeleton */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 animate-pulse">
          <div className="space-y-4">
            <div className="h-5 bg-gray-200 rounded w-1/4" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-100 rounded w-full" />
              <div className="h-3 bg-gray-100 rounded w-5/6" />
              <div className="h-3 bg-gray-100 rounded w-4/6" />
            </div>
            <div className="h-5 bg-gray-200 rounded w-1/4 mt-6" />
            <div className="space-y-2">
              <div className="h-3 bg-gray-100 rounded w-full" />
              <div className="h-3 bg-gray-100 rounded w-3/4" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Info banner */}
      <div className="flex items-start gap-3 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg">
        <Info className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-amber-800">
            <strong>Read-only view.</strong> To update project memory, use the chat commands:
          </p>
          <ul className="text-sm text-amber-700 mt-1 space-y-0.5">
            <li><code className="bg-amber-100 px-1 rounded">/memory</code> — View full memory</li>
            <li><code className="bg-amber-100 px-1 rounded">/remember</code> — Add a decision, learning, or question</li>
          </ul>
        </div>
      </div>

      {/* Memory content */}
      {memoryContent ? (
        <div className="bg-gray-50 border border-gray-200 rounded-xl overflow-hidden">
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-pink-50 rounded-lg flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-pink-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Project Memory</h3>
                {lastUpdated && (
                  <p className="text-xs text-gray-500">
                    Last updated: {new Date(lastUpdated).toLocaleDateString()}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-6">
            <div className="prose prose-sm max-w-none">
              <Markdown content={memoryContent} />
            </div>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
            <BookOpen className="w-8 h-8 text-gray-400" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">No memory recorded yet</h3>
          <p className="text-sm text-gray-500 max-w-sm mb-4">
            Project memory captures key decisions, learnings, and open questions
            discovered during the project.
          </p>
          <p className="text-sm text-gray-400">
            Use <code className="bg-gray-100 px-1.5 py-0.5 rounded">/remember</code> in chat to add entries.
          </p>
        </div>
      )}
    </div>
  )
}
