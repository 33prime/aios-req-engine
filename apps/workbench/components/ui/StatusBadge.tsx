/**
 * StatusBadge Component
 *
 * Displays status badges for entities (PRD sections, VP steps, features)
 * with consistent styling based on the design system.
 *
 * Usage:
 *   <StatusBadge status="draft" />
 *   <StatusBadge status="confirmed_consultant" />
 *   <StatusBadge status="needs_confirmation" />
 *   <StatusBadge status="confirmed_client" />
 */

import React from 'react'
import { getStatusBadgeConfig } from '@/lib/status-utils'

interface StatusBadgeProps {
  status: string | null | undefined
  className?: string
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const config = getStatusBadgeConfig(status)

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide ${className}`}
      style={{
        backgroundColor: config.bg,
        color: config.text,
      }}
    >
      {config.label}
    </span>
  )
}

/**
 * SeverityBadge Component
 *
 * Displays severity badges for insights (critical, important, minor)
 */

import { getSeverityBadgeConfig } from '@/lib/status-utils'
import type { SeverityType } from '@/lib/design-tokens'

interface SeverityBadgeProps {
  severity: SeverityType
  className?: string
}

export function SeverityBadge({ severity, className = '' }: SeverityBadgeProps) {
  const config = getSeverityBadgeConfig(severity)

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide ${className}`}
      style={{
        backgroundColor: config.bg,
        color: config.text,
      }}
    >
      {config.label}
    </span>
  )
}

/**
 * GateBadge Component
 *
 * Displays gate badges for insights (completeness, validation, assumption, scope, wow)
 * with icon and optional tooltip
 */

import { getGateBadgeConfig, getGateIcon, getGateDescription } from '@/lib/status-utils'
import type { GateType } from '@/lib/design-tokens'

interface GateBadgeProps {
  gate: GateType
  showTooltip?: boolean
  className?: string
}

export function GateBadge({ gate, showTooltip = false, className = '' }: GateBadgeProps) {
  const config = getGateBadgeConfig(gate)
  const icon = getGateIcon(gate)
  const description = getGateDescription(gate)

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide ${className}`}
      style={{
        backgroundColor: config.bg,
        color: config.text,
      }}
      title={showTooltip ? description : undefined}
    >
      <span className="text-sm">{icon}</span>
      {config.label}
    </span>
  )
}

/**
 * ChannelBadge Component
 *
 * Displays channel recommendation badges (email, meeting)
 */

import { getChannelBadgeConfig } from '@/lib/status-utils'
import type { ChannelType } from '@/lib/design-tokens'

interface ChannelBadgeProps {
  channel: ChannelType
  className?: string
}

export function ChannelBadge({ channel, className = '' }: ChannelBadgeProps) {
  const config = getChannelBadgeConfig(channel)

  return (
    <span
      className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide ${className}`}
      style={{
        backgroundColor: config.bg,
        color: config.text,
      }}
    >
      <span className="text-sm">{config.icon}</span>
      {config.label}
    </span>
  )
}

/**
 * ComplexityBadge Component
 *
 * Displays complexity indicator for confirmations
 */

import { getComplexityBadge } from '@/lib/status-utils'

interface ComplexityBadgeProps {
  score: number
  showDescription?: boolean
  className?: string
}

export function ComplexityBadge({ score, showDescription = false, className = '' }: ComplexityBadgeProps) {
  const config = getComplexityBadge(score)

  return (
    <div className={`inline-flex flex-col ${className}`}>
      <span
        className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wide"
        style={{
          backgroundColor: config.bg,
          color: config.text,
        }}
      >
        {config.label}
      </span>
      {showDescription && (
        <span className="text-xs text-ui-supportText mt-1">
          {config.description}
        </span>
      )}
    </div>
  )
}
