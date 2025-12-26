/**
 * SourcesTab Component
 *
 * Tab 5: Sources History
 *
 * Purpose: Track signal provenance and impact
 * - Signal list with metadata
 * - Impact tracking (which entities each signal influenced)
 * - Timeline visualization
 * - Chunk usage analytics
 */

'use client'

import React, { useState, useEffect } from 'react'
import { TwoColumnLayout } from '@/components/ui'
import { SignalList } from './sources/SignalList'
import { SignalDetailView } from './sources/SignalDetailView'
import { listProjectSignals } from '@/lib/api'
import type { SignalWithCounts } from '@/types/api'

interface SourcesTabProps {
  projectId: string
}

export type SubTabType = 'details' | 'impact' | 'timeline' | 'analytics'

export function SourcesTab({ projectId }: SourcesTabProps) {
  const [signals, setSignals] = useState<SignalWithCounts[]>([])
  const [selectedSignal, setSelectedSignal] = useState<SignalWithCounts | null>(null)
  const [subTab, setSubTab] = useState<SubTabType>('details')
  const [loading, setLoading] = useState(true)

  // Load signals on mount
  useEffect(() => {
    loadSignals()
  }, [projectId])

  const loadSignals = async () => {
    try {
      setLoading(true)
      console.log('🔄 Loading signals...')
      const data = await listProjectSignals(projectId)
      console.log('✅ Loaded signals:', data)
      setSignals(data.signals as SignalWithCounts[])

      // Auto-select first signal if none selected
      if (!selectedSignal && data.signals.length > 0) {
        setSelectedSignal(data.signals[0] as SignalWithCounts)
      }
    } catch (error) {
      console.error('❌ Failed to load signals:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle signal selection
  const handleSelectSignal = (signal: SignalWithCounts) => {
    setSelectedSignal(signal)
    // Reset to details tab when selecting new signal
    setSubTab('details')
  }

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
          <p className="text-support text-ui-supportText">Loading sources...</p>
        </div>
      </div>
    )
  }

  if (signals.length === 0) {
    return (
      <div className="p-6 flex items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-ui-bodyText mb-2">No signals yet</p>
          <p className="text-sm text-ui-supportText">
            Signals will appear here as you add them to your project. Use the "Add Signal" button in the header to get started.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <TwoColumnLayout
        left={
          <SignalList
            signals={signals}
            selectedId={selectedSignal?.id || null}
            onSelect={handleSelectSignal}
          />
        }
        right={
          <SignalDetailView
            signal={selectedSignal}
            projectId={projectId}
            subTab={subTab}
            onSubTabChange={setSubTab}
          />
        }
        leftWidth="medium"
        stickyLeft={true}
      />
    </div>
  )
}
