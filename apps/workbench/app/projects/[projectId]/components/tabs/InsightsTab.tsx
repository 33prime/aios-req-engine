/**
 * InsightsTab Component
 *
 * Tab 3: Insights (Red Team Analysis)
 *
 * Purpose: Red-team the plan before bothering the client
 * - Shows insights from gap analysis
 * - Consultant can: Apply Internally, Needs Confirmation, or Dismiss
 * - Filterable by severity and gate
 */

'use client'

import React, { useState, useEffect } from 'react'
import { TwoColumnLayout } from '@/components/ui'
import { InsightsList, InsightDetail } from './insights'
import { getInsights, applyInsight, confirmInsight, dismissInsight, getSignal, getSignalChunks } from '@/lib/api'
import type { Insight, Signal, SignalChunk } from '@/types/api'

interface InsightsTabProps {
  projectId: string
}

export function InsightsTab({ projectId }: InsightsTabProps) {
  const [insights, setInsights] = useState<Insight[]>([])
  const [selectedInsight, setSelectedInsight] = useState<Insight | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)

  // Evidence modal state
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [signalChunks, setSignalChunks] = useState<SignalChunk[]>([])

  // Load insights on mount
  useEffect(() => {
    loadInsights()
  }, [projectId])

  const loadInsights = async () => {
    try {
      setLoading(true)
      console.log('🔄 Loading insights...')
      const data = await getInsights(projectId)
      console.log('✅ Loaded insights:', data.length)
      setInsights(data)

      // Auto-select first insight if none selected
      if (!selectedInsight && data.length > 0) {
        setSelectedInsight(data[0])
      }
    } catch (error) {
      console.error('❌ Failed to load insights:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle insight selection
  const handleSelectInsight = (insight: Insight) => {
    setSelectedInsight(insight)
  }

  // Handle Apply Internally
  const handleApplyInternally = async (insightId: string) => {
    try {
      setUpdating(true)
      console.log('🔄 Applying insight internally:', insightId)

      await applyInsight(insightId)
      console.log('✅ Insight applied internally')

      // Reload insights
      await loadInsights()
      alert('Insight applied! The affected entities have been updated.')
    } catch (error) {
      console.error('❌ Failed to apply insight:', error)
      alert('Failed to apply insight')
    } finally {
      setUpdating(false)
    }
  }

  // Handle Needs Confirmation
  const handleNeedsConfirmation = async (insightId: string) => {
    try {
      setUpdating(true)
      console.log('🔄 Creating confirmation for insight:', insightId)

      await confirmInsight(insightId)
      console.log('✅ Confirmation created')

      // Reload insights
      await loadInsights()
      alert('Confirmation item created! This will appear in the Next Steps tab.')
    } catch (error) {
      console.error('❌ Failed to create confirmation:', error)
      alert('Failed to create confirmation')
    } finally {
      setUpdating(false)
    }
  }

  // Handle Dismiss
  const handleDismiss = async (insightId: string) => {
    try {
      setUpdating(true)
      console.log('🔄 Dismissing insight:', insightId)

      await dismissInsight(insightId)
      console.log('✅ Insight dismissed')

      // Reload insights
      await loadInsights()
      alert('Insight dismissed.')
    } catch (error) {
      console.error('❌ Failed to dismiss insight:', error)
      alert('Failed to dismiss insight')
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
          <p className="text-support text-ui-supportText">Loading insights...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="p-6">
        <TwoColumnLayout
          left={
            <InsightsList
              insights={insights}
              selectedId={selectedInsight?.id || null}
              onSelect={handleSelectInsight}
            />
          }
          right={
            <InsightDetail
              insight={selectedInsight}
              onApplyInternally={handleApplyInternally}
              onNeedsConfirmation={handleNeedsConfirmation}
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
