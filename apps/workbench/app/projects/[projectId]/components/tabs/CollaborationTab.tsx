/**
 * CollaborationTab Component
 *
 * Phase-aware interface for client collaboration:
 * - Current focus section (changes based on phase)
 * - Client portal card with sync status
 * - Discovery preparation
 * - Pending validation tasks
 * - Pending proposals
 * - Touchpoint history (completed collaboration events)
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  getPortalConfig,
  listProposals,
  applyProposal,
  discardProposal,
  getCollaborationCurrent,
  updatePortalConfig,
  type CollaborationCurrentResponse,
} from '@/lib/api'
import {
  Loader2,
  Layers,
  UserCheck,
  AlertCircle,
} from 'lucide-react'
import { DiscoveryPrepSection } from '../discovery-prep'
import { ProposalPreview } from '../ProposalPreview'
import { TaskList } from '@/components/tasks'
import {
  CurrentFocusSection,
  ClientPortalCard,
  TouchpointHistory,
} from '@/components/collaboration'

interface CollaborationTabProps {
  projectId: string
  projectName?: string
}

export function CollaborationTab({ projectId, projectName = 'Project' }: CollaborationTabProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Collaboration state from API
  const [collaborationState, setCollaborationState] = useState<CollaborationCurrentResponse | null>(null)

  // Proposal state
  const [proposals, setProposals] = useState<any[]>([])
  const [applyingProposal, setApplyingProposal] = useState<string | null>(null)

  // Task refresh state
  const [taskRefreshKey, setTaskRefreshKey] = useState(0)

  // Load data on mount
  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const [collabData, proposalsData] = await Promise.all([
        getCollaborationCurrent(projectId).catch((err) => {
          console.warn('Collaboration API not available:', err)
          return null
        }),
        listProposals(projectId, 'pending').catch(() => ({ proposals: [] })),
      ])

      setCollaborationState(collabData)
      setProposals(proposalsData.proposals || [])
    } catch (err) {
      console.error('Failed to load data:', err)
      setError('Failed to load collaboration data')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  // Enable portal handler
  const handleEnablePortal = async () => {
    try {
      await updatePortalConfig(projectId, { portal_enabled: true })
      await loadData()
    } catch (err) {
      console.error('Failed to enable portal:', err)
    }
  }

  // Refresh collaboration sync (without full loading state)
  const handleRefreshSync = async () => {
    try {
      const collabData = await getCollaborationCurrent(projectId)
      setCollaborationState(collabData)
    } catch (err) {
      console.error('Failed to refresh sync:', err)
    }
  }

  // Proposal handlers
  const handleApplyProposal = async (proposalId: string) => {
    try {
      setApplyingProposal(proposalId)
      await applyProposal(proposalId)
      await loadData()
      window.location.reload()
    } catch (err) {
      console.error('Failed to apply proposal:', err)
      alert('Failed to apply proposal')
    } finally {
      setApplyingProposal(null)
    }
  }

  const handleDiscardProposal = async (proposalId: string) => {
    try {
      await discardProposal(proposalId)
      await loadData()
    } catch (err) {
      console.error('Failed to discard proposal:', err)
      alert('Failed to discard proposal')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#009b87] mx-auto mb-3" />
          <p className="text-gray-500">Loading collaboration data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <p className="text-red-600">{error}</p>
          <button
            onClick={loadData}
            className="mt-4 px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  // Use collaboration state if available, otherwise fall back to defaults
  const portalSync = collaborationState?.portal_sync || {
    portal_enabled: false,
    portal_phase: 'pre_call',
    questions: { sent: 0, completed: 0, in_progress: 0, pending: 0 },
    documents: { sent: 0, completed: 0, in_progress: 0, pending: 0 },
    last_client_activity: null,
    clients_invited: 0,
    clients_active: 0,
  }

  const currentFocus = collaborationState?.current_focus || {
    phase: 'pre_discovery',
    primary_action: 'Generate discovery call preparation',
    discovery_prep: {
      status: 'not_generated',
      questions_total: 0,
      questions_confirmed: 0,
      questions_answered: 0,
      documents_total: 0,
      documents_confirmed: 0,
      documents_received: 0,
      can_send: false,
    },
  }

  const phase = collaborationState?.collaboration_phase || 'pre_discovery'
  const isPreDiscovery = phase === 'pre_discovery' || phase === 'discovery'

  return (
    <div className="space-y-6">
      {/* Top Row: Current Focus (2/3) + Client Portal (1/3) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Current Focus - Takes 2 columns */}
        <div className="lg:col-span-2">
          <CurrentFocusSection currentFocus={currentFocus} />
        </div>

        {/* Client Portal Card */}
        <ClientPortalCard
          projectId={projectId}
          portalSync={portalSync}
          onManagePortal={() => {
            // Scroll to discovery prep section for now
            document.getElementById('discovery-prep')?.scrollIntoView({ behavior: 'smooth' })
          }}
          onEnablePortal={handleEnablePortal}
          onRefresh={handleRefreshSync}
        />
      </div>

      {/* Discovery Prep Section - Full Width (primarily for pre-discovery) */}
      {isPreDiscovery && (
        <div id="discovery-prep">
          <DiscoveryPrepSection
            projectId={projectId}
            projectName={projectName}
            portalEnabled={portalSync.portal_enabled}
          />
        </div>
      )}

      {/* Pending Validation - Full Width (primarily for post-discovery) */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center gap-2 mb-4">
          <UserCheck className="w-5 h-5 text-[#009b87]" />
          <h2 className="text-lg font-semibold text-gray-900">Pending Validation</h2>
          {collaborationState?.pending_validation_count ? (
            <span className="text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
              {collaborationState.pending_validation_count}
            </span>
          ) : null}
        </div>
        <p className="text-sm text-gray-600 mb-4">
          Tasks that need client review or confirmation before proceeding.
        </p>
        <TaskList
          projectId={projectId}
          initialFilter="client"
          showFilters={false}
          showBulkActions={true}
          compact={false}
          maxItems={8}
          refreshKey={taskRefreshKey}
          onTasksChange={() => setTaskRefreshKey(k => k + 1)}
        />
      </div>

      {/* Pending Proposals - Full Width (if any) */}
      {proposals.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-5 h-5 text-[#009b87]" />
            <h2 className="text-lg font-semibold text-gray-900">Pending Proposals</h2>
            <span className="text-sm text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">
              {proposals.length}
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Review and apply changes extracted from signals.
          </p>

          <div className="space-y-4">
            {proposals.map((proposal) => (
              <ProposalPreview
                key={proposal.id}
                proposal={{
                  proposal_id: proposal.id,
                  title: proposal.title || 'Untitled Proposal',
                  description: proposal.description,
                  status: proposal.status,
                  creates: proposal.creates_count || 0,
                  updates: proposal.updates_count || 0,
                  deletes: proposal.deletes_count || 0,
                  total_changes: proposal.total_changes || 0,
                  changes_by_type: proposal.changes_by_type,
                }}
                onApply={handleApplyProposal}
                onDiscard={handleDiscardProposal}
                isApplying={applyingProposal === proposal.id}
              />
            ))}
          </div>
        </div>
      )}

      {/* Touchpoint History - Expandable */}
      <TouchpointHistory projectId={projectId} />
    </div>
  )
}
