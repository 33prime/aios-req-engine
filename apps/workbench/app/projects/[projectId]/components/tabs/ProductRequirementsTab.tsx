/**
 * ProductRequirementsTab Component
 *
 * Tab 1: Product Requirements (PRD Sections)
 *
 * Purpose: Lock the foundation quickly
 * - PRD sections with enrichment details
 * - Status tracking and confirmation workflow
 * - Evidence-based insights
 */

'use client'

import React, { useState, useEffect } from 'react'
import { TwoColumnLayout } from '@/components/ui'
import { PrdList, PrdDetail } from './prd'
import { getPrdSections, updatePrdSectionStatus, getSignal, getSignalChunks } from '@/lib/api'
import type { PrdSection, Signal, SignalChunk } from '@/types/api'

interface ProductRequirementsTabProps {
  projectId: string
}

export function ProductRequirementsTab({ projectId }: ProductRequirementsTabProps) {
  const [sections, setSections] = useState<PrdSection[]>([])
  const [selectedSection, setSelectedSection] = useState<PrdSection | null>(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)

  // Evidence modal state
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [signalChunks, setSignalChunks] = useState<SignalChunk[]>([])

  // Load PRD sections on mount
  useEffect(() => {
    loadSections()
  }, [projectId])

  const loadSections = async () => {
    try {
      setLoading(true)
      console.log('🔄 Loading PRD sections...')
      const data = await getPrdSections(projectId)
      console.log('✅ Loaded PRD sections:', data.length)
      setSections(data)

      // Auto-select first section if none selected
      if (!selectedSection && data.length > 0) {
        setSelectedSection(data[0])
      }
    } catch (error) {
      console.error('❌ Failed to load PRD sections:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle section selection
  const handleSelectSection = (section: PrdSection) => {
    setSelectedSection(section)
  }

  // Handle status update
  const handleStatusUpdate = async (sectionId: string, newStatus: string) => {
    try {
      setUpdating(true)
      console.log('🔄 Updating section status:', { sectionId, newStatus })

      const updated = await updatePrdSectionStatus(sectionId, newStatus)
      console.log('✅ Section status updated:', updated)

      // Update local state
      setSections(prev => prev.map(s => s.id === sectionId ? { ...s, status: newStatus } : s))
      if (selectedSection?.id === sectionId) {
        setSelectedSection({ ...selectedSection, status: newStatus })
      }
    } catch (error) {
      console.error('❌ Failed to update section status:', error)
      alert('Failed to update section status')
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
          <p className="text-support text-ui-supportText">Loading PRD sections...</p>
        </div>
      </div>
    )
  }

  return (
    <>
      <div className="p-6">
        <TwoColumnLayout
          left={
            <PrdList
              sections={sections}
              selectedId={selectedSection?.id || null}
              onSelect={handleSelectSection}
            />
          }
          right={
            <PrdDetail
              section={selectedSection}
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
