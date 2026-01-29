/**
 * ValuePathTab Component
 *
 * The Golden Path - showing how the system creates value.
 *
 * Layout:
 * - Top: Journey Flow (connected cards showing the path)
 * - Bottom Left: Step Detail (expanded selected step)
 * - Bottom Right: Path Summary (insights across the entire path)
 */

'use client'

import React, { useState, useEffect } from 'react'
import { VpJourneyFlow } from './vp/VpJourneyFlow'
import { VpPathSummary } from './vp/VpPathSummary'
import { VpDetail } from './vp'
import { getVpSteps, updateVpStepStatus, getSignal, getSignalChunks, getPersonas, markEntityNeedsReview } from '@/lib/api'
import type { VpStep, Signal, SignalChunk } from '@/types/api'
import type { Persona } from '@/lib/persona-utils'
import { Zap, Loader2, Download } from 'lucide-react'

interface ValuePathTabProps {
  projectId: string
}

export function ValuePathTab({ projectId }: ValuePathTabProps) {
  const [steps, setSteps] = useState<VpStep[]>([])
  const [personas, setPersonas] = useState<Persona[]>([])
  const [selectedStep, setSelectedStep] = useState<VpStep | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)

  // Evidence modal state
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [signalChunks, setSignalChunks] = useState<SignalChunk[]>([])

  // Load VP steps and personas on mount
  useEffect(() => {
    loadData()
  }, [projectId])

  const loadData = async () => {
    try {
      setLoading(true)
      const [stepsData, personasData] = await Promise.all([
        getVpSteps(projectId),
        getPersonas(projectId)
      ])

      setPersonas(personasData || [])

      // Create persona lookup map
      const personaMap = new Map<string, string>()
      personasData?.forEach((p: Persona) => {
        if (p.id) personaMap.set(p.id, p.name)
      })

      // Enrich steps with persona names
      const enrichedSteps = stepsData.map((step: VpStep) => ({
        ...step,
        actor_persona_name: step.actor_persona_name ||
          (step.actor_persona_id ? personaMap.get(step.actor_persona_id) : null) ||
          null
      }))

      // Sort by step_index
      const sortedData = [...enrichedSteps].sort((a, b) => a.step_index - b.step_index)
      setSteps(sortedData)

      // Auto-select first step if none selected
      if (!selectedStep && sortedData.length > 0) {
        setSelectedStep(sortedData[0])
      }
    } catch (error) {
      console.error('Failed to load VP data:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle step selection
  const handleSelectStep = (step: VpStep) => {
    setSelectedStep(step)
  }

  // Handle selection from summary (by ID)
  const handleSelectStepById = (stepId: string) => {
    const step = steps.find(s => s.id === stepId)
    if (step) {
      setSelectedStep(step)
    }
  }

  // Handle status update
  const handleStatusUpdate = async (stepId: string, newStatus: string) => {
    try {
      setUpdating(true)

      // Use markEntityNeedsReview for needs_client to add to pending queue
      if (newStatus === 'needs_client') {
        await markEntityNeedsReview(projectId, 'vp_step', stepId)
      } else {
        await updateVpStepStatus(stepId, newStatus)
      }

      // Update local state
      setSteps(prev => prev.map(s =>
        s.id === stepId
          ? { ...s, status: newStatus, confirmation_status: newStatus as any }
          : s
      ))
      if (selectedStep?.id === stepId) {
        setSelectedStep({ ...selectedStep, status: newStatus, confirmation_status: newStatus as any })
      }
    } catch (error) {
      console.error('Failed to update step status:', error)
      alert('Failed to update step status')
    } finally {
      setUpdating(false)
    }
  }

  // Handle evidence viewing
  const handleViewEvidence = async (chunkId: string) => {
    try {
      const signalId = chunkId.split('-')[0]

      const [signal, chunks] = await Promise.all([
        getSignal(signalId),
        getSignalChunks(signalId),
      ])

      setSelectedSignal(signal)
      setSignalChunks(chunks.chunks)
    } catch (error) {
      console.error('Failed to load evidence:', error)
      alert('Failed to load evidence details')
    }
  }

  // Close evidence modal
  const handleCloseEvidence = () => {
    setSelectedSignal(null)
    setSignalChunks([])
  }

  // Calculate stats for header
  const confirmedCount = steps.filter(s => {
    const status = s.confirmation_status || s.status
    return status === 'confirmed_consultant' || status === 'confirmed_client'
  }).length

  // Determine path status
  const isPathComplete = steps.length > 0 && confirmedCount === steps.length
  const pathTitle = steps.length > 0 ? 'Primary Value Path' : 'Value Path'
  const pathDescription = steps.length > 0
    ? `End-to-end journey showing how ${steps[0]?.actor_persona_name || 'users'} create value through the system`
    : 'The golden path showing how users flow through the system to create value'

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#009b87] mx-auto mb-3" />
          <p className="text-gray-500">Loading Value Path...</p>
        </div>
      </div>
    )
  }

  if (steps.length === 0) {
    return (
      <div className="p-8">
        <div className="text-center py-16 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
          <Zap className="h-16 w-16 text-gray-300 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-gray-900 mb-2">No Value Path Yet</h2>
          <p className="text-gray-500 mb-4 max-w-md mx-auto">
            The Value Path is your "golden path" showing how users flow through the system to create value.
            It combines personas, features, and evidence into a demo-ready narrative.
          </p>
          <p className="text-[#009b87] text-sm">
            Ask the AI assistant to "generate the value path" to get started.
          </p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-2">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">{pathTitle}</h1>
            <p className="text-base text-gray-600">{pathDescription}</p>
            <p className="text-sm text-gray-500 mt-1">
              {steps.length} steps • {confirmedCount} confirmed
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-3 py-1 text-sm font-medium rounded-full ${
              isPathComplete
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-600'
            }`}>
              {isPathComplete ? 'Active' : 'Draft'}
            </span>
            <button className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2">
              <Download className="w-4 h-4" />
              Export
            </button>
          </div>
        </div>

        {/* Journey Flow (Connected Cards) */}
        <VpJourneyFlow
          steps={steps}
          selectedId={selectedStep?.id || null}
          onSelect={handleSelectStep}
        />

        {/* Bottom Section: Detail + Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Step Detail (Left/Main) */}
          <div className="lg:col-span-8">
            <VpDetail
              step={selectedStep}
              onStatusUpdate={handleStatusUpdate}
              onViewEvidence={handleViewEvidence}
              updating={updating}
            />
          </div>

          {/* Path Summary (Right Sidebar) */}
          <div className="lg:col-span-4">
            <div className="sticky top-6">
              <VpPathSummary
                steps={steps}
                onSelectStep={handleSelectStepById}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Evidence Modal */}
      {selectedSignal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[80vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">Evidence Source</h3>
                <button
                  onClick={handleCloseEvidence}
                  className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
                >
                  ×
                </button>
              </div>
              <div className="mt-3 space-y-1 text-sm text-gray-500">
                <p><strong>Source:</strong> {selectedSignal.source}</p>
                <p><strong>Type:</strong> {selectedSignal.signal_type}</p>
                <p><strong>Date:</strong> {new Date(selectedSignal.created_at).toLocaleString()}</p>
              </div>
            </div>

            <div className="p-6 overflow-y-auto max-h-96">
              <div className="space-y-4">
                {signalChunks.map((chunk, idx) => (
                  <div key={idx} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-700">
                        Chunk {chunk.chunk_index + 1}
                      </span>
                      <span className="text-xs text-gray-400">
                        Characters {chunk.start_char}-{chunk.end_char}
                      </span>
                    </div>
                    <p className="text-gray-700">{chunk.content}</p>
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
