/**
 * CollaborationTab Component
 *
 * Phase-aware interface for client collaboration:
 * - Client portal management (compact card)
 * - Discovery preparation (pre-discovery phase)
 * - Pending validation tasks (post-discovery phase)
 * - Pending proposals
 * - Touchpoint history (completed collaboration events)
 */

'use client'

import React, { useState, useEffect } from 'react'
import {
  getPortalConfig,
  listProposals,
  applyProposal,
  discardProposal,
} from '@/lib/api'
import {
  Loader2,
  Layers,
  UserCheck,
  History,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  ExternalLink,
  Users,
  Mail,
} from 'lucide-react'
import ClientPortalSection from '../ClientPortalSection'
import { DiscoveryPrepSection } from '../discovery-prep'
import { ProposalPreview } from '../ProposalPreview'
import { TaskList } from '@/components/tasks'

interface CollaborationTabProps {
  projectId: string
  projectName?: string
}

export function CollaborationTab({ projectId, projectName = 'Project' }: CollaborationTabProps) {
  const [loading, setLoading] = useState(true)
  const [portalEnabled, setPortalEnabled] = useState(false)

  // Proposal state
  const [proposals, setProposals] = useState<any[]>([])
  const [applyingProposal, setApplyingProposal] = useState<string | null>(null)

  // Task refresh state
  const [taskRefreshKey, setTaskRefreshKey] = useState(0)

  // UI state
  const [showHistory, setShowHistory] = useState(false)

  // Load data on mount
  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      const [portalConfig, proposalsData] = await Promise.all([
        getPortalConfig(projectId).catch(() => ({ portal_enabled: false })),
        listProposals(projectId, 'pending').catch(() => ({ proposals: [] })),
      ])
      setPortalEnabled(portalConfig.portal_enabled)
      setProposals(proposalsData.proposals || [])
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Proposal handlers
  const handleApplyProposal = async (proposalId: string) => {
    try {
      setApplyingProposal(proposalId)
      await applyProposal(proposalId)
      await loadData()
      window.location.reload()
    } catch (error) {
      console.error('Failed to apply proposal:', error)
      alert('Failed to apply proposal')
    } finally {
      setApplyingProposal(null)
    }
  }

  const handleDiscardProposal = async (proposalId: string) => {
    try {
      await discardProposal(proposalId)
      await loadData()
    } catch (error) {
      console.error('Failed to discard proposal:', error)
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

  return (
    <div className="space-y-6">
      {/* Top Row: Tasks (2/3) + Client Portal (1/3) - matching Overview layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Pending Validation - Takes 2 columns */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <UserCheck className="w-5 h-5 text-[#009b87]" />
            <h2 className="text-lg font-semibold text-gray-900">Pending Validation</h2>
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

        {/* Client Portal Card - Compact version */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-2 mb-4">
            <Mail className="w-5 h-5 text-[#009b87]" />
            <h2 className="text-lg font-semibold text-gray-900">Client Portal</h2>
          </div>

          {/* Portal Status */}
          <div className="mb-4">
            {portalEnabled ? (
              <div className="flex items-center gap-2 text-sm">
                <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  <CheckCircle className="w-3 h-3" />
                  Enabled
                </span>
              </div>
            ) : (
              <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-600">
                Not Enabled
              </span>
            )}
          </div>

          {/* Quick Stats */}
          <div className="space-y-3 mb-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-500 flex items-center gap-2">
                <Users className="w-4 h-4" />
                Clients invited
              </span>
              <span className="font-medium text-gray-900">-</span>
            </div>
          </div>

          {/* Action */}
          <a
            href={`/projects/${projectId}?tab=collaboration&section=portal`}
            className="block w-full text-center px-4 py-2 text-sm font-medium text-[#009b87] bg-[#009b87]/10 rounded-lg hover:bg-[#009b87]/20 transition-colors"
          >
            Manage Portal
          </a>
        </div>
      </div>

      {/* Discovery Prep Section - Full Width */}
      <div className="bg-white rounded-xl border border-gray-200">
        <DiscoveryPrepSection
          projectId={projectId}
          projectName={projectName}
          portalEnabled={portalEnabled}
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
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-gray-400" />
            <h2 className="text-lg font-semibold text-gray-900">Collaboration History</h2>
          </div>
          {showHistory ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </button>

        {showHistory && (
          <div className="border-t border-gray-100 p-4">
            <div className="text-center py-8 text-gray-500">
              <History className="w-10 h-10 text-gray-300 mx-auto mb-3" />
              <p className="text-sm">No completed touchpoints yet.</p>
              <p className="text-xs text-gray-400 mt-1">
                Completed discovery calls and validation rounds will appear here.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Full Client Portal Section - Hidden by default, shown when managing */}
      <div className="hidden">
        <ClientPortalSection projectId={projectId} projectName={projectName} />
      </div>
    </div>
  )
}
