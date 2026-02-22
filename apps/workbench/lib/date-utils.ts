/**
 * Shared date formatting utilities.
 *
 * Extracted from 8+ drawer components that each had identical copies.
 */

const SYSTEM_AUTHORS = new Set([
  'system',
  'build_state',
  'signal_pipeline_v2',
  'project_launch',
])

/** Relative time string: "just now", "5m ago", "3h ago", "2d ago", or formatted date. */
export function formatRelativeTime(dateStr: string): string {
  try {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  } catch {
    return ''
  }
}

/** Format as "Jan 5, 2026, 02:30 PM" */
export function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Format as "Jan 5, 2026" (no time). Accepts null/undefined → returns ''. */
export function formatDateShort(dateStr: string | null | undefined): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

/** Display name for a revision author — maps system actors to "✦ AIOS". */
export function formatRevisionAuthor(createdBy: string | null | undefined): string {
  if (!createdBy || SYSTEM_AUTHORS.has(createdBy)) return '✦ AIOS'
  return createdBy
}

/** Color classes for revision type badges. */
export const REVISION_TYPE_COLORS: Record<string, string> = {
  created: 'bg-[#E8F5E9] text-[#25785A]',
  enriched: 'bg-[#F0F0F0] text-[#666666]',
  updated: 'bg-[#F0F0F0] text-[#666666]',
  merged: 'bg-[#F0F0F0] text-[#666666]',
}
