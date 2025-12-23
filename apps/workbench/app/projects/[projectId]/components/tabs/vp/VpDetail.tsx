/**
 * VpDetail Component
 *
 * Right column: Detailed view of selected VP step
 * - Step description and core fields
 * - Enrichment details (data schema, business logic, transition logic)
 * - Evidence links
 * - Status update actions
 */

'use client'

import React, { useState } from 'react'
import { Card, CardHeader, CardSection, EmptyState, Button, ButtonGroup } from '@/components/ui'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Zap, Info, AlertCircle, ExternalLink, CheckCircle, AlertTriangle, Database, GitBranch, Code } from 'lucide-react'
import type { VpStep } from '@/types/api'

interface VpDetailProps {
  step: VpStep | null
  onStatusUpdate: (stepId: string, newStatus: string) => Promise<void>
  onViewEvidence: (chunkId: string) => void
  updating?: boolean
}

export function VpDetail({ step, onStatusUpdate, onViewEvidence, updating = false }: VpDetailProps) {
  const [showEnrichment, setShowEnrichment] = useState(true)
  const [showEvidence, setShowEvidence] = useState(false)

  if (!step) {
    return (
      <EmptyState
        icon={<Zap className="h-16 w-16" />}
        title="No Step Selected"
        description="Select a Value Path step from the list to view details."
      />
    )
  }

  const hasEnrichment = !!step.enrichment
  const evidenceItems = step.enrichment?.evidence || []

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card>
        <CardHeader
          title={
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 bg-brand-primary/10 rounded-full text-brand-primary font-semibold">
                {step.step_index}
              </div>
              <span>{step.label}</span>
            </div>
          }
          subtitle={`Step ${step.step_index} of ${step.step_index}`}
          actions={
            <div className="flex items-center gap-2">
              {hasEnrichment && (
                <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded">
                  ✨ Enriched
                </span>
              )}
              <StatusBadge status={step.status} />
            </div>
          }
        />

        {/* Description */}
        {step.description && (
          <div className="mt-4 pt-4 border-t border-ui-cardBorder">
            <h4 className="text-sm font-medium text-ui-bodyText mb-2">Description</h4>
            <p className="text-body text-ui-bodyText">{step.description}</p>
          </div>
        )}

        {/* Status Actions */}
        <div className="mt-4 pt-4 border-t border-ui-cardBorder">
          <h4 className="text-sm font-medium text-ui-bodyText mb-3">Update Status</h4>
          <ButtonGroup>
            <Button
              variant={step.status === 'confirmed_consultant' ? 'primary' : 'secondary'}
              onClick={() => onStatusUpdate(step.id, 'confirmed_consultant')}
              disabled={updating || step.status === 'confirmed_consultant'}
              icon={<CheckCircle className="h-4 w-4" />}
              className="flex-1"
            >
              Confirm
            </Button>
            <Button
              variant={step.status === 'needs_confirmation' ? 'primary' : 'secondary'}
              onClick={() => onStatusUpdate(step.id, 'needs_confirmation')}
              disabled={updating || step.status === 'needs_confirmation'}
              icon={<AlertTriangle className="h-4 w-4" />}
              className="flex-1"
            >
              Needs Confirmation
            </Button>
          </ButtonGroup>
          <p className="text-xs text-ui-supportText mt-2">
            Confirm if the step is accurate. Mark for confirmation if client input is needed.
          </p>
        </div>
      </Card>

      {/* Core Fields (if available) */}
      {(step.user_benefit_pain || step.ui_overview || step.value_created || step.kpi_impact) && (
        <Card>
          <CardHeader title="Core Fields" />
          <div className="space-y-4">
            {step.user_benefit_pain && (
              <div>
                <h5 className="text-sm font-medium text-ui-bodyText mb-1">User Benefit/Pain</h5>
                <p className="text-support text-ui-supportText">{step.user_benefit_pain}</p>
              </div>
            )}
            {step.ui_overview && (
              <div>
                <h5 className="text-sm font-medium text-ui-bodyText mb-1">UI Overview</h5>
                <p className="text-support text-ui-supportText">{step.ui_overview}</p>
              </div>
            )}
            {step.value_created && (
              <div>
                <h5 className="text-sm font-medium text-ui-bodyText mb-1">Value Created</h5>
                <p className="text-support text-ui-supportText">{step.value_created}</p>
              </div>
            )}
            {step.kpi_impact && (
              <div>
                <h5 className="text-sm font-medium text-ui-bodyText mb-1">KPI Impact</h5>
                <p className="text-support text-ui-supportText">{step.kpi_impact}</p>
              </div>
            )}
          </div>
        </Card>
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
              {/* Summary */}
              {step.enrichment.summary && (
                <div className="bg-brand-primary/5 p-4 rounded-lg border border-brand-primary/20">
                  <div className="flex items-start gap-2">
                    <Info className="h-4 w-4 text-brand-accent flex-shrink-0 mt-0.5" />
                    <div>
                      <h5 className="text-sm font-medium text-ui-bodyText mb-1">AI Summary</h5>
                      <p className="text-support text-ui-supportText">{step.enrichment.summary}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Data Schema */}
              {step.enrichment.enhanced_fields?.data_schema && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <div className="flex items-start gap-2 mb-2">
                    <Database className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
                    <h5 className="text-sm font-semibold text-blue-900">Data Schema</h5>
                  </div>
                  <div className="text-support text-blue-800 whitespace-pre-wrap">
                    {step.enrichment.enhanced_fields.data_schema}
                  </div>
                </div>
              )}

              {/* Business Logic */}
              {step.enrichment.enhanced_fields?.business_logic && (
                <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                  <div className="flex items-start gap-2 mb-2">
                    <Code className="h-4 w-4 text-green-600 flex-shrink-0 mt-0.5" />
                    <h5 className="text-sm font-semibold text-green-900">Business Logic</h5>
                  </div>
                  <div className="text-support text-green-800 whitespace-pre-wrap">
                    {step.enrichment.enhanced_fields.business_logic}
                  </div>
                </div>
              )}

              {/* Transition Logic */}
              {step.enrichment.enhanced_fields?.transition_logic && (
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                  <div className="flex items-start gap-2 mb-2">
                    <GitBranch className="h-4 w-4 text-purple-600 flex-shrink-0 mt-0.5" />
                    <h5 className="text-sm font-semibold text-purple-900">Transition Logic</h5>
                  </div>
                  <div className="text-support text-purple-800 whitespace-pre-wrap">
                    {step.enrichment.enhanced_fields.transition_logic}
                  </div>
                </div>
              )}

              {/* Other Enhanced Fields */}
              {step.enrichment.enhanced_fields && Object.keys(step.enrichment.enhanced_fields).length > 0 && (
                <div className="pt-4 border-t border-ui-cardBorder">
                  <h5 className="text-sm font-medium text-ui-bodyText mb-3">Additional Fields</h5>
                  <div className="space-y-2">
                    {Object.entries(step.enrichment.enhanced_fields)
                      .filter(([key]) => !['data_schema', 'business_logic', 'transition_logic'].includes(key))
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

              {/* Proposed Needs */}
              {step.enrichment.proposed_needs && step.enrichment.proposed_needs.length > 0 && (
                <div className="pt-4 border-t border-ui-cardBorder">
                  <h5 className="text-sm font-medium text-ui-bodyText mb-3">
                    Proposed Client Needs ({step.enrichment.proposed_needs.length})
                  </h5>
                  <div className="space-y-3">
                    {step.enrichment.proposed_needs.map((need: any, idx: number) => (
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

      {/* Metadata */}
      <Card>
        <CardHeader title="Metadata" />
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-support text-ui-supportText">Step Index</div>
            <div className="text-body text-ui-bodyText font-medium">{step.step_index}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Status</div>
            <div className="text-body text-ui-bodyText font-medium">{step.status}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Created</div>
            <div className="text-body text-ui-bodyText font-medium">
              {new Date(step.created_at).toLocaleString()}
            </div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Last Updated</div>
            <div className="text-body text-ui-bodyText font-medium">
              {new Date(step.updated_at).toLocaleString()}
            </div>
          </div>
          <div className="col-span-2">
            <div className="text-support text-ui-supportText">Step ID</div>
            <div className="text-xs font-mono text-ui-supportText">{step.id}</div>
          </div>
        </div>
      </Card>
    </div>
  )
}
