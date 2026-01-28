/**
 * DocumentCard Component
 *
 * Card displaying document information with:
 * - File icon by type
 * - Title, date, page count
 * - Usage bar with count
 * - AI summary
 * - Contributed entities
 * - Evidence badge
 */

'use client'

import { formatDistanceToNow } from 'date-fns'
import { UsageBar, EvidenceBadge, SourceTypeBadge } from '../shared'
import type { DocumentSummaryItem } from '@/lib/api'

interface DocumentCardProps {
  document: DocumentSummaryItem
  onClick?: () => void
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DocumentCard({ document, onClick }: DocumentCardProps) {
  const {
    original_filename,
    file_type,
    file_size_bytes,
    page_count,
    created_at,
    content_summary,
    usage_count,
    contributed_to,
    confidence_level,
    processing_status,
  } = document

  const isProcessing = processing_status === 'pending' || processing_status === 'processing'
  const hasFailed = processing_status === 'failed'

  // Map confidence level to badge level
  const badgeLevel = confidence_level === 'client'
    ? 'client'
    : confidence_level === 'consultant'
    ? 'consultant'
    : confidence_level === 'ai_strong'
    ? 'ai_strong'
    : confidence_level === 'ai_weak'
    ? 'ai_weak'
    : 'pending'

  return (
    <div
      onClick={onClick}
      className={`
        bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3 transition-all
        ${onClick ? 'cursor-pointer hover:border-gray-300 hover:shadow-sm' : ''}
        ${isProcessing ? 'opacity-60' : ''}
      `}
    >
      {/* Header: Icon, title, meta */}
      <div className="flex items-start gap-3">
        <SourceTypeBadge type={file_type} showLabel={false} />

        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-medium text-gray-900 truncate">
            {original_filename}
          </h3>
          <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-500">
            <span>{formatFileSize(file_size_bytes)}</span>
            {page_count && (
              <>
                <span>·</span>
                <span>{page_count} pages</span>
              </>
            )}
            <span>·</span>
            <span>{formatDistanceToNow(new Date(created_at), { addSuffix: true })}</span>
          </div>
        </div>

        {/* Status/badge */}
        {isProcessing ? (
          <span className="px-2 py-1 text-xs font-medium text-amber-700 bg-amber-50 rounded-md">
            Processing...
          </span>
        ) : hasFailed ? (
          <span className="px-2 py-1 text-xs font-medium text-red-700 bg-red-50 rounded-md">
            Failed
          </span>
        ) : (
          <EvidenceBadge level={badgeLevel} size="sm" />
        )}
      </div>

      {/* Summary */}
      {content_summary && !isProcessing && (
        <p className="text-sm text-gray-600 line-clamp-2">
          {content_summary}
        </p>
      )}

      {isProcessing && (
        <p className="text-sm text-gray-400 italic">
          Document is being processed...
        </p>
      )}

      {/* Footer: Usage and contributions */}
      {!isProcessing && (
        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <div className="flex-1 max-w-[120px]">
            <UsageBar count={usage_count} showCount={true} size="sm" />
          </div>

          {usage_count > 0 && (
            <div className="flex items-center gap-3 text-xs text-gray-500">
              {contributed_to.features > 0 && (
                <span>{contributed_to.features} features</span>
              )}
              {contributed_to.personas > 0 && (
                <span>{contributed_to.personas} personas</span>
              )}
              {contributed_to.vp_steps > 0 && (
                <span>{contributed_to.vp_steps} steps</span>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
