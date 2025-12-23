/**
 * ConfirmationDetail Component
 *
 * Right column: Detailed view of selected confirmation
 * - Title, why, ask
 * - Evidence with source links
 * - Complexity scoring
 * - Status workflow (Resolve, Queue for Meeting, Dismiss)
 */

'use client'

import React, { useState } from 'react'
import { Card, CardHeader, EmptyState, Button } from '@/components/ui'
import { ComplexityBadge } from '@/components/ui/StatusBadge'
import { CheckSquare, CheckCircle, Phone, XCircle, AlertCircle, ExternalLink, MessageSquare } from 'lucide-react'
import type { Confirmation } from '@/types/api'
import { getComplexityScore, getComplexityBadge } from '@/lib/status-utils'

interface ConfirmationDetailProps {
  confirmation: Confirmation | null
  onResolve: (confirmationId: string) => Promise<void>
  onQueue: (confirmationId: string) => Promise<void>
  onDismiss: (confirmationId: string) => Promise<void>
  onViewEvidence: (chunkId: string) => void
  updating?: boolean
}

const KIND_LABELS: Record<string, string> = {
  prd: 'PRD Section',
  vp: 'Value Path Step',
  feature: 'Feature',
  insight: 'Red Team Insight',
  gate: 'Gate Validation',
}

export function ConfirmationDetail({
  confirmation,
  onResolve,
  onQueue,
  onDismiss,
  onViewEvidence,
  updating = false,
}: ConfirmationDetailProps) {
  const [showEvidence, setShowEvidence] = useState(true)

  if (!confirmation) {
    return (
      <EmptyState
        icon={<CheckSquare className="h-16 w-16" />}
        title="No Confirmation Selected"
        description="Select a confirmation from the list to view details and take action."
      />
    )
  }

  const complexityScore = getComplexityScore(confirmation)
  const complexityInfo = getComplexityBadge(complexityScore)

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card>
        <CardHeader
          title={confirmation.title}
          subtitle={KIND_LABELS[confirmation.kind] || confirmation.kind}
          actions={
            <div className="flex items-center gap-2">
              {confirmation.suggested_method === 'email' ? (
                <MessageSquare className="h-4 w-4 text-ui-supportText" />
              ) : (
                <Phone className="h-4 w-4 text-ui-supportText" />
              )}
              <span className="text-xs text-ui-supportText capitalize">
                {confirmation.suggested_method}
              </span>
            </div>
          }
        />

        {/* Complexity Scoring */}
        <div className="mt-4 pt-4 border-t border-ui-cardBorder">
          <h4 className="text-sm font-medium text-ui-bodyText mb-3">Complexity Assessment</h4>
          <div className="bg-ui-background p-4 rounded-lg border border-ui-cardBorder">
            <div className="flex items-center justify-between mb-2">
              <ComplexityBadge score={complexityScore} />
              <span className="text-sm font-semibold text-ui-bodyText">
                Score: {complexityScore}/10
              </span>
            </div>
            <p className="text-xs text-ui-supportText">{complexityInfo.description}</p>

            {/* Complexity Breakdown */}
            <div className="mt-3 pt-3 border-t border-ui-cardBorder space-y-1 text-xs text-ui-supportText">
              <div className="flex justify-between">
                <span>Base Priority ({confirmation.priority})</span>
                <span className="font-medium">
                  {confirmation.priority === 'high' ? '+3' : confirmation.priority === 'medium' ? '+2' : '+1'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Evidence Count ({confirmation.evidence.length})</span>
                <span className="font-medium">
                  {confirmation.evidence.length >= 3 ? '+2' : confirmation.evidence.length === 2 ? '+1' : '0'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Suggested Method ({confirmation.suggested_method})</span>
                <span className="font-medium">
                  {confirmation.suggested_method === 'meeting' ? '+2' : '0'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Status Actions */}
        <div className="mt-4 pt-4 border-t border-ui-cardBorder">
          <h4 className="text-sm font-medium text-ui-bodyText mb-3">Actions</h4>
          <div className="space-y-2">
            <Button
              variant="primary"
              onClick={() => onResolve(confirmation.id)}
              disabled={updating || confirmation.status === 'resolved'}
              icon={<CheckCircle className="h-4 w-4" />}
              fullWidth
            >
              Mark as Resolved
            </Button>
            <Button
              variant="secondary"
              onClick={() => onQueue(confirmation.id)}
              disabled={updating || confirmation.status === 'queued'}
              icon={<Phone className="h-4 w-4" />}
              fullWidth
            >
              Queue for Meeting
            </Button>
            <Button
              variant="outline"
              onClick={() => onDismiss(confirmation.id)}
              disabled={updating || confirmation.status === 'dismissed'}
              icon={<XCircle className="h-4 w-4" />}
              fullWidth
            >
              Dismiss
            </Button>
          </div>
          <p className="text-xs text-ui-supportText mt-3">
            Resolve if confirmed. Queue if needs discussion. Dismiss if not relevant.
          </p>
        </div>
      </Card>

      {/* Details Card */}
      <Card>
        <CardHeader title="Confirmation Details" />
        <div className="space-y-4">
          <div>
            <h5 className="text-sm font-medium text-ui-bodyText mb-2">Question for Client</h5>
            <p className="text-body text-ui-bodyText">{confirmation.ask}</p>
          </div>
          <div>
            <h5 className="text-sm font-medium text-ui-bodyText mb-2">Why This Needs Confirmation</h5>
            <p className="text-support text-ui-supportText">{confirmation.why}</p>
          </div>
          <div>
            <h5 className="text-sm font-medium text-ui-bodyText mb-2">Priority</h5>
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
              confirmation.priority === 'high' ? 'bg-red-100 text-red-800' :
              confirmation.priority === 'medium' ? 'bg-yellow-100 text-yellow-800' :
              'bg-green-100 text-green-800'
            }`}>
              {confirmation.priority.toUpperCase()} PRIORITY
            </span>
          </div>
        </div>
      </Card>

      {/* Evidence Card */}
      {confirmation.evidence && confirmation.evidence.length > 0 && (
        <Card>
          <CardHeader
            title={`Evidence (${confirmation.evidence.length})`}
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
              {confirmation.evidence.map((evidence, idx) => (
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
            <div className="text-support text-ui-supportText">Type</div>
            <div className="text-body text-ui-bodyText font-medium capitalize">{confirmation.kind}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Status</div>
            <div className="text-body text-ui-bodyText font-medium capitalize">{confirmation.status}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Suggested Method</div>
            <div className="text-body text-ui-bodyText font-medium capitalize">{confirmation.suggested_method}</div>
          </div>
          <div>
            <div className="text-support text-ui-supportText">Created</div>
            <div className="text-body text-ui-bodyText font-medium">
              {new Date(confirmation.created_at).toLocaleString()}
            </div>
          </div>
          <div className="col-span-2">
            <div className="text-support text-ui-supportText">Confirmation ID</div>
            <div className="text-xs font-mono text-ui-supportText">{confirmation.id}</div>
          </div>
        </div>
      </Card>
    </div>
  )
}
