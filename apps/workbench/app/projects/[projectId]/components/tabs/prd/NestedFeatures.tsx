/**
 * NestedFeatures Component
 *
 * Displays list of features within Key Features section detail view.
 */

'use client'

import React, { useState, useEffect } from 'react'
import { Target, ChevronDown, ChevronUp, ExternalLink, History, CheckCircle, Clock } from 'lucide-react'
import { getFeatures } from '@/lib/api'
import type { Feature } from '@/types/api'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Card } from '@/components/ui'

interface NestedFeaturesProps {
  projectId: string
  onViewEvidence: (chunkId: string) => void
}

export function NestedFeatures({ projectId, onViewEvidence }: NestedFeaturesProps) {
  const [features, setFeatures] = useState<Feature[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [patchHistory, setPatchHistory] = useState<Record<string, any[]>>({})
  const [loadingPatches, setLoadingPatches] = useState<Record<string, boolean>>({})

  // Check if entity was recently updated (last 24 hours)
  const isRecentlyUpdated = (updatedAt: string) => {
    const diffMs = new Date().getTime() - new Date(updatedAt).getTime()
    return diffMs < 24 * 60 * 60 * 1000
  }

  useEffect(() => {
    loadFeatures()
  }, [projectId])

  const loadFeatures = async () => {
    try {
      setLoading(true)
      const data = await getFeatures(projectId)
      setFeatures(data)
    } catch (error) {
      console.error('Failed to load features:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadPatchHistory = async (featureId: string) => {
    if (patchHistory[featureId]) return // Already loaded

    try {
      setLoadingPatches({ ...loadingPatches, [featureId]: true })
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/entities/feature/${featureId}/patch-history?limit=5`
      )

      if (response.ok) {
        const patches = await response.json()
        setPatchHistory({ ...patchHistory, [featureId]: patches })
      }
    } catch (error) {
      console.error('Failed to load patch history:', error)
    } finally {
      setLoadingPatches({ ...loadingPatches, [featureId]: false })
    }
  }

  const toggleExpand = (featureId: string) => {
    const newExpandedId = expandedId === featureId ? null : featureId
    setExpandedId(newExpandedId)

    // Load patch history when expanding
    if (newExpandedId === featureId) {
      loadPatchHistory(featureId)
    }
  }

  const getTimeAgo = (timestamp: string) => {
    const now = new Date()
    const past = new Date(timestamp)
    const diffMs = now.getTime() - past.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  if (loading) {
    return (
      <Card>
        <div className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <Target className="h-5 w-5 text-brand-primary" />
            <h4 className="font-semibold text-ui-bodyText">Features</h4>
          </div>
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary mx-auto"></div>
          </div>
        </div>
      </Card>
    )
  }

  if (features.length === 0) {
    return (
      <Card>
        <div className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <Target className="h-5 w-5 text-brand-primary" />
            <h4 className="font-semibold text-ui-bodyText">Features</h4>
          </div>
          <div className="text-center py-8 bg-ui-background rounded-lg border border-ui-cardBorder">
            <Target className="h-12 w-12 text-ui-supportText mx-auto mb-3" />
            <p className="text-sm font-medium text-ui-bodyText mb-1">No features yet</p>
            <p className="text-xs text-ui-supportText">
              Run build state to extract features from signals
            </p>
          </div>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <div className="p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Target className="h-5 w-5 text-brand-primary" />
            <h4 className="font-semibold text-ui-bodyText">Features</h4>
            <span className="text-xs text-ui-supportText">({features.length})</span>
          </div>
        </div>

        <div className="space-y-3">
          {features.map((feature) => {
            const isExpanded = expandedId === feature.id
            const hasEnrichment = !!feature.details
            const recentlyUpdated = isRecentlyUpdated(feature.updated_at)

            return (
              <div
                key={feature.id}
                className="bg-ui-background border border-ui-cardBorder rounded-lg p-4"
              >
                {/* Feature Header */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h5 className="font-semibold text-ui-bodyText">{feature.name}</h5>
                      {feature.is_mvp && (
                        <span className="text-xs font-medium px-2 py-0.5 rounded bg-purple-100 text-purple-800">
                          MVP
                        </span>
                      )}
                      {hasEnrichment && (
                        <span className="text-xs">✨</span>
                      )}
                      {recentlyUpdated && (
                        <span className="relative inline-flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-xs text-ui-supportText">
                      <span className="font-medium">{feature.category}</span>
                      <span>•</span>
                      <span className="capitalize">{feature.confidence} confidence</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={feature.status} />
                    {(hasEnrichment || feature.evidence.length > 0) && (
                      <button
                        onClick={() => toggleExpand(feature.id)}
                        className="text-sm text-brand-primary hover:text-brand-primary/80 flex items-center gap-1"
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp className="h-4 w-4" />
                            <span>Less</span>
                          </>
                        ) : (
                          <>
                            <ChevronDown className="h-4 w-4" />
                            <span>Details</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-ui-cardBorder space-y-3">
                    {/* Enrichment Summary */}
                    {hasEnrichment && feature.details.summary && (
                      <div>
                        <h6 className="text-sm font-medium text-ui-bodyText mb-1">Summary</h6>
                        <p className="text-sm text-ui-supportText">{feature.details.summary}</p>
                      </div>
                    )}

                    {/* Acceptance Criteria */}
                    {hasEnrichment && feature.details.acceptance_criteria && feature.details.acceptance_criteria.length > 0 && (
                      <div>
                        <h6 className="text-sm font-medium text-ui-bodyText mb-2">
                          Acceptance Criteria
                        </h6>
                        <ul className="space-y-1">
                          {feature.details.acceptance_criteria.map((criterion: any, idx: number) => (
                            <li key={idx} className="text-sm text-ui-supportText flex items-start gap-2">
                              <span className="text-brand-primary mt-1">•</span>
                              <span>{criterion.criterion || criterion}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Evidence */}
                    {feature.evidence.length > 0 && (
                      <div>
                        <h6 className="text-sm font-medium text-ui-bodyText mb-2">
                          Evidence ({feature.evidence.length})
                        </h6>
                        <div className="space-y-2">
                          {feature.evidence.map((evidence: any, idx: number) => (
                            <div
                              key={idx}
                              className="bg-white border border-ui-cardBorder rounded p-2"
                            >
                              <p className="text-xs text-ui-bodyText italic mb-1">
                                "{evidence.excerpt}"
                              </p>
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-ui-supportText">
                                  {evidence.rationale}
                                </span>
                                <button
                                  onClick={() => onViewEvidence(evidence.chunk_id)}
                                  className="text-xs text-brand-primary hover:text-brand-primary/80 flex items-center gap-1"
                                >
                                  View source <ExternalLink className="h-3 w-3" />
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Patch History */}
                    <div className="pt-3 border-t border-ui-cardBorder">
                      <div className="flex items-center gap-2 mb-2">
                        <History className="h-4 w-4 text-brand-accent" />
                        <h6 className="text-sm font-medium text-ui-bodyText">Recent Changes</h6>
                      </div>

                      {loadingPatches[feature.id] ? (
                        <div className="text-center py-4">
                          <p className="text-xs text-ui-supportText">Loading...</p>
                        </div>
                      ) : !patchHistory[feature.id] || patchHistory[feature.id].length === 0 ? (
                        <div className="text-center py-4 bg-white rounded border border-ui-cardBorder">
                          <Clock className="h-8 w-8 text-ui-supportText mx-auto mb-2" />
                          <p className="text-xs text-ui-supportText">No recent changes</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {patchHistory[feature.id].map((patch) => {
                            const patchData = patch.patch_data || {}
                            const proposedChanges = patchData.proposed_changes || {}
                            const changedFields = Object.keys(proposedChanges)

                            return (
                              <div
                                key={patch.id}
                                className="bg-white border border-ui-cardBorder rounded p-2"
                              >
                                <div className="flex items-start gap-2">
                                  <CheckCircle className="h-3 w-3 text-green-600 flex-shrink-0 mt-0.5" />
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center justify-between mb-1">
                                      <span className="text-xs font-medium text-ui-bodyText truncate">
                                        {patch.title || 'Updated feature'}
                                      </span>
                                      <span className="text-xs text-ui-supportText whitespace-nowrap ml-2">
                                        {patch.applied_at ? getTimeAgo(patch.applied_at) : 'Recently'}
                                      </span>
                                    </div>
                                    <p className="text-xs text-ui-supportText mb-1">
                                      {patchData.rationale || patch.finding}
                                    </p>
                                    {changedFields.length > 0 && (
                                      <div className="flex flex-wrap gap-1">
                                        {changedFields.map((field) => (
                                          <span
                                            key={field}
                                            className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded"
                                          >
                                            {field.replace(/_/g, ' ')}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </div>
    </Card>
  )
}
