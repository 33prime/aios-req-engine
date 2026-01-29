/**
 * CollaborationTab Component
 *
 * Clean layout:
 * 1. Phase Progress Timeline
 * 2. Three cards: Client Portal | Pending Queue | History (click → modal)
 * 3. Phase Prep (Discovery Call Prep, etc.)
 * 4. Draft/Sent Package
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  getPhaseProgress,
  generateClientPackage,
  updateClientPackage,
  sendClientPackage,
  removePendingItem,
  updatePortalConfig,
} from '@/lib/api'
import {
  Loader2,
  AlertCircle,
  Mail,
  ClipboardList,
  History,
  ChevronRight,
  X,
  Plus,
} from 'lucide-react'
import {
  PhaseProgress,
  PendingQueue,
  PackagePreview,
  PackageEditor,
  TouchpointHistory,
} from '@/components/collaboration'
import { DiscoveryPrepSection } from '../discovery-prep'
import ClientPortalSection from '../ClientPortalSection'
import { CreateTouchpointModal } from '../CreateTouchpointModal'
import type { PhaseProgressResponse } from '@/types/api'

interface CollaborationTabProps {
  projectId: string
  projectName?: string
}

export function CollaborationTab({ projectId, projectName = 'Project' }: CollaborationTabProps) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [progressData, setProgressData] = useState<PhaseProgressResponse | null>(null)

  // Package editing state
  const [editingPackage, setEditingPackage] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isSending, setIsSending] = useState(false)

  // Modal states
  const [portalModalOpen, setPortalModalOpen] = useState(false)
  const [queueModalOpen, setQueueModalOpen] = useState(false)
  const [historyModalOpen, setHistoryModalOpen] = useState(false)
  const [createTouchpointOpen, setCreateTouchpointOpen] = useState(false)

  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await getPhaseProgress(projectId)
      setProgressData(data)
    } catch (err: any) {
      console.error('Failed to load data:', err)
      setError(err.message || 'Failed to load collaboration data')
    } finally {
      setLoading(false)
    }
  }, [projectId])

  const handleGeneratePackage = async (itemIds?: string[]) => {
    try {
      setIsGenerating(true)
      await generateClientPackage(projectId, {
        item_ids: itemIds,
        max_questions: 5,
        include_asset_suggestions: true,
      })
      await loadData()
      setQueueModalOpen(false)
    } catch (err: any) {
      console.error('Failed to generate package:', err)
      alert(err.message || 'Failed to generate client questions')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRemoveItem = async (itemId: string) => {
    try {
      await removePendingItem(itemId)
      await loadData()
    } catch (err) {
      console.error('Failed to remove item:', err)
    }
  }

  const handleEditPackage = () => setEditingPackage(true)
  const handleCancelEdit = () => setEditingPackage(false)

  const handleSavePackage = async (updates: { questions?: any[]; action_items?: any[] }) => {
    if (!progressData?.draft_package?.id) return
    try {
      setIsSaving(true)
      await updateClientPackage(progressData.draft_package.id, updates)
      await loadData()
      setEditingPackage(false)
    } catch (err: any) {
      console.error('Failed to save package:', err)
      alert(err.message || 'Failed to save changes')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSendPackage = async () => {
    if (!progressData?.draft_package?.id) return
    if (!confirm('Send this package to the client portal? Clients will be notified.')) return
    try {
      setIsSending(true)
      await sendClientPackage(progressData.draft_package.id)
      await loadData()
    } catch (err: any) {
      console.error('Failed to send package:', err)
      alert(err.message || 'Failed to send package')
    } finally {
      setIsSending(false)
    }
  }

  const handleEnablePortal = async () => {
    try {
      await updatePortalConfig(projectId, { portal_enabled: true })
      await loadData()
      setPortalModalOpen(true)
    } catch (err) {
      console.error('Failed to enable portal:', err)
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
          <button onClick={loadData} className="mt-4 px-4 py-2 text-sm text-gray-600 hover:text-gray-900">
            Try again
          </button>
        </div>
      </div>
    )
  }

  if (!progressData) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-gray-500">No collaboration data available</p>
      </div>
    )
  }

  const {
    current_phase,
    phases,
    phase_config,
    readiness_score,
    pending_queue,
    draft_package,
    sent_package,
    portal_enabled,
    clients_count,
  } = progressData

  const isDiscoveryPhase = current_phase === 'pre_discovery' || current_phase === 'discovery'

  return (
    <div className="space-y-6">
      {/* 1. Phase Progress Timeline */}
      <PhaseProgress
        currentPhase={current_phase}
        phases={phases}
        phaseConfig={phase_config}
        readinessScore={readiness_score}
      />

      {/* 2. Three Cards: Portal | Queue | History */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Client Portal Card */}
        <button
          onClick={() => portal_enabled ? setPortalModalOpen(true) : handleEnablePortal()}
          className="bg-white rounded-xl border border-gray-200 p-4 hover:border-[#009b87]/50 hover:shadow-sm transition-all text-left"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                portal_enabled ? 'bg-[#009b87]' : 'bg-gray-200'
              }`}>
                <Mail className={`w-5 h-5 ${portal_enabled ? 'text-white' : 'text-gray-500'}`} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Client Portal</h3>
                <p className="text-sm text-gray-500">
                  {portal_enabled ? `${clients_count} client${clients_count !== 1 ? 's' : ''} invited` : 'Click to enable'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {portal_enabled && <span className="w-2 h-2 rounded-full bg-[#009b87]" />}
              <ChevronRight className="w-5 h-5 text-gray-400" />
            </div>
          </div>
        </button>

        {/* Pending Queue Card */}
        <button
          onClick={() => setQueueModalOpen(true)}
          className="bg-white rounded-xl border border-gray-200 p-4 hover:border-[#009b87]/50 hover:shadow-sm transition-all text-left"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                pending_queue.total_count > 0 ? 'bg-[#009b87]' : 'bg-gray-200'
              }`}>
                <ClipboardList className={`w-5 h-5 ${pending_queue.total_count > 0 ? 'text-white' : 'text-gray-500'}`} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">Pending Queue</h3>
                <p className="text-sm text-gray-500">
                  {pending_queue.total_count > 0
                    ? `${pending_queue.total_count} item${pending_queue.total_count !== 1 ? 's' : ''} need input`
                    : 'No items pending'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {pending_queue.total_count > 0 && (
                <span className="px-2 py-0.5 text-xs font-medium bg-[#009b87]/10 text-[#009b87] rounded-full">
                  {pending_queue.total_count}
                </span>
              )}
              <ChevronRight className="w-5 h-5 text-gray-400" />
            </div>
          </div>
        </button>

        {/* History Card */}
        <button
          onClick={() => setHistoryModalOpen(true)}
          className="bg-white rounded-xl border border-gray-200 p-4 hover:border-gray-300 hover:shadow-sm transition-all text-left"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-gray-100">
                <History className="w-5 h-5 text-gray-500" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900">History</h3>
                <p className="text-sm text-gray-500">Past touchpoints</p>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-gray-400" />
          </div>
        </button>
      </div>

      {/* New Touchpoint Button */}
      <button
        onClick={() => setCreateTouchpointOpen(true)}
        className="w-full bg-white rounded-xl border-2 border-dashed border-gray-300 p-4 hover:border-[#009b87] hover:bg-[#009b87]/5 transition-all"
      >
        <div className="flex items-center justify-center gap-2 text-gray-500 hover:text-[#009b87]">
          <Plus className="w-5 h-5" />
          <span className="font-medium">Create New Touchpoint</span>
        </div>
      </button>

      {/* 3. Phase Prep */}
      {isDiscoveryPhase ? (
        <DiscoveryPrepSection
          projectId={projectId}
          projectName={projectName}
          portalEnabled={portal_enabled}
        />
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-[#009b87]/10 rounded-lg flex items-center justify-center">
              <ClipboardList className="w-5 h-5 text-[#009b87]" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-900">
                {current_phase === 'validation' ? 'Validation Prep' :
                 current_phase === 'prototype' ? 'Prototype Review Prep' :
                 current_phase === 'proposal' ? 'Proposal Prep' :
                 'Phase Prep'}
              </h3>
              <p className="text-sm text-gray-500">Prepare materials for this phase</p>
            </div>
          </div>
          <p className="text-gray-500 text-sm">Phase-specific preparation tools coming soon.</p>
        </div>
      )}

      {/* 4. Draft/Sent Package */}
      {draft_package && (
        <div>
          {editingPackage ? (
            <PackageEditor
              package_={draft_package}
              onSave={handleSavePackage}
              onCancel={handleCancelEdit}
              isSaving={isSaving}
            />
          ) : (
            <PackagePreview
              package_={draft_package}
              onEdit={handleEditPackage}
              onSend={handleSendPackage}
              isSending={isSending}
            />
          )}
        </div>
      )}

      {sent_package && !draft_package && (
        <PackagePreview package_={sent_package} />
      )}

      {/* ============ MODALS ============ */}

      {/* Client Portal Modal */}
      {portalModalOpen && (
        <Modal title="Client Portal" onClose={() => setPortalModalOpen(false)}>
          <ClientPortalSection
            projectId={projectId}
            projectName={projectName}
            onPhaseChange={loadData}
          />
        </Modal>
      )}

      {/* Pending Queue Modal */}
      {queueModalOpen && (
        <Modal title="Pending Input Queue" onClose={() => setQueueModalOpen(false)} size="lg">
          <PendingQueue
            queue={pending_queue}
            onGeneratePackage={handleGeneratePackage}
            onRemoveItem={handleRemoveItem}
            isGenerating={isGenerating}
          />
        </Modal>
      )}

      {/* History Modal */}
      {historyModalOpen && (
        <Modal title="Collaboration History" onClose={() => setHistoryModalOpen(false)} size="lg">
          <TouchpointHistory projectId={projectId} defaultExpanded={true} />
        </Modal>
      )}

      {/* Create Touchpoint Modal */}
      {createTouchpointOpen && (
        <CreateTouchpointModal
          projectId={projectId}
          onClose={() => setCreateTouchpointOpen(false)}
          onCreated={loadData}
        />
      )}
    </div>
  )
}

// ============================================================================
// Modal Component
// ============================================================================

interface ModalProps {
  title: string
  children: React.ReactNode
  onClose: () => void
  size?: 'sm' | 'md' | 'lg'
}

function Modal({ title, children, onClose, size = 'md' }: ModalProps) {
  const sizeClasses = {
    sm: 'max-w-md',
    md: 'max-w-2xl',
    lg: 'max-w-4xl',
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className={`relative bg-white rounded-xl shadow-2xl w-full ${sizeClasses[size]} max-h-[85vh] overflow-hidden flex flex-col`}>
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </div>
    </div>
  )
}
