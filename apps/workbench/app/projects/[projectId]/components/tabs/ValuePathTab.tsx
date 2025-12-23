/**
 * ValuePathTab Component
 *
 * Tab 2: Value Path (VP Steps)
 *
 * Purpose: Expand into step-level clarity
 * - Ordered VP steps with enrichment details
 * - Data schema, business logic, transition logic
 * - Status tracking and confirmation workflow
 */

'use client'

import React, { useState, useEffect } from 'react'
import { TwoColumnLayout } from '@/components/ui'
import { VpList, VpDetail } from './vp'
import { getVpSteps, updateVpStepStatus, getSignal, getSignalChunks } from '@/lib/api'
import type { VpStep, Signal, SignalChunk } from '@/types/api'

interface ValuePathTabProps {
  projectId: string
}

export function ValuePathTab({ projectId }: ValuePathTabProps) {
  const [steps, setSteps] = useState<VpStep[]>([])
  const [selectedStep, setSelectedStep] = useState<VpStep | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)

  // Evidence modal state
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [signalChunks, setSignalChunks] = useState<SignalChunk[]>([])

  // Load VP steps on mount
  useEffect(() => {
    loadSteps()
  }, [projectId])

  const loadSteps = async () => {
    try {
      setLoading(true)
      console.log('🔄 Loading VP steps...')
      const data = await getVpSteps(projectId)
      console.log('✅ Loaded VP steps:', data.length)

      // Sort by step_index
      const sortedData = [...data].sort((a, b) => a.step_index - b.step_index)
      setSteps(sortedData)

      // Auto-select first step if none selected
      if (!selectedStep && sortedData.length > 0) {
        setSelectedStep(sortedData[0])
      }
    } catch (error) {
      console.error('❌ Failed to load VP steps:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle step selection
  const handleSelectStep = (step: VpStep) => {
    setSelectedStep(step)
  }

  // Handle status update
  const handleStatusUpdate = async (stepId: string, newStatus: string) => {
    try {
      setUpdating(true)
      console.log('🔄 Updating step status:', { stepId, newStatus })

      const updated = await updateVpStepStatus(stepId, newStatus)
      console.log('✅ Step status updated:', updated)

      // Update local state
      setSteps(prev => prev.map(s => s.id === stepId ? { ...s, status: newStatus } : s))
      if (selectedStep?.id === stepId) {
        setSelectedStep({ ...selectedStep, status: newStatus })
      }
    } catch (error) {
      console.error('❌ Failed to update step status:', error)
      alert('Failed to update step status')
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
          <p className="text-support text-ui-supportText">Loading VP steps...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="p-6">
        <TwoColumnLayout
          left={
            <VpList
              steps={steps}
              selectedId={selectedStep?.id || null}
              onSelect={handleSelectStep}
            />
          }
          right={
            <VpDetail
              step={selectedStep}
              onStatusUpdate={handleStatusUpdate}
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
