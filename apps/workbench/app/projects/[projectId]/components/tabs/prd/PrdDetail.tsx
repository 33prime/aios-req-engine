/**
 * PrdDetail Component
 *
 * Right column: Detailed view of selected PRD section
 * - Section content (enhanced and original)
 * - Enrichment insights
 * - Evidence links
 * - Status update actions
 */

'use client'

import React, { useState, useEffect } from 'react'
import { Card, CardHeader, CardSection, EmptyState, Button, ButtonGroup } from '@/components/ui'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { FileText, Users, Target, Zap, Info, AlertCircle, ExternalLink, CheckCircle, AlertTriangle, History, Clock, ShieldAlert } from 'lucide-react'
import type { PrdSection } from '@/types/api'
import { EvidenceGroup } from '@/components/evidence/EvidenceChip'
import { NestedFeatures } from './NestedFeatures'
import { NestedPersonas } from './NestedPersonas'
import { NestedVpSteps } from './NestedVpSteps'

interface PrdDetailProps {
  section: PrdSection | null
  projectId: string
  onStatusUpdate: (sectionId: string, newStatus: string) => Promise<void>
  onViewEvidence: (chunkId: string) => void
  updating?: boolean
}

const SECTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  software_summary: Info,
  personas: Users,
  key_features: Target,
  happy_path: Zap,
  constraints: ShieldAlert,
}

export function PrdDetail({ section, projectId, onStatusUpdate, onViewEvidence, updating = false }: PrdDetailProps) {
  const [showEnrichment, setShowEnrichment] = useState(true)
  const [showEvidence, setShowEvidence] = useState(false)
  const [patchHistory, setPatchHistory] = useState<any[]>([])
  const [loadingPatches, setLoadingPatches] = useState(false)
  const [personas, setPersonas] = useState<any[]>([])
  const [loadingPersonas, setLoadingPersonas] = useState(false)

  // Load personas when viewing personas section
  useEffect(() => {
    if (section?.slug === 'personas' && projectId) {
      loadPersonas()
    }
  }, [section?.slug, projectId])

  const loadPersonas = async () => {
    try {
      setLoadingPersonas(true)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/state/personas?project_id=${projectId}`
      )

      if (response.ok) {
        const data = await response.json()
        setPersonas(data)
      }
    } catch (error) {
      console.error('Failed to load personas:', error)
    } finally {
      setLoadingPersonas(false)
    }
  }

  // Load patch history when section changes
  useEffect(() => {
    if (section?.id) {
      loadPatchHistory()
    } else {
      setPatchHistory([])
    }
  }, [section?.id])

  const loadPatchHistory = async () => {
    if (!section?.id) return

    try {
      setLoadingPatches(true)
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/v1/entities/prd_section/${section.id}/patch-history?limit=5`
      )

      if (response.ok) {
        const patches = await response.json()
        setPatchHistory(patches)
      }
    } catch (error) {
      console.error('Failed to load patch history:', error)
    } finally {
      setLoadingPatches(false)
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

  if (!section) {
    return (
      <EmptyState
        icon={<FileText className="h-16 w-16" />}
        title="No Section Selected"
        description="Select a PRD section from the list to view details."
      />
    )
  }

  const Icon = SECTION_ICONS[section.slug] || FileText
  const hasEnrichment = !!section.enrichment
  const evidenceItems = section.evidence || section.enrichment?.evidence || []

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card>
        <CardHeader
          title={
            <div className="flex items-center gap-3">
              <Icon className="h-6 w-6 text-brand-primary" />
              <span>{section.label}</span>
            </div>
          }
          subtitle={`Section: ${section.slug.replace(/_/g, ' ')}`}
          actions={
            <div className="flex items-center gap-2">
              {section.required && (
                <span className="text-xs font-medium text-red-600 bg-red-50 px-2 py-1 rounded">
                  Required
                </span>
              )}
              {hasEnrichment && (
                <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded">
                  ✨ Enriched
                </span>
              )}
              <StatusBadge status={section.status} />
            </div>
          }
        />

        {/* Status Actions */}
        <div className="mt-4 pt-4 border-t border-ui-cardBorder">
          <h4 className="text-sm font-medium text-ui-bodyText mb-3">Update Status</h4>
          <ButtonGroup>
            <Button
              variant={section.status === 'confirmed_consultant' ? 'primary' : 'secondary'}
              onClick={() => onStatusUpdate(section.id, 'confirmed_consultant')}
              disabled={updating || section.status === 'confirmed_consultant'}
              icon={<CheckCircle className="h-4 w-4" />}
              className="flex-1"
            >
              Confirm
            </Button>
            <Button
              variant={section.status === 'needs_client' ? 'primary' : 'secondary'}
              onClick={() => onStatusUpdate(section.id, 'needs_client')}
              disabled={updating || section.status === 'needs_client'}
              icon={<AlertTriangle className="h-4 w-4" />}
              className="flex-1"
            >
              Needs Client
            </Button>
          </ButtonGroup>
          <p className="text-xs text-ui-supportText mt-2">
            Confirm if the section is accurate. Mark for confirmation if client input is needed.
          </p>
        </div>
      </Card>

      {/* Content Card */}
      <Card>
        <CardHeader title="Section Content" />

        {/* Enhanced Content */}
        {hasEnrichment && section.enrichment.enhanced_fields?.content ? (
          <div className="space-y-4">
            <div className="bg-brand-primary/5 p-4 rounded-lg border border-brand-primary/20">
              <div className="flex items-center justify-between mb-2">
                <h5 className="text-sm font-semibold text-brand-primary">Enhanced Content</h5>
                <span className="text-xs text-brand-accent">✨ AI-Enhanced</span>
              </div>
              <div className="text-body text-ui-bodyText whitespace-pre-wrap">
                {section.enrichment.enhanced_fields.content}
              </div>
            </div>

            {/* Original Content (if different) */}
            {section.fields?.content && section.fields.content !== section.enrichment.enhanced_fields.content && (
              <div className="bg-ui-background p-4 rounded-lg border border-ui-cardBorder">
                <h5 className="text-sm font-medium text-ui-bodyText mb-2">Original Content</h5>
                <div className="text-support text-ui-supportText whitespace-pre-wrap">
                  {section.fields.content}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Fallback to original content */
          <div className="bg-ui-background p-4 rounded-lg border border-ui-cardBorder">
            <div className="text-body text-ui-bodyText whitespace-pre-wrap">
              {section.fields?.content || 'No content available'}
            </div>
          </div>
        )}

        {/* Summary */}
        {hasEnrichment && section.enrichment.summary && (
          <div className="mt-4 pt-4 border-t border-ui-cardBorder">
            <div className="flex items-start gap-2">
              <Info className="h-4 w-4 text-brand-accent flex-shrink-0 mt-0.5" />
              <div>
                <h5 className="text-sm font-medium text-ui-bodyText mb-1">AI Summary</h5>
                <p className="text-support text-ui-supportText">{section.enrichment.summary}</p>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Nested Content Based on Section Type */}
      {section.slug === 'key_features' && (
        <NestedFeatures projectId={projectId} onViewEvidence={onViewEvidence} />
      )}

      {section.slug === 'personas' && (
        <NestedPersonas
          content={section.fields?.content || ''}
          enrichedContent={section.enrichment?.enhanced_fields?.content}
          structuredPersonas={personas}
        />
      )}

      {section.slug === 'happy_path' && (
        <NestedVpSteps projectId={projectId} onViewEvidence={onViewEvidence} />
      )}

      {/* Enrichment Details (if available) */}
      {hasEnrichment && (
        <Card>
          <CardHeader
            title="Enrichment Details"
            actions={
              <button
                onClick={() => setShowEnrichment(!showEnrichment)}
                className="text-sm text-brand-primary hover:text-brand-primary/80"
              >
                {showEnrichment ? 'Hide' : 'Show'}
              </button>
            }
          />

          {showEnrichment && (
            <div className="space-y-4">
              {/* Enhanced Fields */}
              {section.enrichment.enhanced_fields && Object.keys(section.enrichment.enhanced_fields).length > 0 && (
                <div>
                  <h5 className="text-sm font-medium text-ui-bodyText mb-2">Enhanced Fields</h5>
                  <div className="space-y-2">
                    {Object.entries(section.enrichment.enhanced_fields)
                      .filter(([key]) => key !== 'content') // Skip content as it's shown above
                      .map(([field, value]) => (
                        <div key={field} className="bg-ui-background p-3 rounded border border-ui-cardBorder">
                          <div className="text-sm font-medium text-ui-bodyText capitalize mb-1">
                            {field.replace(/_/g, ' ')}
                          </div>
                          <div className="text-support text-ui-supportText whitespace-pre-wrap">
                            {String(value)}
                          </div>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* Proposed Client Needs */}
              {section.enrichment.proposed_client_needs && section.enrichment.proposed_client_needs.length > 0 && (
                <div className="pt-4 border-t border-ui-cardBorder">
                  <h5 className="text-sm font-medium text-ui-bodyText mb-3">
                    Proposed Client Needs ({section.enrichment.proposed_client_needs.length})
                  </h5>
                  <div className="space-y-3">
                    {section.enrichment.proposed_client_needs.map((need: any, idx: number) => (
                      <div key={idx} className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
                        <div className="font-medium text-ui-bodyText text-sm mb-1">
                          {need.title || need.ask}
                        </div>
                        <div className="text-support text-ui-supportText text-sm mb-2">
                          {need.ask || need.why}
                        </div>
                        {need.why && need.ask && (
                          <div className="text-xs text-ui-supportText italic mb-2">
                            "{need.why}"
                          </div>
                        )}
                        <div className="flex items-center gap-2">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                            need.priority === 'high' ? 'bg-red-100 text-red-800' :
                            need.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }`}>
                            {need.priority} priority
                          </span>
                          {need.suggested_method && (
                            <span className="text-xs text-ui-supportText">
                              {need.suggested_method}
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      )}

      {/* Evidence Card */}
      {evidenceItems.length > 0 && (
        <Card>
          <CardHeader
            title={`Evidence (${evidenceItems.length})`}
            actions={
              <button
                onClick={() => setShowEvidence(!showEvidence)}
                className="text-sm text-brand-primary hover:text-brand-primary/80"
              >
                {showEvidence ? 'Hide' : 'Show'}
              </button>
            }
          />

          {showEvidence && (
            <div className="space-y-3">
              {evidenceItems.map((evidence: any, idx: number) => (
                <div key={idx} className="bg-ui-background border border-ui-cardBorder rounded-lg p-3">
                  <div className="flex items-start gap-2 mb-2">
                    <AlertCircle className="h-4 w-4 text-brand-accent flex-shrink-0 mt-0.5" />
                    <p className="text-support text-ui-bodyText flex-1 italic">
                      "{evidence.excerpt}"
                    </p>
                  </div>
                  <div className="flex items-center justify-between pl-6">
                    <span className="text-xs text-ui-supportText">{evidence.rationale}</span>
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
          )}
        </Card>
      )}

      {/* Recent Changes (Patch History) */}
      <Card>
        <CardHeader
          title={
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-brand-accent" />
              <span>Recent Changes</span>
            </div>
          }
          subtitle="Surgical updates applied to this section"
        />

        {loadingPatches ? (
          <div className="text-center py-8">
            <p className="text-sm text-ui-supportText">Loading patch history...</p>
          </div>
        ) : patchHistory.length === 0 ? (
          <div className="text-center py-8 bg-ui-background rounded-lg border border-ui-cardBorder">
            <Clock className="h-12 w-12 text-ui-supportText mx-auto mb-3" />
            <p className="text-sm font-medium text-ui-bodyText mb-1">No recent changes</p>
            <p className="text-xs text-ui-supportText">
              Surgical updates will appear here in maintenance mode
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {patchHistory.map((patch) => {
              const patchData = patch.patch_data || {}
              const proposedChanges = patchData.proposed_changes || {}
              const changedFields = Object.keys(proposedChanges)

              return (
                <div key={patch.id} className="bg-ui-background border border-ui-cardBorder rounded-lg p-3">
                  <div className="flex items-start gap-2 mb-2">
                    <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-ui-bodyText">
                          {patch.title || 'Updated section'}
                        </span>
                        <span className="text-xs text-ui-supportText">
                          {patch.applied_at ? getTimeAgo(patch.applied_at) : 'Recently'}
                        </span>
                      </div>
                      <p className="text-xs text-ui-supportText mb-2">
                        {patchData.rationale || patch.finding}
                      </p>
                      {changedFields.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-2">
                          {changedFields.map((field) => (
                            <span
                              key={field}
                              className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded"
                            >
                              {field.replace(/_/g, ' ')}
                            </span>
                          ))}
                        </div>
                      )}
                      {patch.auto_apply_ok && (
                        <span className="text-xs text-green-600">Auto-applied • Safe</span>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {/* Metadata */}
      <Card>
        <CardHeader title="Metadata" />
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-support text-ui-supportText">Created</div>
            <div className="text-body text-ui-bodyText font-medium">
              {new Date(section.created_at).toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Last Updated</div>
            <div className="text-body text-ui-bodyText font-medium">
              {new Date(section.updated_at).toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Section ID</div>
            <div className="text-xs font-mono text-ui-supportText">{section.id}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Slug</div>
            <div className="text-xs font-mono text-ui-supportText">{section.slug}</div>
          </div>
        </div>
      </Card>
    </div>
  )
}
