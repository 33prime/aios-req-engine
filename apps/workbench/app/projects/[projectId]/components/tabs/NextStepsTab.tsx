/**
 * NextStepsTab Component
 *
 * Tab 4: Next Steps (Client Confirmations)
 *
 * Purpose: Batch client confirmations into one clean outreach
 * - Aggregates all items marked "needs confirmation"
 * - Groups by source (PRD, VP, Insights)
 * - Complexity scoring for meeting recommendations
 * - Status workflow for managing confirmations
 */

'use client'

import React, { useState, useEffect } from 'react'
import { TwoColumnLayout } from '@/components/ui'
import { ConfirmationsList, ConfirmationDetail } from './confirmations'
import { listConfirmations, updateConfirmationStatus, getSignal, getSignalChunks } from '@/lib/api'
import type { Confirmation, Signal, SignalChunk } from '@/types/api'

interface NextStepsTabProps {
  projectId: string
}

export function NextStepsTab({ projectId }: NextStepsTabProps) {
  const [confirmations, setConfirmations] = useState<Confirmation[]>([])
  const [selectedConfirmation, setSelectedConfirmation] = useState<Confirmation | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)

  // Evidence modal state
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [signalChunks, setSignalChunks] = useState<SignalChunk[]>([])

  // Load confirmations on mount
  useEffect(() => {
    loadConfirmations()
  }, [projectId])

  const loadConfirmations = async () => {
    try {
      setLoading(true)
      console.log('🔄 Loading confirmations...')
      const data = await listConfirmations(projectId)
      console.log('✅ Loaded confirmations:', data.confirmations.length)
      setConfirmations(data.confirmations)

      // Auto-select first confirmation if none selected
      if (!selectedConfirmation && data.confirmations.length > 0) {
        setSelectedConfirmation(data.confirmations[0])
      }
    } catch (error) {
      console.error('❌ Failed to load confirmations:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle confirmation selection
  const handleSelectConfirmation = (confirmation: Confirmation) => {
    setSelectedConfirmation(confirmation)
  }

  // Handle Resolve
  const handleResolve = async (confirmationId: string) => {
    try {
      setUpdating(true)
      console.log('🔄 Resolving confirmation:', confirmationId)

      await updateConfirmationStatus(confirmationId, 'resolved', {
        type: 'consultant_review',
        ref: 'confirmed',
        note: 'Confirmed and resolved by consultant',
      })
      console.log('✅ Confirmation resolved')

      // Reload confirmations
      await loadConfirmations()
      alert('Confirmation marked as resolved.')
    } catch (error) {
      console.error('❌ Failed to resolve confirmation:', error)
      alert('Failed to resolve confirmation')
    } finally {
      setUpdating(false)
    }
  }

  // Handle Queue for Meeting
  const handleQueue = async (confirmationId: string) => {
    try {
      setUpdating(true)
      console.log('🔄 Queuing confirmation for meeting:', confirmationId)

      await updateConfirmationStatus(confirmationId, 'queued', {
        type: 'meeting',
        ref: 'queued_for_discussion',
        note: 'Queued for client meeting',
      })
      console.log('✅ Confirmation queued')

      // Reload confirmations
      await loadConfirmations()
      alert('Confirmation queued for meeting.')
    } catch (error) {
      console.error('❌ Failed to queue confirmation:', error)
      alert('Failed to queue confirmation')
    } finally {
      setUpdating(false)
    }
  }

  // Handle Dismiss
  const handleDismiss = async (confirmationId: string) => {
    try {
      setUpdating(true)
      console.log('🔄 Dismissing confirmation:', confirmationId)

      await updateConfirmationStatus(confirmationId, 'dismissed', {
        type: 'consultant_decision',
        ref: 'not_relevant',
        note: 'Dismissed as not relevant',
      })
      console.log('✅ Confirmation dismissed')

      // Reload confirmations
      await loadConfirmations()
      alert('Confirmation dismissed.')
    } catch (error) {
      console.error('❌ Failed to dismiss confirmation:', error)
      alert('Failed to dismiss confirmation')
    } finally {
      setUpdating(false)
    }
  }

  // Handle evidence viewing
  const handleViewEvidence = async (chunkId: string) => {
    try {
      console.log('🔍 Viewing evidence for chunk:', chunkId)
      const signalId = chunkId.split('-')[0]

      const [signal, chunks] = await Promise.all([
        getSignal(signalId),
        getSignalChunks(signalId),
      ])

      console.log('✅ Loaded evidence:', { signal, chunks: chunks.chunks })
      setSelectedSignal(signal)
      setSignalChunks(chunks.chunks)
    } catch (error) {
      console.error('❌ Failed to load evidence:', error)
      alert('Failed to load evidence details')
    }
  }

  // Close evidence modal
  const handleCloseEvidence = () => {
    setSelectedSignal(null)
    setSignalChunks([])
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
          <p className="text-support text-ui-supportText">Loading confirmations...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="p-6">
        <TwoColumnLayout
          left={
            <ConfirmationsList
              confirmations={confirmations}
              selectedId={selectedConfirmation?.id || null}
              onSelect={handleSelectConfirmation}
            />
          }
          right={
            <ConfirmationDetail
              confirmation={selectedConfirmation}
              onResolve={handleResolve}
              onQueue={handleQueue}
              onDismiss={handleDismiss}
              onViewEvidence={handleViewEvidence}
              updating={updating}
            />
          }
          leftWidth="medium"
          stickyLeft={true}
        />
      </div>

      {/* Evidence Modal */}
      {selectedSignal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-ui-cardBorder">
              <div className="flex items-center justify-between">
                <h3 className="heading-2">Evidence Source</h3>
                <button
                  onClick={handleCloseEvidence}
                  className="text-ui-supportText hover:text-ui-bodyText text-2xl leading-none"
                >
                  ×
                </button>
              </div>
              <div className="mt-3 space-y-1 text-support text-ui-supportText">
                <p><strong>Source:</strong> {selectedSignal.source}</p>
                <p><strong>Type:</strong> {selectedSignal.signal_type}</p>
                <p><strong>Date:</strong> {new Date(selectedSignal.created_at).toLocaleString()}</p>
              </div>
            </div>

            <div className="p-6 overflow-y-auto max-h-96">
              <div className="space-y-4">
                {signalChunks.map((chunk, idx) => (
                  <div key={idx} className="border border-ui-cardBorder rounded-lg p-4 bg-ui-background">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-ui-bodyText">
                        Chunk {chunk.chunk_index + 1}
                      </span>
                      <span className="text-xs text-ui-supportText">
                        Characters {chunk.start_char}-{chunk.end_char}
                      </span>
                    </div>
                    <p className="text-body text-ui-bodyText">{chunk.content}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
