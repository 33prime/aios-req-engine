/**
 * CollaborationHub - Phase-aware action panel for sidebar
 *
 * Shows:
 * - Current phase + readiness indicator
 * - "Next Action" card — the most important thing to do right now
 * - Quick stats (pending, clients, packages)
 * - Portal link
 * - Recent activity feed
 */

'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  ArrowRight,
  CheckCircle,
  Clock,
  ExternalLink,
  Loader2,
  Mail,
  Package,
  RefreshCw,
  Send,
  Target,
  Users,
  FileText,
  AlertTriangle,
} from 'lucide-react'
import {
  getPhaseProgress,
  getCollaborationHistory,
  generateDiscoveryPrep,
  generateClientPackage,
  inviteClient,
  type CollaborationHistoryResponse,
} from '@/lib/api'
import { formatRelativeTime } from '@/lib/date-utils'
import type { CollaborationPhase, PhaseGate, PhaseProgressResponse } from '@/types/api'
import { PendingItemsModal } from '@/components/collaboration/PendingItemsModal'
import { PrepReviewModal } from '@/components/collaboration/PrepReviewModal'
import { SendConfirmModal } from '@/components/collaboration/SendConfirmModal'
import { ClientPortalModal } from '@/components/collaboration/ClientPortalModal'

// =============================================================================
// Types
// =============================================================================

interface CollaborationHubProps {
  projectId: string
  projectName: string
}

interface NextAction {
  type: 'generate_prep' | 'review_prep' | 'invite_client' | 'send_prep' | 'awaiting_responses'
    | 'schedule_call' | 'review_pending' | 'generate_package' | 'review_package' | 'process_responses'
    | 'advance_phase' | 'setup_portal' | 'idle'
  label: string
  description: string
  cta?: string
  ctaAction?: () => Promise<void> | void
  progress?: { current: number; total: number }
}

// =============================================================================
// Phase display helpers
// =============================================================================

const PHASE_LABELS: Record<string, string> = {
  pre_discovery: 'Pre-Discovery',
  discovery: 'Discovery',
  validation: 'Validation',
  prototype: 'Prototype',
  proposal: 'Proposal',
  build: 'Build',
  delivery: 'Delivery',
}

function getPhaseLabel(phase: string): string {
  return PHASE_LABELS[phase] || phase.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

// =============================================================================
// Main Component
// =============================================================================

export function CollaborationHub({ projectId, projectName }: CollaborationHubProps) {
  const [progress, setProgress] = useState<PhaseProgressResponse | null>(null)
  const [history, setHistory] = useState<CollaborationHistoryResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [showInviteInput, setShowInviteInput] = useState(false)
  const [inviting, setInviting] = useState(false)

  // Modal states
  const [showPendingModal, setShowPendingModal] = useState(false)
  const [showClientsModal, setShowClientsModal] = useState(false)
  const [showPrepModal, setShowPrepModal] = useState(false)
  const [showSendConfirm, setShowSendConfirm] = useState(false)
  const [prepCounts, setPrepCounts] = useState({ questions: 0, documents: 0 })

  const portalUrl = process.env.NEXT_PUBLIC_PORTAL_URL || 'http://localhost:3001'

  // Fetch data
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const [progressData, historyData] = await Promise.all([
        getPhaseProgress(projectId).catch(() => null),
        getCollaborationHistory(projectId).catch(() => null),
      ])
      setProgress(progressData)
      setHistory(historyData)
    } finally {
      setLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Determine next action
  const nextAction = useMemo((): NextAction => {
    if (!progress) {
      return { type: 'idle', label: 'Loading...', description: 'Fetching collaboration data' }
    }

    const {
      current_phase,
      phase_config,
      pending_queue,
      draft_package,
      sent_package,
      package_responses,
      portal_enabled,
      clients_count,
    } = progress

    const pendingCount = pending_queue?.total_count || 0

    // Check gates in order — first unmet gate drives the next action
    if (phase_config?.gates) {
      for (const gate of phase_config.gates) {
        if (!gate.met) {
          return mapGateToAction(gate, current_phase, progress)
        }
      }
    }

    // If responses received, process them
    if (package_responses && package_responses.overall_progress > 0) {
      const answered = package_responses.questions_answered
      const total = package_responses.questions_total
      if (answered > 0) {
        return {
          type: 'process_responses',
          label: 'Process client responses',
          description: `${answered}/${total} questions answered. Review and incorporate feedback.`,
          cta: 'View Responses',
          progress: { current: answered, total },
        }
      }
    }

    // If sent package, awaiting
    if (sent_package && sent_package.status === 'sent') {
      return {
        type: 'awaiting_responses',
        label: 'Awaiting client responses',
        description: `Package sent with ${sent_package.questions_count} questions. Waiting for replies.`,
        progress: { current: 0, total: sent_package.questions_count },
      }
    }

    // If draft package, review it
    if (draft_package && draft_package.status === 'draft') {
      return {
        type: 'review_package',
        label: 'Review & send package',
        description: `Draft ready: ${draft_package.questions_count} questions, ${draft_package.action_items_count} action items.`,
        cta: 'Review Package',
      }
    }

    // Pending items need attention
    if (pendingCount > 0) {
      return {
        type: 'review_pending',
        label: `Review ${pendingCount} pending item${pendingCount !== 1 ? 's' : ''}`,
        description: 'Items need your review before advancing.',
        cta: 'Review Items',
      }
    }

    // Portal not enabled
    if (!portal_enabled) {
      return {
        type: 'setup_portal',
        label: 'Enable client portal',
        description: 'Set up the portal to start collaborating with clients.',
        cta: 'Enable Portal',
      }
    }

    // No clients
    if (clients_count === 0) {
      return {
        type: 'invite_client',
        label: 'Invite your first client',
        description: 'Add a client email to begin collaboration.',
        cta: 'Invite Client',
      }
    }

    // All gates met — advance
    return {
      type: 'advance_phase',
      label: 'Ready to advance',
      description: `All ${getPhaseLabel(current_phase)} gates are met. Consider moving to the next phase.`,
      cta: 'View Progress',
    }
  }, [progress])

  // Action handlers
  const handleGeneratePrep = useCallback(async () => {
    setActionLoading(true)
    try {
      await generateDiscoveryPrep(projectId)
      await loadData()
    } finally {
      setActionLoading(false)
    }
  }, [projectId, loadData])

  const handleGeneratePackage = useCallback(async () => {
    setActionLoading(true)
    try {
      await generateClientPackage(projectId, {})
      await loadData()
    } finally {
      setActionLoading(false)
    }
  }, [projectId, loadData])

  const handleInviteClient = useCallback(async () => {
    if (!inviteEmail.trim()) return
    setInviting(true)
    try {
      await inviteClient(projectId, { email: inviteEmail.trim(), send_email: true })
      setInviteEmail('')
      setShowInviteInput(false)
      await loadData()
    } finally {
      setInviting(false)
    }
  }, [projectId, inviteEmail, loadData])

  // Bind CTA actions
  const actionWithCta = useMemo((): NextAction => {
    const action = { ...nextAction }
    switch (action.type) {
      case 'generate_prep':
        action.ctaAction = handleGeneratePrep
        break
      case 'generate_package':
        action.ctaAction = handleGeneratePackage
        break
      case 'review_prep':
        action.ctaAction = () => setShowPrepModal(true)
        break
      case 'review_pending':
        action.ctaAction = () => setShowPendingModal(true)
        break
      case 'send_prep':
        action.ctaAction = () => setShowPrepModal(true)
        break
      case 'review_package':
        action.ctaAction = () => setShowPrepModal(true)
        break
      case 'invite_client':
        action.ctaAction = () => setShowInviteInput(true)
        break
    }
    return action
  }, [nextAction, handleGeneratePrep, handleGeneratePackage])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Loader2 className="h-6 w-6 text-brand-teal mx-auto mb-2 animate-spin" />
          <p className="text-xs text-ui-supportText">Loading collaboration...</p>
        </div>
      </div>
    )
  }

  if (!progress) {
    return (
      <div className="p-4 text-center">
        <p className="text-xs text-ui-supportText mb-2">Could not load collaboration data</p>
        <button onClick={loadData} className="text-xs text-brand-teal hover:text-brand-tealDark font-medium">
          Retry
        </button>
      </div>
    )
  }

  const readinessPercent = Math.round(progress.readiness_score * 100)
  const gates = progress.readiness_gates || []
  const gatesMet = gates.filter((g: PhaseGate) => g.met).length
  const gatesTotal = gates.length

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-3 space-y-3">
        {/* Phase + Readiness Indicator */}
        <div className="bg-ui-background rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide">
              {getPhaseLabel(progress.current_phase)}
            </span>
            <span className="text-xs font-medium text-brand-teal">
              {readinessPercent}%
            </span>
          </div>
          {/* Readiness bar */}
          <div className="h-1.5 bg-ui-cardBorder rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-teal rounded-full transition-all duration-500"
              style={{ width: `${readinessPercent}%` }}
            />
          </div>
          {/* Gates */}
          {gatesTotal > 0 && (
            <div className="flex items-center gap-1 mt-2">
              {gates.map((gate: PhaseGate, i: number) => (
                <div
                  key={i}
                  className={`w-2 h-2 rounded-full ${gate.met ? 'bg-brand-teal' : 'bg-ui-cardBorder'}`}
                  title={`${gate.label}: ${gate.met ? 'Met' : 'Not met'}`}
                />
              ))}
              <span className="text-[10px] text-ui-supportText ml-1">
                {gatesMet}/{gatesTotal} gates
              </span>
            </div>
          )}
        </div>

        {/* Next Action Card */}
        <div className="border border-brand-teal/30 bg-brand-teal/5 rounded-lg p-3">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Target className="h-3.5 w-3.5 text-brand-teal" />
            <span className="text-[11px] font-semibold text-brand-teal uppercase tracking-wide">Next Step</span>
          </div>
          <p className="text-sm font-medium text-ui-headingDark mb-1">
            {actionWithCta.label}
          </p>
          <p className="text-xs text-ui-supportText mb-2">
            {actionWithCta.description}
          </p>
          {/* Progress bar if applicable */}
          {actionWithCta.progress && (
            <div className="mb-2">
              <div className="h-1 bg-ui-cardBorder rounded-full overflow-hidden">
                <div
                  className="h-full bg-brand-teal rounded-full transition-all"
                  style={{ width: `${(actionWithCta.progress.current / actionWithCta.progress.total) * 100}%` }}
                />
              </div>
              <p className="text-[10px] text-ui-supportText mt-0.5">
                {actionWithCta.progress.current} / {actionWithCta.progress.total}
              </p>
            </div>
          )}
          {/* Inline invite input */}
          {showInviteInput && actionWithCta.type === 'invite_client' && (
            <div className="flex items-center gap-1.5 mb-2">
              <input
                type="email"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleInviteClient() }}
                placeholder="client@example.com"
                className="flex-1 px-2.5 py-1.5 border border-ui-cardBorder rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-brand-teal"
                disabled={inviting}
              />
              <button
                onClick={handleInviteClient}
                disabled={!inviteEmail.trim() || inviting}
                className="px-2.5 py-1.5 bg-brand-teal text-white text-xs font-medium rounded-lg disabled:opacity-50 hover:bg-brand-tealDark transition-colors"
              >
                {inviting ? <Loader2 className="h-3 w-3 animate-spin" /> : <Send className="h-3 w-3" />}
              </button>
            </div>
          )}
          {/* CTA button */}
          {actionWithCta.cta && actionWithCta.ctaAction && !showInviteInput && (
            <button
              onClick={actionWithCta.ctaAction}
              disabled={actionLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-teal text-white text-xs font-medium rounded-lg hover:bg-brand-tealDark transition-colors disabled:opacity-50"
            >
              {actionLoading ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <>
                  {actionWithCta.cta}
                  <ArrowRight className="h-3 w-3" />
                </>
              )}
            </button>
          )}
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-2">
          <StatPill
            value={progress.pending_queue?.total_count || 0}
            label="Pending"
            icon={<Clock className="h-3 w-3" />}
            highlight={!!progress.pending_queue?.total_count}
            onClick={() => setShowPendingModal(true)}
          />
          <StatPill
            value={progress.clients_count}
            label="Clients"
            icon={<Users className="h-3 w-3" />}
            onClick={() => setShowClientsModal(true)}
          />
          <StatPill
            value={(progress.draft_package ? 1 : 0) + (progress.sent_package ? 1 : 0)}
            label="Packages"
            icon={<Package className="h-3 w-3" />}
          />
        </div>

        {/* Portal Link */}
        {progress.portal_enabled && (
          <a
            href={`${portalUrl}/${projectId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-between px-3 py-2 bg-ui-background rounded-lg hover:bg-ui-buttonGrayHover transition-colors group"
          >
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500" />
              <span className="text-xs font-medium text-ui-bodyText">Portal: Enabled</span>
            </div>
            <ExternalLink className="h-3.5 w-3.5 text-ui-supportText group-hover:text-brand-teal transition-colors" />
          </a>
        )}

        {/* Refresh button */}
        <button
          onClick={loadData}
          className="flex items-center gap-1.5 text-[11px] text-ui-supportText hover:text-ui-bodyText transition-colors mx-auto"
        >
          <RefreshCw className="h-3 w-3" />
          Refresh
        </button>

        {/* Recent Activity */}
        {history && history.touchpoints.length > 0 && (
          <div>
            <p className="text-[11px] font-semibold text-ui-supportText uppercase tracking-wide mb-2">
              Recent
            </p>
            <div className="space-y-1.5">
              {history.touchpoints.slice(0, 3).map((tp) => (
                <div key={tp.id} className="flex items-start gap-2 text-xs">
                  <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                    tp.status === 'completed' ? 'bg-green-500' :
                    tp.status === 'in_progress' ? 'bg-amber-500' : 'bg-ui-cardBorder'
                  }`} />
                  <div className="min-w-0">
                    <p className="text-ui-bodyText truncate">{tp.title}</p>
                    <p className="text-[10px] text-ui-supportText">
                      {formatRelativeTime(tp.completed_at || tp.created_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Summary stats from history */}
        {history && (history.total_questions_answered > 0 || history.total_documents_received > 0) && (
          <div className="bg-ui-background rounded-lg p-2.5">
            <p className="text-[11px] font-semibold text-ui-supportText uppercase tracking-wide mb-1.5">
              All Time
            </p>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
              {history.total_questions_answered > 0 && (
                <div className="text-ui-bodyText">
                  <span className="font-medium">{history.total_questions_answered}</span> answers
                </div>
              )}
              {history.total_documents_received > 0 && (
                <div className="text-ui-bodyText">
                  <span className="font-medium">{history.total_documents_received}</span> docs
                </div>
              )}
              {history.total_features_extracted > 0 && (
                <div className="text-ui-bodyText">
                  <span className="font-medium">{history.total_features_extracted}</span> features
                </div>
              )}
              {history.total_items_confirmed > 0 && (
                <div className="text-ui-bodyText">
                  <span className="font-medium">{history.total_items_confirmed}</span> confirmed
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      <PendingItemsModal
        projectId={projectId}
        isOpen={showPendingModal}
        onClose={() => setShowPendingModal(false)}
        onRefresh={loadData}
      />
      <ClientPortalModal
        projectId={projectId}
        projectName={projectName}
        isOpen={showClientsModal}
        onClose={() => setShowClientsModal(false)}
        onRefresh={loadData}
      />
      <PrepReviewModal
        projectId={projectId}
        isOpen={showPrepModal}
        onClose={() => setShowPrepModal(false)}
        onRefresh={loadData}
        onSendRequest={(qCount, dCount) => {
          setPrepCounts({ questions: qCount, documents: dCount })
          setShowPrepModal(false)
          setShowSendConfirm(true)
        }}
      />
      <SendConfirmModal
        projectId={projectId}
        isOpen={showSendConfirm}
        onClose={() => setShowSendConfirm(false)}
        onRefresh={loadData}
        questionCount={prepCounts.questions}
        documentCount={prepCounts.documents}
      />
    </div>
  )
}

// =============================================================================
// Sub-components
// =============================================================================

function StatPill({
  value,
  label,
  icon,
  highlight = false,
  onClick,
}: {
  value: number
  label: string
  icon: React.ReactNode
  highlight?: boolean
  onClick?: () => void
}) {
  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className={`rounded-lg p-2 text-center w-full transition-colors
        ${highlight ? 'bg-amber-50 border border-amber-200' : 'bg-ui-background'}
        ${onClick ? 'cursor-pointer hover:ring-1 hover:ring-brand-teal/30' : ''}`}
    >
      <div className={`flex items-center justify-center gap-1 ${highlight ? 'text-amber-700' : 'text-ui-bodyText'}`}>
        {icon}
        <span className="text-sm font-semibold">{value}</span>
      </div>
      <p className={`text-[10px] ${highlight ? 'text-amber-600' : 'text-ui-supportText'}`}>{label}</p>
    </button>
  )
}

// =============================================================================
// Helpers
// =============================================================================

function mapGateToAction(
  gate: PhaseGate,
  phase: CollaborationPhase,
  progress: PhaseProgressResponse,
): NextAction {
  const gateId = gate.id || gate.label.toLowerCase().replace(/\s+/g, '_')

  // Map common gate patterns to actions
  if (gateId.includes('prep') && gateId.includes('generated') || gate.label.toLowerCase().includes('prep generated')) {
    return {
      type: 'generate_prep',
      label: 'Generate discovery prep',
      description: 'Create prep questions for client before the discovery call.',
      cta: 'Generate Prep',
    }
  }

  if (gateId.includes('prep') && gateId.includes('confirmed') || gate.label.toLowerCase().includes('confirmed')) {
    return {
      type: 'review_prep',
      label: 'Review & confirm prep',
      description: 'Review generated prep questions before sending to clients.',
      cta: 'Review Prep',
    }
  }

  if (gateId.includes('client') && gateId.includes('invited') || gate.label.toLowerCase().includes('invited')) {
    return {
      type: 'invite_client',
      label: 'Invite a client',
      description: 'Add client collaborators to the project portal.',
      cta: 'Invite Client',
    }
  }

  if (gateId.includes('sent') || gate.label.toLowerCase().includes('sent to portal')) {
    return {
      type: 'send_prep',
      label: 'Send prep to portal',
      description: 'Push confirmed prep questions to the client portal.',
      cta: 'Send to Portal',
    }
  }

  if (gateId.includes('call') || gate.label.toLowerCase().includes('call')) {
    return {
      type: 'schedule_call',
      label: 'Schedule discovery call',
      description: gate.condition || 'Set up a discovery call with stakeholders.',
      cta: 'Schedule Call',
    }
  }

  if (gateId.includes('package') && gateId.includes('generated')) {
    return {
      type: 'generate_package',
      label: 'Generate client package',
      description: 'Create synthesized questions from your findings.',
      cta: 'Generate Package',
    }
  }

  // Fallback: use gate label directly
  return {
    type: 'review_pending',
    label: gate.label,
    description: gate.condition || `This gate needs to be met to advance: ${gate.label}`,
    cta: 'View Details',
  }
}

export default CollaborationHub
