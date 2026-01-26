/**
 * ClientPortalCard Component
 *
 * Compact card showing client portal status and sync information.
 * Similar in size to the Upcoming Meetings card in Overview.
 */

'use client'

import React from 'react'
import {
  Mail,
  Users,
  CheckCircle,
  Clock,
  ExternalLink,
  MessageSquare,
  FileText,
  AlertCircle,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

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
  confirmations: PortalItemSync
  last_client_activity: string | null
  clients_invited: number
  clients_active: number
}

interface ClientPortalCardProps {
  projectId: string
  portalSync: PortalSyncStatus
  onManagePortal?: () => void
  onEnablePortal?: () => void
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
}: ClientPortalCardProps) {
  const totalQuestionsSent = portalSync.questions.sent
  const questionsAnswered = portalSync.questions.completed
  const totalDocsSent = portalSync.documents.sent
  const docsReceived = portalSync.documents.completed

  const hasActivity = totalQuestionsSent > 0 || totalDocsSent > 0
  const lastActivity = portalSync.last_client_activity
    ? formatDistanceToNow(new Date(portalSync.last_client_activity), { addSuffix: true })
    : null

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Mail className="w-5 h-5 text-[#009b87]" />
          <h2 className="text-lg font-semibold text-gray-900">Client Portal</h2>
        </div>
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
          <div className="space-y-3">
            {/* Clients */}
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Clients
              </span>
              <span className="font-medium text-gray-900">
                {portalSync.clients_active}/{portalSync.clients_invited}
                <span className="text-gray-400 font-normal ml-1">active</span>
              </span>
            </div>

            {/* Questions sync */}
            {totalQuestionsSent > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500 flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  Questions
                </span>
                <span className="font-medium text-gray-900">
                  {questionsAnswered}/{totalQuestionsSent}
                  <span className="text-gray-400 font-normal ml-1">answered</span>
                </span>
              </div>
            )}

            {/* Documents sync */}
            {totalDocsSent > 0 && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-500 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Documents
                </span>
                <span className="font-medium text-gray-900">
                  {docsReceived}/{totalDocsSent}
                  <span className="text-gray-400 font-normal ml-1">received</span>
                </span>
              </div>
            )}

            {/* No activity yet */}
            {!hasActivity && (
              <div className="py-4 text-center">
                <AlertCircle className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm text-gray-500">No items sent yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  Send discovery prep to start
                </p>
              </div>
            )}

            {/* Last activity */}
            {lastActivity && (
              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs text-gray-400">
                  Last activity {lastActivity}
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

      {/* Action button */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        {portalSync.portal_enabled ? (
          <button
            onClick={onManagePortal}
            className="w-full px-4 py-2 text-sm font-medium text-[#009b87] bg-[#009b87]/10 rounded-lg hover:bg-[#009b87]/20 transition-colors"
          >
            Manage Portal
          </button>
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
