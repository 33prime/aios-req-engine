/**
 * SignalDetailView Component
 *
 * Right column of Sources tab - shows signal details with 4 sub-tabs:
 * 1. Details - Signal metadata + chunks
 * 2. Impact - Entities influenced by this signal
 * 3. Timeline - Project evolution (uses project-wide timeline)
 * 4. Analytics - Chunk usage statistics (uses project-wide analytics)
 */

'use client'

import React, { useState, useEffect } from 'react'
import { getSignalChunks, getSignalImpact, getProjectTimeline, getChunkUsageAnalytics } from '@/lib/api'
import type { SignalWithCounts } from '@/types/api'
import type { SubTabType } from '../SourcesTab'

interface SignalDetailViewProps {
  signal: SignalWithCounts | null
  projectId: string
  subTab: SubTabType
  onSubTabChange: (tab: SubTabType) => void
}

const subTabs = [
  { id: 'details' as SubTabType, label: 'Details' },
  { id: 'impact' as SubTabType, label: 'Impact' },
  { id: 'timeline' as SubTabType, label: 'Timeline' },
  { id: 'analytics' as SubTabType, label: 'Analytics' },
]

export function SignalDetailView({ signal, projectId, subTab, onSubTabChange }: SignalDetailViewProps) {
  const [chunks, setChunks] = useState<any[]>([])
  const [impact, setImpact] = useState<any>(null)
  const [timeline, setTimeline] = useState<any[]>([])
  const [analytics, setAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  // Load data based on active sub-tab
  useEffect(() => {
    if (!signal) return

    if (subTab === 'details') {
      loadChunks()
    } else if (subTab === 'impact') {
      loadImpact()
    } else if (subTab === 'timeline') {
      loadTimeline()
    } else if (subTab === 'analytics') {
      loadAnalytics()
    }
  }, [signal?.id, subTab])

  const loadChunks = async () => {
    if (!signal) return
    try {
      setLoading(true)
      const data = await getSignalChunks(signal.id)
      setChunks(data.chunks)
    } catch (error) {
      console.error('Failed to load chunks:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadImpact = async () => {
    if (!signal) return
    try {
      setLoading(true)
      const data = await getSignalImpact(signal.id)
      setImpact(data)
    } catch (error) {
      console.error('Failed to load impact:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTimeline = async () => {
    try {
      setLoading(true)
      const data = await getProjectTimeline(projectId)
      setTimeline(data.events)
    } catch (error) {
      console.error('Failed to load timeline:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadAnalytics = async () => {
    try {
      setLoading(true)
      const data = await getChunkUsageAnalytics(projectId)
      setAnalytics(data)
    } catch (error) {
      console.error('Failed to load analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  if (!signal) {
    return (
      <div className="bg-white rounded-lg border border-ui-cardBorder p-8 text-center">
        <p className="text-ui-supportText">Select a signal to view details</p>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-ui-cardBorder">
      {/* Sub-tab navigation */}
      <div className="border-b border-ui-cardBorder px-6 pt-4">
        <div className="flex space-x-1">
          {subTabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => onSubTabChange(tab.id)}
              className={`
                px-4 py-2 text-sm font-medium rounded-t-lg transition-colors
                ${
                  subTab === tab.id
                    ? 'bg-white text-brand-primary border-b-2 border-brand-primary'
                    : 'text-ui-supportText hover:text-ui-bodyText'
                }
              `}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Sub-tab content */}
      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary"></div>
          </div>
        ) : (
          <>
            {subTab === 'details' && <DetailsTab signal={signal} chunks={chunks} />}
            {subTab === 'impact' && <ImpactTab signal={signal} impact={impact} />}
            {subTab === 'timeline' && <TimelineTab timeline={timeline} />}
            {subTab === 'analytics' && <AnalyticsTab analytics={analytics} />}
          </>
        )}
      </div>
    </div>
  )
}

// Details sub-tab
function DetailsTab({ signal, chunks }: { signal: SignalWithCounts; chunks: any[] }) {
  return (
    <div className="space-y-6">
      {/* Metadata */}
      <div>
        <h3 className="text-sm font-medium text-ui-bodyText mb-3">Metadata</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-ui-supportText">Type:</span>
            <span className="ml-2 text-ui-bodyText">{signal.signal_type}</span>
          </div>
          <div>
            <span className="text-ui-supportText">Source:</span>
            <span className="ml-2 text-ui-bodyText">{signal.source}</span>
          </div>
          <div>
            <span className="text-ui-supportText">Chunks:</span>
            <span className="ml-2 text-ui-bodyText">{signal.chunk_count}</span>
          </div>
          <div>
            <span className="text-ui-supportText">Impacts:</span>
            <span className="ml-2 text-brand-primary font-medium">{signal.impact_count}</span>
          </div>
          <div className="col-span-2">
            <span className="text-ui-supportText">Created:</span>
            <span className="ml-2 text-ui-bodyText">{new Date(signal.created_at).toLocaleString()}</span>
          </div>
        </div>
      </div>

      {/* Chunks */}
      <div>
        <h3 className="text-sm font-medium text-ui-bodyText mb-3">Chunks ({chunks.length})</h3>
        <div className="space-y-3">
          {chunks.map((chunk, idx) => (
            <div key={idx} className="p-4 bg-ui-background rounded-lg border border-ui-cardBorder">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-ui-bodyText">
                  Chunk {chunk.chunk_index + 1}
                </span>
                <span className="text-xs text-ui-supportText">
                  {chunk.start_char}-{chunk.end_char}
                </span>
              </div>
              <p className="text-sm text-ui-bodyText whitespace-pre-wrap">{chunk.content}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Impact sub-tab
function ImpactTab({ signal, impact }: { signal: SignalWithCounts; impact: any }) {
  if (!impact || impact.total_impacts === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-ui-supportText">This signal has not influenced any entities yet.</p>
        <p className="text-sm text-ui-supportText mt-2">
          Run "Build State" to process signals and create entities.
        </p>
      </div>
    )
  }

  const entityTypeLabels: Record<string, string> = {
    prd_section: 'PRD Sections',
    vp_step: 'VP Steps',
    feature: 'Features',
    insight: 'Insights',
    persona: 'Personas',
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-ui-bodyText mb-1">Total Impacts</h3>
        <p className="text-2xl font-bold text-brand-primary">{impact.total_impacts}</p>
      </div>

      {Object.entries(impact.details || {}).map(([entityType, entities]: [string, any]) => (
        <div key={entityType}>
          <h3 className="text-sm font-medium text-ui-bodyText mb-3">
            {entityTypeLabels[entityType] || entityType} ({entities.length})
          </h3>
          <div className="space-y-2">
            {entities.map((entity: any) => (
              <div
                key={entity.id}
                className="p-3 bg-ui-background rounded-lg border border-ui-cardBorder hover:border-brand-primary/50 transition-colors"
              >
                <p className="text-sm font-medium text-ui-bodyText">{entity.label || entity.slug}</p>
                {entity.slug && entity.slug !== entity.label && (
                  <p className="text-xs text-ui-supportText mt-1">{entity.slug}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// Timeline sub-tab
function TimelineTab({ timeline }: { timeline: any[] }) {
  const eventTypeLabels: Record<string, string> = {
    signal_ingested: 'Signal Ingested',
    prd_section_created: 'PRD Section Created',
    vp_step_created: 'VP Step Created',
    feature_created: 'Feature Created',
    insight_created: 'Insight Created',
    baseline_finalized: 'Baseline Finalized',
  }

  if (timeline.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-ui-supportText">No timeline events yet.</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium text-ui-bodyText">Project Timeline ({timeline.length} events)</h3>
      <div className="space-y-3">
        {timeline.map((event, idx) => (
          <div key={idx} className="flex gap-4">
            <div className="flex-shrink-0 w-2 h-2 mt-2 rounded-full bg-brand-primary"></div>
            <div className="flex-1 pb-4 border-b border-ui-cardBorder last:border-0">
              <p className="text-sm font-medium text-ui-bodyText">{event.description}</p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-ui-supportText">
                  {new Date(event.timestamp).toLocaleString()}
                </span>
                <span className="px-2 py-0.5 text-xs rounded-full bg-ui-buttonGray text-ui-supportText">
                  {eventTypeLabels[event.type] || event.type}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// Analytics sub-tab
function AnalyticsTab({ analytics }: { analytics: any }) {
  if (!analytics) {
    return (
      <div className="text-center py-12">
        <p className="text-ui-supportText">No analytics data available.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-4 bg-ui-background rounded-lg border border-ui-cardBorder">
          <p className="text-xs text-ui-supportText mb-1">Total Citations</p>
          <p className="text-2xl font-bold text-brand-primary">{analytics.total_citations}</p>
        </div>
        <div className="p-4 bg-ui-background rounded-lg border border-ui-cardBorder">
          <p className="text-xs text-ui-supportText mb-1">Unused Signals</p>
          <p className="text-2xl font-bold text-ui-bodyText">{analytics.unused_signals_count}</p>
        </div>
      </div>

      {/* Top chunks */}
      <div>
        <h3 className="text-sm font-medium text-ui-bodyText mb-3">
          Top Cited Chunks ({analytics.top_chunks.length})
        </h3>
        <div className="space-y-2">
          {analytics.top_chunks.map((chunk: any, idx: number) => (
            <div key={idx} className="p-3 bg-ui-background rounded-lg border border-ui-cardBorder">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-ui-bodyText">
                  Chunk {chunk.chunk_index + 1}
                </span>
                <span className="px-2 py-1 text-xs font-semibold rounded-full bg-brand-primary/10 text-brand-primary">
                  {chunk.citation_count} citations
                </span>
              </div>
              <p className="text-sm text-ui-supportText line-clamp-2">{chunk.content_preview}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Citations by entity type */}
      {Object.keys(analytics.citations_by_entity_type || {}).length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-ui-bodyText mb-3">Citations by Entity Type</h3>
          <div className="space-y-2">
            {Object.entries(analytics.citations_by_entity_type).map(([type, count]: [string, any]) => (
              <div key={type} className="flex items-center justify-between p-3 bg-ui-background rounded-lg border border-ui-cardBorder">
                <span className="text-sm text-ui-bodyText capitalize">{type.replace('_', ' ')}</span>
                <span className="text-sm font-semibold text-brand-primary">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
