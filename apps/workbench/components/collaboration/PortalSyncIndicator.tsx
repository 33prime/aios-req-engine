/**
 * PortalSyncIndicator Component
 *
 * Real-time sync indicator showing progress between consultant
 * and client portal. Shows question/document completion with
 * visual progress bars and activity indicators.
 */

'use client'

import React from 'react'
import {
  MessageSquare,
  FileText,
  CheckCircle2,
  Clock,
  Activity,
  RefreshCw,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface PortalItemSync {
  sent: number
  completed: number
  in_progress: number
  pending: number
}

interface PortalSyncIndicatorProps {
  questions: PortalItemSync
  documents: PortalItemSync
  lastClientActivity: string | null
  isRefreshing?: boolean
  onRefresh?: () => void
  compact?: boolean
}

export function PortalSyncIndicator({
  questions,
  documents,
  lastClientActivity,
  isRefreshing = false,
  onRefresh,
  compact = false,
}: PortalSyncIndicatorProps) {
  const totalQuestions = questions.sent
  const questionsAnswered = questions.completed
  const questionsInProgress = questions.in_progress

  const totalDocs = documents.sent
  const docsReceived = documents.completed
  const docsInProgress = documents.in_progress

  const hasActivity = totalQuestions > 0 || totalDocs > 0
  const hasRecentActivity = lastClientActivity &&
    (Date.now() - new Date(lastClientActivity).getTime()) < 1000 * 60 * 60 // 1 hour

  const lastActivityText = lastClientActivity
    ? formatDistanceToNow(new Date(lastClientActivity), { addSuffix: true })
    : null

  if (compact) {
    return (
      <CompactIndicator
        questions={{ total: totalQuestions, completed: questionsAnswered }}
        documents={{ total: totalDocs, completed: docsReceived }}
        hasRecentActivity={!!hasRecentActivity}
        lastActivityText={lastActivityText}
      />
    )
  }

  return (
    <div className="space-y-4">
      {/* Header with refresh */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className={`w-4 h-4 ${hasRecentActivity ? 'text-green-500' : 'text-gray-400'}`} />
          <span className="text-sm font-medium text-gray-700">Portal Sync</span>
          {hasRecentActivity && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
          )}
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>

      {!hasActivity ? (
        <div className="text-center py-4 text-gray-400 text-sm">
          No items sent to portal yet
        </div>
      ) : (
        <>
          {/* Questions Progress */}
          {totalQuestions > 0 && (
            <SyncProgressBar
              icon={MessageSquare}
              label="Questions"
              completed={questionsAnswered}
              inProgress={questionsInProgress}
              total={totalQuestions}
              color="purple"
            />
          )}

          {/* Documents Progress */}
          {totalDocs > 0 && (
            <SyncProgressBar
              icon={FileText}
              label="Documents"
              completed={docsReceived}
              inProgress={docsInProgress}
              total={totalDocs}
              color="blue"
            />
          )}

          {/* Last activity */}
          {lastActivityText && (
            <div className="flex items-center gap-2 text-xs text-gray-500 pt-2 border-t border-gray-100">
              <Clock className="w-3 h-3" />
              <span>Last activity {lastActivityText}</span>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ============================================================================
// Sub-components
// ============================================================================

interface SyncProgressBarProps {
  icon: typeof MessageSquare
  label: string
  completed: number
  inProgress: number
  total: number
  color: 'purple' | 'blue' | 'green' | 'amber'
}

function SyncProgressBar({
  icon: Icon,
  label,
  completed,
  inProgress,
  total,
  color,
}: SyncProgressBarProps) {
  const completedPercent = total > 0 ? (completed / total) * 100 : 0
  const inProgressPercent = total > 0 ? (inProgress / total) * 100 : 0
  const isComplete = completed === total && total > 0

  const colorMap = {
    purple: {
      bg: 'bg-purple-100',
      filled: 'bg-purple-500',
      inProgress: 'bg-purple-300',
      text: 'text-purple-700',
      icon: 'text-purple-500',
    },
    blue: {
      bg: 'bg-blue-100',
      filled: 'bg-blue-500',
      inProgress: 'bg-blue-300',
      text: 'text-brand-primary-hover',
      icon: 'text-blue-500',
    },
    green: {
      bg: 'bg-green-100',
      filled: 'bg-green-500',
      inProgress: 'bg-green-300',
      text: 'text-green-700',
      icon: 'text-green-500',
    },
    amber: {
      bg: 'bg-amber-100',
      filled: 'bg-amber-500',
      inProgress: 'bg-amber-300',
      text: 'text-amber-700',
      icon: 'text-amber-500',
    },
  }

  const colors = colorMap[color]

  return (
    <div>
      {/* Label row */}
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-2">
          <Icon className={`w-4 h-4 ${colors.icon}`} />
          <span className="text-sm text-gray-700">{label}</span>
        </div>
        <div className="flex items-center gap-2">
          {isComplete ? (
            <CheckCircle2 className="w-4 h-4 text-green-500" />
          ) : (
            <span className="text-sm font-medium text-gray-900">
              {completed}/{total}
            </span>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className={`h-2 rounded-full ${colors.bg} overflow-hidden`}>
        <div className="h-full flex">
          <div
            className={`${colors.filled} transition-all duration-500`}
            style={{ width: `${completedPercent}%` }}
          />
          {inProgress > 0 && (
            <div
              className={`${colors.inProgress} transition-all duration-500`}
              style={{ width: `${inProgressPercent}%` }}
            />
          )}
        </div>
      </div>

      {/* Status text */}
      {inProgress > 0 && (
        <p className="text-xs text-gray-500 mt-1">
          {inProgress} in progress
        </p>
      )}
    </div>
  )
}

interface CompactIndicatorProps {
  questions: { total: number; completed: number }
  documents: { total: number; completed: number }
  hasRecentActivity?: boolean
  lastActivityText?: string | null
}

function CompactIndicator({
  questions,
  documents,
  hasRecentActivity,
  lastActivityText,
}: CompactIndicatorProps) {
  const hasItems = questions.total > 0 || documents.total > 0

  if (!hasItems) {
    return (
      <span className="text-xs text-gray-400">No items sent</span>
    )
  }

  return (
    <div className="flex items-center gap-3">
      {questions.total > 0 && (
        <div className="flex items-center gap-1">
          <MessageSquare className="w-3 h-3 text-purple-500" />
          <span className="text-xs text-gray-600">
            {questions.completed}/{questions.total}
          </span>
        </div>
      )}
      {documents.total > 0 && (
        <div className="flex items-center gap-1">
          <FileText className="w-3 h-3 text-blue-500" />
          <span className="text-xs text-gray-600">
            {documents.completed}/{documents.total}
          </span>
        </div>
      )}
      {hasRecentActivity && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
        </span>
      )}
    </div>
  )
}

export default PortalSyncIndicator
