/**
 * InsightDetail Component
 *
 * Right column: Detailed view of selected insight
 * - Finding, why, ask
 * - Targets (affected entities)
 * - Evidence links
 * - Decision workflow (Apply Internally, Needs Confirmation, Dismiss)
 */

'use client'

import React, { useState } from 'react'
import { Card, CardHeader, EmptyState, Button, ButtonGroup } from '@/components/ui'
import { SeverityBadge, GateBadge } from '@/components/ui/StatusBadge'
import { AlertCircle, CheckCircle, AlertTriangle, XCircle, ExternalLink, Target } from 'lucide-react'
import type { Insight } from '@/types/api'

interface InsightDetailProps {
  insight: Insight | null
  onApplyInternally: (insightId: string) => Promise<void>
  onNeedsConfirmation: (insightId: string) => Promise<void>
  onDismiss: (insightId: string) => Promise<void>
  onViewEvidence: (chunkId: string) => void
  updating?: boolean
}

const GATE_DESCRIPTIONS: Record<string, string> = {
  completeness: 'Can we build a prototype with what we know?',
  validation: 'Is this optimal per research?',
  assumption: 'Are our assumptions solid?',
  scope: 'Is the VP staying focused?',
  wow: 'Will this impress the client?',
}

export function InsightDetail({
  insight,
  onApplyInternally,
  onNeedsConfirmation,
  onDismiss,
  onViewEvidence,
  updating = false,
}: InsightDetailProps) {
  const [showEvidence, setShowEvidence] = useState(false)

  if (!insight) {
    return (
      <EmptyState
        icon={<AlertCircle className="h-16 w-16" />}
        title="No Insight Selected"
        description="Select an insight from the list to view details and make decisions."
      />
    )
  }

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card>
        <CardHeader
          title={insight.title}
          subtitle={GATE_DESCRIPTIONS[insight.gate] || insight.gate}
          actions={
            <div className="flex items-center gap-2">
              <GateBadge gate={insight.gate} showTooltip />
              <SeverityBadge severity={insight.severity} />
            </div>
          }
        />

        {/* Decision Actions */}
        <div className="mt-4 pt-4 border-t border-ui-cardBorder">
          <h4 className="text-sm font-medium text-ui-bodyText mb-3">Consultant Decision</h4>
          <div className="space-y-2">
            <Button
              variant="primary"
              onClick={() => onApplyInternally(insight.id)}
              disabled={updating}
              icon={<CheckCircle className="h-4 w-4" />}
              fullWidth
            >
              Apply Internally
            </Button>
            <Button
              variant="secondary"
              onClick={() => onNeedsConfirmation(insight.id)}
              disabled={updating}
              icon={<AlertTriangle className="h-4 w-4" />}
              fullWidth
            >
              Needs Client Confirmation
            </Button>
            <Button
              variant="outline"
              onClick={() => onDismiss(insight.id)}
              disabled={updating}
              icon={<XCircle className="h-4 w-4" />}
              fullWidth
            >
              Dismiss
            </Button>
          </div>
          <p className="text-xs text-ui-supportText mt-3">
            Apply if you can address this internally. Mark for confirmation if client input is needed. Dismiss if not relevant.
          </p>
        </div>
      </Card>

      {/* Finding Card */}
      <Card>
        <CardHeader title="Gap Analysis" />
        <div className="space-y-4">
          <div>
            <h5 className="text-sm font-medium text-ui-bodyText mb-2">Finding</h5>
            <p className="text-body text-ui-bodyText">{insight.finding}</p>
          </div>
          <div>
            <h5 className="text-sm font-medium text-ui-bodyText mb-2">Why This Matters</h5>
            <p className="text-support text-ui-supportText">{insight.why}</p>
          </div>
          <div>
            <h5 className="text-sm font-medium text-ui-bodyText mb-2">Recommended Action</h5>
            <p className="text-support text-ui-supportText">{insight.ask}</p>
          </div>
        </div>
      </Card>

      {/* Targets Card */}
      {insight.targets && insight.targets.length > 0 && (
        <Card>
          <CardHeader
            title={`Affected Entities (${insight.targets.length})`}
            subtitle="PRD sections, VP steps, or features impacted by this insight"
          />
          <div className="space-y-2">
            {insight.targets.map((target, idx) => (
              <div
                key={idx}
                className="bg-ui-background border border-ui-cardBorder rounded-lg p-3 flex items-center gap-3"
              >
                <Target className="h-4 w-4 text-brand-accent flex-shrink-0" />
                <div className="flex-1">
                  <div className="text-sm font-medium text-ui-bodyText">{target.label}</div>
                  <div className="text-xs text-ui-supportText capitalize">{target.kind}</div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Evidence Card */}
      {insight.evidence && insight.evidence.length > 0 && (
        <Card>
          <CardHeader
            title={`Evidence (${insight.evidence.length})`}
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
              {insight.evidence.map((evidence, idx) => (
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
            <div className="text-support text-ui-supportText">Severity</div>
            <div className="text-body text-ui-bodyText font-medium capitalize">{insight.severity}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Gate</div>
            <div className="text-body text-ui-bodyText font-medium capitalize">{insight.gate}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Status</div>
            <div className="text-body text-ui-bodyText font-medium capitalize">{insight.status || 'open'}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Created</div>
            <div className="text-body text-ui-bodyText font-medium">
              {new Date(insight.created_at).toLocaleString()}
            </div>
          </div>
          <div className="col-span-2">
            <div className="text-support text-ui-supportText">Insight ID</div>
            <div className="text-xs font-mono text-ui-supportText">{insight.id}</div>
          </div>
        </div>
      </Card>
    </div>
  )
}
