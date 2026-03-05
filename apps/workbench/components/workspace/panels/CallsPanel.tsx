/**
 * CallsPanel - Call Intelligence panel for the Bottom Dock
 *
 * Four tabs:
 * 1. Recordings — list + seed recording + status badges + strategy brief indicators
 * 2. Strategy — pre-call strategy brief view with goals, stakeholder intel, readiness
 * 3. Insights — post-call detail view with synced transcript, engagement heatmap, aha moments
 * 4. Performance — consultant coaching dashboard
 */

'use client'

import { useState } from 'react'
import { Phone, FileText, BarChart3, Award } from 'lucide-react'
import { getCallDetails } from '@/lib/api'
import type { CallDetails } from '@/types/call-intelligence'
import {
  RecordingsTab,
  StrategyView,
  InsightsView,
  PerformanceView,
} from '@/components/call-intelligence'

type Tab = 'recordings' | 'strategy' | 'insights' | 'performance'

export function CallsPanel({ projectId }: { projectId: string }) {
  const [activeTab, setActiveTab] = useState<Tab>('recordings')
  const [selectedRecordingId, setSelectedRecordingId] = useState<string | null>(null)
  const [loadedDetails, setLoadedDetails] = useState<CallDetails | null>(null)

  const handleSelectRecording = (recordingId: string) => {
    setSelectedRecordingId(recordingId)
    setActiveTab('insights')
    // Pre-fetch details for performance tab
    getCallDetails(recordingId)
      .then(d => setLoadedDetails(d))
      .catch(() => setLoadedDetails(null))
  }

  const handleBack = () => {
    setSelectedRecordingId(null)
    setLoadedDetails(null)
    setActiveTab('recordings')
  }

  const tabs: { key: Tab; label: string; icon: typeof Phone; disabled: boolean }[] = [
    { key: 'recordings', label: 'Recordings', icon: Phone, disabled: false },
    { key: 'strategy', label: 'Strategy', icon: FileText, disabled: false },
    { key: 'insights', label: 'Insights', icon: BarChart3, disabled: !selectedRecordingId },
    { key: 'performance', label: 'Performance', icon: Award, disabled: !selectedRecordingId },
  ]

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-6 py-2 border-b border-border bg-white shrink-0">
        {tabs.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.key}
              onClick={() => !tab.disabled && setActiveTab(tab.key)}
              disabled={tab.disabled}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                activeTab === tab.key
                  ? 'bg-brand-primary-light text-brand-primary'
                  : 'text-text-muted hover:text-text-body hover:bg-surface-muted'
              } disabled:opacity-40 disabled:cursor-not-allowed`}
            >
              <Icon className="w-3.5 h-3.5" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'recordings' && (
          <RecordingsTab projectId={projectId} onSelectRecording={handleSelectRecording} />
        )}
        {activeTab === 'strategy' && (
          <StrategyView
            recordingId={selectedRecordingId}
            brief={loadedDetails?.strategy_brief}
            projectId={projectId}
            onBack={handleBack}
          />
        )}
        {activeTab === 'insights' && selectedRecordingId && (
          <InsightsView recordingId={selectedRecordingId} onBack={handleBack} />
        )}
        {activeTab === 'performance' && (
          <PerformanceView details={loadedDetails} onBack={handleBack} />
        )}
      </div>
    </div>
  )
}
