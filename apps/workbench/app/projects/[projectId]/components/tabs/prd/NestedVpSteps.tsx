/**
 * NestedVpSteps Component
 *
 * Displays VP steps within Happy Path section detail view.
 */

'use client'

import React, { useState, useEffect } from 'react'
import { Zap, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { getVpSteps } from '@/lib/api'
import type { VpStep } from '@/types/api'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { Card } from '@/components/ui'

interface NestedVpStepsProps {
  projectId: string
  onViewEvidence: (chunkId: string) => void
}

export function NestedVpSteps({ projectId, onViewEvidence }: NestedVpStepsProps) {
  const [steps, setSteps] = useState<VpStep[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    loadSteps()
  }, [projectId])

  const loadSteps = async () => {
    try {
      setLoading(true)
      const data = await getVpSteps(projectId)
      setSteps(data)
    } catch (error) {
      console.error('Failed to load VP steps:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleExpand = (stepId: string) => {
    setExpandedId(expandedId === stepId ? null : stepId)
  }

  if (loading) {
    return (
      <Card>
        <div className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-5 w-5 text-brand-primary" />
            <h4 className="font-semibold text-ui-bodyText">Value Path Steps</h4>
          </div>
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-primary mx-auto"></div>
          </div>
        </div>
      </Card>
    )
  }

  if (steps.length === 0) {
    return (
      <Card>
        <div className="p-4">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="h-5 w-5 text-brand-primary" />
            <h4 className="font-semibold text-ui-bodyText">Value Path Steps</h4>
          </div>
          <div className="text-center py-8 bg-ui-background rounded-lg border border-ui-cardBorder">
            <Zap className="h-12 w-12 text-ui-supportText mx-auto mb-3" />
            <p className="text-sm font-medium text-ui-bodyText mb-1">No VP steps yet</p>
            <p className="text-xs text-ui-supportText">
              Run build state to extract value path from signals
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
            <Zap className="h-5 w-5 text-brand-primary" />
            <h4 className="font-semibold text-ui-bodyText">Value Path Steps</h4>
            <span className="text-xs text-ui-supportText">({steps.length})</span>
          </div>
        </div>

        <div className="space-y-3">
          {steps.map((step) => {
            const isExpanded = expandedId === step.id
            const hasEnrichment = !!step.enrichment
            const hasEvidence = step.evidence && step.evidence.length > 0

            return (
              <div
                key={step.id}
                className="bg-ui-background border border-ui-cardBorder rounded-lg p-4"
              >
                {/* Step Header */}
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-brand-primary text-white flex items-center justify-center text-sm font-semibold">
                    {step.step_index}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <h5 className="font-semibold text-ui-bodyText">{step.label}</h5>
                        {hasEnrichment && <span className="text-xs">✨</span>}
                      </div>
                      <div className="flex items-center gap-2">
                        <StatusBadge status={step.status} />
                        {(hasEnrichment || hasEvidence) && (
                          <button
                            onClick={() => toggleExpand(step.id)}
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
                    <p className="text-sm text-ui-supportText">{step.description}</p>
                  </div>
                </div>

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="ml-11 mt-4 pt-4 border-t border-ui-cardBorder space-y-3">
                    {/* Core Fields */}
                    {step.user_benefit_pain && (
                      <div>
                        <h6 className="text-sm font-medium text-ui-bodyText mb-1">
                          User Benefit / Pain
                        </h6>
                        <p className="text-sm text-ui-supportText">{step.user_benefit_pain}</p>
                      </div>
                    )}

                    {step.value_created && (
                      <div>
                        <h6 className="text-sm font-medium text-ui-bodyText mb-1">
                          Value Created
                        </h6>
                        <p className="text-sm text-ui-supportText">{step.value_created}</p>
                      </div>
                    )}

                    {step.kpi_impact && (
                      <div>
                        <h6 className="text-sm font-medium text-ui-bodyText mb-1">KPI Impact</h6>
                        <p className="text-sm text-ui-supportText">{step.kpi_impact}</p>
                      </div>
                    )}

                    {/* Enrichment Summary */}
                    {hasEnrichment && step.enrichment.summary && (
                      <div>
                        <h6 className="text-sm font-medium text-ui-bodyText mb-1">AI Summary</h6>
                        <p className="text-sm text-ui-supportText">{step.enrichment.summary}</p>
                      </div>
                    )}

                    {/* Evidence */}
                    {hasEvidence && step.evidence && (
                      <div>
                        <h6 className="text-sm font-medium text-ui-bodyText mb-2">
                          Evidence ({step.evidence.length})
                        </h6>
                        <div className="space-y-2">
                          {step.evidence.map((evidence: any, idx: number) => (
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
