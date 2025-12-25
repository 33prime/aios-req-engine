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

import React, { useState } from 'react'
import { Card, CardHeader, CardSection, EmptyState, Button, ButtonGroup } from '@/components/ui'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { FileText, Users, Target, Zap, Info, AlertCircle, ExternalLink, CheckCircle, AlertTriangle, History, Clock } from 'lucide-react'
import type { PrdSection } from '@/types/api'
import { EvidenceGroup } from '@/components/evidence/EvidenceChip'

interface PrdDetailProps {
  section: PrdSection | null
  onStatusUpdate: (sectionId: string, newStatus: string) => Promise<void>
  onViewEvidence: (chunkId: string) => void
  updating?: boolean
}

const SECTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  personas: Users,
  key_features: Target,
  happy_path: Zap,
}

export function PrdDetail({ section, onStatusUpdate, onViewEvidence, updating = false }: PrdDetailProps) {
  const [showEnrichment, setShowEnrichment] = useState(true)
  const [showEvidence, setShowEvidence] = useState(false)

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
              variant={section.status === 'needs_confirmation' ? 'primary' : 'secondary'}
              onClick={() => onStatusUpdate(section.id, 'needs_confirmation')}
              disabled={updating || section.status === 'needs_confirmation'}
              icon={<AlertTriangle className="h-4 w-4" />}
              className="flex-1"
            >
              Needs Confirmation
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

        {/* TODO: Load patch history from API */}
        {/* For now, show empty state */}
        <div className="text-center py-8 bg-ui-background rounded-lg border border-ui-cardBorder">
          <Clock className="h-12 w-12 text-ui-supportText mx-auto mb-3" />
          <p className="text-sm font-medium text-ui-bodyText mb-1">No recent changes</p>
          <p className="text-xs text-ui-supportText">
            Surgical updates will appear here in maintenance mode
          </p>
        </div>

        {/* Example of what patch history will look like when implemented:
        <div className="space-y-3">
          <div className="bg-ui-background border border-ui-cardBorder rounded-lg p-3">
            <div className="flex items-start gap-2 mb-2">
              <CheckCircle className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium text-ui-bodyText">
                    Added constraint about data privacy
                  </span>
                  <span className="text-xs text-ui-supportText">2h ago</span>
                </div>
                <p className="text-xs text-ui-supportText mb-2">
                  Auto-applied • Minor severity
                </p>
                <EvidenceGroup
                  evidence={[...]}
                  maxDisplay={2}
                />
              </div>
            </div>
          </div>
        </div>
        */}
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
