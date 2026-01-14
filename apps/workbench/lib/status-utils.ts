/**
 * Status Utilities
 *
 * Helper functions for mapping database statuses to badge configurations,
 * determining status order, and other status-related logic.
 */

import {
  statusColors,
  severityColors,
  gateColors,
  channelColors,
  type StatusType,
  type SeverityType,
  type GateType,
  type ChannelType
} from './design-tokens'

// ============================================================================
// STATUS BADGE HELPERS
// ============================================================================

/**
 * Map database status to badge configuration
 */
export function getStatusBadgeConfig(status: string | null | undefined) {
  // Handle null/undefined
  if (!status) {
    return statusColors.aiDraft
  }

  // Normalize status string
  const normalizedStatus = status.toLowerCase().trim()

  // Map to badge config
  switch (normalizedStatus) {
    case 'draft':
    case 'ai_draft':
      return statusColors.aiDraft

    case 'needs_client':
    case 'needs_confirmation':
    case 'needs confirmation':
      return statusColors.needsConfirmation

    case 'confirmed_consultant':
    case 'confirmed':
      return statusColors.confirmedConsultant

    case 'confirmed_client':
    case 'client_confirmed':
      return statusColors.confirmedClient

    default:
      console.warn(`Unknown status: ${status}, defaulting to AI Draft`)
      return statusColors.aiDraft
  }
}

/**
 * Get severity badge configuration
 */
export function getSeverityBadgeConfig(severity: SeverityType) {
  return severityColors[severity] || severityColors.minor
}

/**
 * Get gate badge configuration
 */
export function getGateBadgeConfig(gate: GateType) {
  return gateColors[gate] || gateColors.completeness
}

/**
 * Get channel badge configuration
 */
export function getChannelBadgeConfig(channel: ChannelType) {
  return channelColors[channel] || channelColors.email
}

// ============================================================================
// STATUS ORDER & FILTERING
// ============================================================================

/**
 * Status order for sorting (lower = earlier in workflow)
 */
const statusOrder: Record<string, number> = {
  draft: 0,
  ai_draft: 0,
  confirmed_consultant: 1,
  confirmed: 1,
  needs_client: 2,
  needs_confirmation: 2,
  confirmed_client: 3,
  client_confirmed: 3
}

/**
 * Compare two statuses for sorting
 */
export function compareStatuses(statusA: string, statusB: string): number {
  const orderA = statusOrder[statusA.toLowerCase()] ?? 999
  const orderB = statusOrder[statusB.toLowerCase()] ?? 999
  return orderA - orderB
}

/**
 * Check if status is "ready for client"
 */
export function isReadyForClient(status: string): boolean {
  const normalized = status.toLowerCase().trim()
  return normalized === 'needs_client' || normalized === 'needs_confirmation'
}

/**
 * Check if status is "consultant approved"
 */
export function isConsultantApproved(status: string): boolean {
  const normalized = status.toLowerCase().trim()
  return normalized === 'confirmed_consultant' || normalized === 'confirmed'
}

/**
 * Check if status is "client confirmed"
 */
export function isClientConfirmed(status: string): boolean {
  const normalized = status.toLowerCase().trim()
  return normalized === 'confirmed_client' || normalized === 'client_confirmed'
}

/**
 * Check if item needs consultant review (draft state)
 */
export function needsConsultantReview(status: string): boolean {
  const normalized = status.toLowerCase().trim()
  return normalized === 'draft' || normalized === 'ai_draft' || !status
}

// ============================================================================
// SEVERITY ORDER & FILTERING
// ============================================================================

/**
 * Severity order for sorting (lower = more severe)
 */
const severityOrder: Record<SeverityType, number> = {
  critical: 0,
  important: 1,
  minor: 2
}

/**
 * Compare two severities for sorting
 */
export function compareSeverities(severityA: SeverityType, severityB: SeverityType): number {
  return severityOrder[severityA] - severityOrder[severityB]
}

/**
 * Filter items by severity
 */
export function filterBySeverity<T extends { severity: SeverityType }>(
  items: T[],
  severity: SeverityType | 'all'
): T[] {
  if (severity === 'all') return items
  return items.filter(item => item.severity === severity)
}

// ============================================================================
// GATE FILTERING
// ============================================================================

/**
 * Filter items by gate
 */
export function filterByGate<T extends { gate?: GateType }>(
  items: T[],
  gate: GateType | 'all'
): T[] {
  if (gate === 'all') return items
  return items.filter(item => item.gate === gate)
}

// ============================================================================
// COMPLEXITY SCORING (for confirmations)
// ============================================================================

/**
 * Calculate complexity score for a confirmation
 *
 * Score breakdown:
 * - Priority: low = 1, medium = 2, high = 3
 * - Evidence count: +1 per item (max +3)
 * - Suggested method: meeting = +2, email = +0
 *
 * Range: 1-8
 * - Low (1-3): Email sufficient
 * - Medium (4-5): Meeting recommended
 * - High (6+): Meeting strongly recommended
 */
export function getComplexityScore(confirmation: {
  priority: 'low' | 'medium' | 'high'
  evidence: unknown[]
  suggested_method: 'email' | 'meeting'
}): number {
  let score = 0

  // Priority score (1-3)
  const priorityScores = { low: 1, medium: 2, high: 3 }
  score += priorityScores[confirmation.priority]

  // Evidence count (0-3)
  const evidenceScore = Math.min(confirmation.evidence?.length || 0, 3)
  score += evidenceScore

  // Suggested method bonus
  if (confirmation.suggested_method === 'meeting') {
    score += 2
  }

  return score
}

/**
 * Get complexity badge info based on score
 */
export function getComplexityBadge(score: number) {
  if (score >= 6) {
    return {
      label: 'HIGH COMPLEXITY',
      bg: '#FEE2E2', // red-50
      text: '#991B1B', // red-800
      description: 'Meeting strongly recommended'
    }
  } else if (score >= 4) {
    return {
      label: 'MEDIUM COMPLEXITY',
      bg: '#FEF3C7', // yellow-50
      text: '#92400E', // yellow-800
      description: 'Meeting recommended'
    }
  } else {
    return {
      label: 'LOW COMPLEXITY',
      bg: '#D1FAE5', // green-50
      text: '#047857', // green-700
      description: 'Email sufficient'
    }
  }
}

// ============================================================================
// DISPLAY HELPERS
// ============================================================================

/**
 * Format status for display (human-readable)
 */
export function formatStatus(status: string | null | undefined): string {
  if (!status) return 'Draft'

  const config = getStatusBadgeConfig(status)
  return config.label
}

/**
 * Format severity for display
 */
export function formatSeverity(severity: SeverityType): string {
  return severityColors[severity].label
}

/**
 * Format gate for display
 */
export function formatGate(gate: GateType): string {
  return (gateColors[gate] || gateColors.completeness).label
}

/**
 * Get icon for gate
 */
export function getGateIcon(gate: GateType): string {
  return (gateColors[gate] || gateColors.completeness).icon
}

/**
 * Get description for gate
 */
export function getGateDescription(gate: GateType): string {
  return (gateColors[gate] || gateColors.completeness).description
}

// ============================================================================
// PROGRESS TRACKING
// ============================================================================

/**
 * Calculate completion percentage for a collection
 */
export function calculateCompletionPercentage<T extends { status?: string }>(
  items: T[]
): {
  total: number
  draft: number
  confirmed: number
  needsConfirmation: number
  clientConfirmed: number
  percentComplete: number
} {
  const stats = {
    total: items.length,
    draft: 0,
    confirmed: 0,
    needsConfirmation: 0,
    clientConfirmed: 0,
    percentComplete: 0
  }

  if (items.length === 0) return stats

  items.forEach(item => {
    const status = item.status || 'draft'
    if (needsConsultantReview(status)) {
      stats.draft++
    } else if (isReadyForClient(status)) {
      stats.needsConfirmation++
    } else if (isClientConfirmed(status)) {
      stats.clientConfirmed++
    } else if (isConsultantApproved(status)) {
      stats.confirmed++
    }
  })

  // Calculate percentage based on items that have consultant approval or better
  const approved = stats.confirmed + stats.needsConfirmation + stats.clientConfirmed
  stats.percentComplete = Math.round((approved / items.length) * 100)

  return stats
}

/**
 * Get progress label for display
 */
export function getProgressLabel(stats: ReturnType<typeof calculateCompletionPercentage>): string {
  if (stats.percentComplete === 100) {
    return 'All items reviewed'
  } else if (stats.percentComplete >= 75) {
    return 'Nearly complete'
  } else if (stats.percentComplete >= 50) {
    return 'In progress'
  } else if (stats.percentComplete > 0) {
    return 'Getting started'
  } else {
    return 'Not started'
  }
}
