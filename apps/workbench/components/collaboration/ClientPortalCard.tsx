/**
 * ClientPortalCard Component
 *
 * Compact card showing client portal status and sync information.
 * Similar in size to the Upcoming Meetings card in Overview.
 * Includes visual progress bars and real-time activity pulse.
 */

'use client'

import React, { useState } from 'react'
import {
  Mail,
  Users,
  CheckCircle,
  Clock,
  ExternalLink,
  AlertCircle,
  RefreshCw,
  UserPlus,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { PortalSyncIndicator } from './PortalSyncIndicator'

interface PortalItemSync {
  sent: number
  completed: number
  in_progress: number
  pending: number
}

interface PortalSyncStatus {
  portal_enabled: boolean
  portal_phase: string
  questions: PortalItemSync
  documents: PortalItemSync
  confirmations?: PortalItemSync
  last_client_activity: string | null
  clients_invited: number
  clients_active: number
}

interface ClientPortalCardProps {
  projectId: string
  portalSync: PortalSyncStatus
  onManagePortal?: () => void
  onEnablePortal?: () => void
  onRefresh?: () => void
  onInviteClient?: () => void
}

const phaseLabels: Record<string, string> = {
  pre_call: 'Pre-Call',
  post_call: 'Post-Call',
  building: 'Building',
  testing: 'Testing',
}

export function ClientPortalCard({
  projectId,
  portalSync,
  onManagePortal,
  onEnablePortal,
  onRefresh,
  onInviteClient,
}: ClientPortalCardProps) {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const totalQuestionsSent = portalSync.questions.sent
  const totalDocsSent = portalSync.documents.sent

  const hasActivity = totalQuestionsSent > 0 || totalDocsSent > 0
  const hasRecentActivity = portalSync.last_client_activity &&
    (Date.now() - new Date(portalSync.last_client_activity).getTime()) < 1000 * 60 * 60 // 1 hour

  const handleRefresh = async () => {
    if (!onRefresh) return
    setIsRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-[#009b87]" />
          <h2 className="text-lg font-semibold text-gray-900">Client Portal</h2>
          {portalSync.portal_enabled && hasRecentActivity && (
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {portalSync.portal_enabled && onRefresh && (
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
              title="Refresh sync status"
            >
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
          {portalSync.portal_enabled && (
            <a
              href={`http://localhost:3001/${projectId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-[#009b87] transition-colors"
              title="Open Portal"
            >
              <ExternalLink className="w-4 h-4" />
            </a>
          )}
        </div>
      </div>

      {/* Portal Status */}
      <div className="mb-4">
        {portalSync.portal_enabled ? (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
              <CheckCircle className="w-3 h-3" />
              Enabled
            </span>
            <span className="text-xs text-gray-500 capitalize">
              {phaseLabels[portalSync.portal_phase] || portalSync.portal_phase}
            </span>
          </div>
        ) : (
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
            <Clock className="w-3 h-3" />
            Not Enabled
          </span>
        )}
      </div>

      {/* Main content - grows to fill space */}
      <div className="flex-1">
        {portalSync.portal_enabled ? (
          <div className="space-y-4">
            {/* Clients row */}
            <div className="flex items-center justify-between text-sm pb-3 border-b border-gray-100">
              <span className="text-gray-500 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Clients
              </span>
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-900">
                  {portalSync.clients_active}/{portalSync.clients_invited}
                  <span className="text-gray-400 font-normal ml-1">active</span>
                </span>
                {onInviteClient && (
                  <button
                    onClick={onInviteClient}
                    className="p-1 text-[#009b87] hover:bg-[#009b87]/10 rounded transition-colors"
                    title="Invite client"
                  >
                    <UserPlus className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>

            {/* Sync progress indicator */}
            {hasActivity ? (
              <PortalSyncIndicator
                questions={portalSync.questions}
                documents={portalSync.documents}
                lastClientActivity={portalSync.last_client_activity}
                isRefreshing={isRefreshing}
              />
            ) : (
              <div className="py-4 text-center">
                <AlertCircle className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No items sent yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  Send discovery prep to start
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="py-4 text-center">
            <Mail className="w-10 h-10 text-gray-300 mx-auto mb-3" />
            <p className="text-sm text-gray-600 mb-1">
              Enable the client portal
            </p>
            <p className="text-xs text-gray-400">
              Invite clients to prepare for discovery calls
            </p>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="mt-4 pt-4 border-t border-gray-100 space-y-2">
        {portalSync.portal_enabled ? (
          <>
            <button
              onClick={onInviteClient}
              className="w-full px-4 py-2 text-sm font-medium text-white bg-[#009b87] rounded-lg hover:bg-[#008775] transition-colors flex items-center justify-center gap-2"
            >
              <UserPlus className="w-4 h-4" />
              Invite Client
            </button>
            <button
              onClick={onManagePortal}
              className="w-full px-4 py-2 text-sm font-medium text-[#009b87] bg-[#009b87]/10 rounded-lg hover:bg-[#009b87]/20 transition-colors"
            >
              Manage Portal
            </button>
          </>
        ) : (
          <button
            onClick={onEnablePortal}
            className="w-full px-4 py-2 text-sm font-medium text-white bg-[#009b87] rounded-lg hover:bg-[#008775] transition-colors"
          >
            Enable Portal
          </button>
        )}
      </div>
    </div>
  )
}

export default ClientPortalCard
