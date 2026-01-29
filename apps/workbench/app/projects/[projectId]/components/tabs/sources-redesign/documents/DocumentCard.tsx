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
 * - Download button
 * - Delete/withdraw button
 * - Expandable analysis section
 */

'use client'

import { useState } from 'react'
import { formatDistanceToNow } from 'date-fns'
import { Download, Loader2, Trash2, ChevronDown, ChevronUp, RotateCcw } from 'lucide-react'
import { UsageBar, EvidenceBadge, SourceTypeBadge } from '../shared'
import { getDocumentDownloadUrl, withdrawDocument, resetDocument, deleteDocument, type DocumentSummaryItem } from '@/lib/api'

interface DocumentCardProps {
  document: DocumentSummaryItem
  onClick?: () => void
  onWithdraw?: () => void
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatScore(score: number | undefined): string {
  if (score === undefined) return 'N/A'
  return `${Math.round(score * 100)}%`
}

export function DocumentCard({ document, onClick, onWithdraw }: DocumentCardProps) {
  const [isDownloading, setIsDownloading] = useState(false)
  const [isWithdrawing, setIsWithdrawing] = useState(false)
  const [showWithdrawConfirm, setShowWithdrawConfirm] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [isRetrying, setIsRetrying] = useState(false)

  const {
    id,
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
    quality_score,
    relevance_score,
    information_density,
    keyword_tags,
    key_topics,
  } = document

  const isProcessing = processing_status === 'pending' || processing_status === 'processing'
  const hasFailed = processing_status === 'failed'

  // Check if we have analysis data to show
  const hasAnalysis = quality_score !== undefined ||
    relevance_score !== undefined ||
    information_density !== undefined ||
    (keyword_tags && keyword_tags.length > 0) ||
    (key_topics && key_topics.length > 0)

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

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation() // Prevent card click if card is clickable
    setIsDownloading(true)
    try {
      const result = await getDocumentDownloadUrl(id)
      // Open download URL in new tab
      window.open(result.download_url, '_blank')
    } catch (error) {
      console.error('Failed to download document:', error)
    } finally {
      setIsDownloading(false)
    }
  }

  const handleWithdraw = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsWithdrawing(true)
    try {
      await withdrawDocument(id)
      setShowWithdrawConfirm(false)
      onWithdraw?.()
    } catch (error) {
      console.error('Failed to withdraw document:', error)
    } finally {
      setIsWithdrawing(false)
    }
  }

  const handleToggleExpand = (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsExpanded(!isExpanded)
  }

  const handleRetry = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsRetrying(true)
    try {
      await resetDocument(id)
      onWithdraw?.() // Refresh the list
    } catch (error) {
      console.error('Failed to retry document:', error)
    } finally {
      setIsRetrying(false)
    }
  }

  const handleForceDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    setIsWithdrawing(true)
    try {
      await deleteDocument(id, true)
      setShowWithdrawConfirm(false)
      onWithdraw?.()
    } catch (error) {
      console.error('Failed to delete document:', error)
    } finally {
      setIsWithdrawing(false)
    }
  }

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

        {/* Status/badge and actions */}
        <div className="flex items-center gap-1">
          {/* Expand/collapse button */}
          {!isProcessing && !hasFailed && hasAnalysis && (
            <button
              onClick={handleToggleExpand}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
              title={isExpanded ? "Hide analysis" : "Show analysis"}
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          )}

          {/* Download button */}
          {!isProcessing && !hasFailed && (
            <button
              onClick={handleDownload}
              disabled={isDownloading}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors disabled:opacity-50"
              title="Download file"
            >
              {isDownloading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Download className="w-4 h-4" />
              )}
            </button>
          )}

          {/* Delete/withdraw button */}
          {!isProcessing && (
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  setShowWithdrawConfirm(!showWithdrawConfirm)
                }}
                className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-md transition-colors"
                title="Remove document"
              >
                <Trash2 className="w-4 h-4" />
              </button>

              {/* Confirmation popover */}
              {showWithdrawConfirm && (
                <div className="absolute right-0 top-full mt-1 z-10 bg-white border border-gray-200 rounded-lg shadow-lg p-3 w-56">
                  <p className="text-xs text-gray-600 mb-2">
                    {hasFailed
                      ? 'Delete this failed document?'
                      : isProcessing
                      ? 'Force delete this stuck document?'
                      : 'Remove this document from the project?'}
                  </p>
                  {isProcessing && (
                    <p className="text-xs text-amber-600 mb-2">
                      Document appears stuck. This will force delete it.
                    </p>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        setShowWithdrawConfirm(false)
                      }}
                      className="flex-1 px-2 py-1 text-xs text-gray-600 bg-gray-100 hover:bg-gray-200 rounded transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={hasFailed || isProcessing ? handleForceDelete : handleWithdraw}
                      disabled={isWithdrawing}
                      className="flex-1 px-2 py-1 text-xs text-white bg-red-600 hover:bg-red-700 rounded transition-colors disabled:opacity-50"
                    >
                      {isWithdrawing ? 'Removing...' : hasFailed ? 'Delete' : 'Remove'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {isProcessing ? (
            <span className="px-2 py-1 text-xs font-medium text-amber-700 bg-amber-50 rounded-md ml-1">
              Processing...
            </span>
          ) : hasFailed ? (
            <div className="flex items-center gap-1 ml-1">
              <button
                onClick={handleRetry}
                disabled={isRetrying}
                className="p-1 text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded transition-colors disabled:opacity-50"
                title="Retry processing"
              >
                {isRetrying ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RotateCcw className="w-4 h-4" />
                )}
              </button>
              <span className="px-2 py-1 text-xs font-medium text-red-700 bg-red-50 rounded-md">
                Failed
              </span>
            </div>
          ) : (
            <div className="ml-1">
              <EvidenceBadge level={badgeLevel} size="sm" />
            </div>
          )}
        </div>
      </div>

      {/* Summary */}
      {content_summary && !isProcessing && (
        <p className={`text-sm text-gray-600 ${isExpanded ? '' : 'line-clamp-2'}`}>
          {content_summary}
        </p>
      )}

      {isProcessing && (
        <p className="text-sm text-gray-400 italic">
          Document is being processed...
        </p>
      )}

      {/* Expanded Analysis Section */}
      {isExpanded && hasAnalysis && !isProcessing && (
        <div className="pt-2 border-t border-gray-100 space-y-3">
          {/* Quality Scores */}
          {(quality_score !== undefined || relevance_score !== undefined || information_density !== undefined) && (
            <div className="flex items-center gap-2 flex-wrap">
              {quality_score !== undefined && (
                <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-blue-50 text-blue-700">
                  Quality: {formatScore(quality_score)}
                </span>
              )}
              {relevance_score !== undefined && (
                <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-green-50 text-green-700">
                  Relevance: {formatScore(relevance_score)}
                </span>
              )}
              {information_density !== undefined && (
                <span className="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full bg-purple-50 text-purple-700">
                  Density: {formatScore(information_density)}
                </span>
              )}
            </div>
          )}

          {/* Key Topics */}
          {key_topics && key_topics.length > 0 && (
            <div>
              <span className="text-xs font-medium text-gray-500 block mb-1">Key Topics</span>
              <div className="flex flex-wrap gap-1">
                {key_topics.map((topic, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-700"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Keywords */}
          {keyword_tags && keyword_tags.length > 0 && (
            <div>
              <span className="text-xs font-medium text-gray-500 block mb-1">Keywords</span>
              <div className="flex flex-wrap gap-1">
                {keyword_tags.slice(0, 10).map((tag, index) => (
                  <span
                    key={index}
                    className="inline-flex items-center px-2 py-0.5 text-xs rounded bg-amber-50 text-amber-700"
                  >
                    {tag}
                  </span>
                ))}
                {keyword_tags.length > 10 && (
                  <span className="text-xs text-gray-400">
                    +{keyword_tags.length - 10} more
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
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
