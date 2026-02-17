/**
 * CollaborationPanel - Right sidebar for collaboration features
 *
 * Contains:
 * - AI Chat interface (full WorkspaceChat) — switches to FeatureInfoCard + contextual chat during review
 * - Collab hub (phase-aware action panel)
 * - Activity feed (real collaboration events)
 *
 * Three-state width: collapsed (48px) | normal (320px) | wide (400px)
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  MessageSquare,
  GitBranch,
  Bell,
  ChevronLeft,
  ChevronRight,
  Maximize2,
  Minimize2,
  Clock,
  Users,
  Package,
  FileText,
  ArrowUpRight,
  CheckCircle,
  Loader2,
  Layers,
} from 'lucide-react'
import { WorkspaceChat, type ChatMessage } from './WorkspaceChat'
import { CollaborationHub } from './CollaborationHub'
import { getCollaborationHistory, getDIAgentLogs } from '@/lib/api'
import FeatureVerdictCard from '@/components/prototype/FeatureVerdictCard'
import VerdictChat from '@/components/prototype/VerdictChat'
import type { FeatureOverlay, FeatureVerdict, TourStep, PrototypeSession, SessionContext } from '@/types/prototype'

// =============================================================================
// Types
// =============================================================================

export type PanelState = 'collapsed' | 'normal' | 'wide'

interface CollaborationPanelProps {
  projectId: string
  projectName: string
  pendingCount?: number
  // Chat props (passed from WorkspaceLayout)
  messages: ChatMessage[]
  isChatLoading: boolean
  onSendMessage: (content: string) => Promise<void> | void
  onSendSignal?: (type: string, content: string, source: string) => Promise<void>
  onAddLocalMessage?: (msg: ChatMessage) => void
  // Panel state
  panelState: PanelState
  onPanelStateChange: (state: PanelState) => void
  // Review mode props
  isReviewActive?: boolean
  isTourActive?: boolean
  currentOverlay?: FeatureOverlay | null
  currentTourStep?: TourStep | null
  allOverlays?: FeatureOverlay[]
  visibleFeatureIds?: string[]
  session?: PrototypeSession | null
  sessionContext?: SessionContext | null
  prototypeId?: string | null
  onVerdictSubmit?: (overlayId: string, verdict: FeatureVerdict) => void
}

export function CollaborationPanel({
  projectId,
  projectName,
  pendingCount = 0,
  messages,
  isChatLoading,
  onSendMessage,
  onSendSignal,
  onAddLocalMessage,
  panelState,
  onPanelStateChange,
  isReviewActive = false,
  isTourActive = false,
  currentOverlay = null,
  currentTourStep = null,
  allOverlays = [],
  visibleFeatureIds = [],
  session = null,
  sessionContext = null,
  prototypeId = null,
  onVerdictSubmit,
}: CollaborationPanelProps) {
  const [activeTab, setActiveTab] = useState<'chat' | 'collab' | 'activity'>('chat')

  const isCollapsed = panelState === 'collapsed'
  const isWide = panelState === 'wide'

  // Review progress counts
  const reviewedCount = isReviewActive ? allOverlays.filter(o => o.consultant_verdict).length : 0
  const totalOverlays = isReviewActive ? allOverlays.length : 0

  const handleToggleCollapse = useCallback(() => {
    if (isCollapsed) {
      // Expand to last-known expanded state (default normal)
      onPanelStateChange('normal')
    } else {
      onPanelStateChange('collapsed')
    }
  }, [isCollapsed, onPanelStateChange])

  const handleToggleWide = useCallback(() => {
    onPanelStateChange(isWide ? 'normal' : 'wide')
  }, [isWide, onPanelStateChange])

  // Collapsed state — icon strip
  if (isCollapsed) {
    return (
      <aside className="fixed right-0 top-0 h-screen w-12 bg-white border-l border-ui-cardBorder flex flex-col items-center py-4 z-30">
        <button
          onClick={handleToggleCollapse}
          className="p-2 rounded-lg text-ui-supportText hover:bg-ui-background hover:text-ui-bodyText transition-colors mb-4"
          title="Expand panel"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex flex-col gap-2">
          <button
            onClick={() => { setActiveTab('chat'); handleToggleCollapse() }}
            className={`p-2 rounded-lg transition-colors ${
              activeTab === 'chat' ? 'bg-brand-teal/10 text-brand-teal' : 'text-ui-supportText hover:bg-ui-background'
            }`}
            title={isReviewActive ? 'Review' : 'Chat'}
          >
            {isReviewActive ? <Layers className="w-5 h-5" /> : <MessageSquare className="w-5 h-5" />}
          </button>
          <button
            onClick={() => { setActiveTab('collab'); handleToggleCollapse() }}
            className={`p-2 rounded-lg transition-colors ${
              activeTab === 'collab' ? 'bg-brand-teal/10 text-brand-teal' : 'text-ui-supportText hover:bg-ui-background'
            }`}
            title="Collaboration"
          >
            <GitBranch className="w-5 h-5" />
          </button>
          <button
            onClick={() => { setActiveTab('activity'); handleToggleCollapse() }}
            className={`p-2 rounded-lg transition-colors relative ${
              activeTab === 'activity' ? 'bg-brand-teal/10 text-brand-teal' : 'text-ui-supportText hover:bg-ui-background'
            }`}
            title="Activity"
          >
            <Bell className="w-5 h-5" />
            {pendingCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                {pendingCount > 9 ? '9+' : pendingCount}
              </span>
            )}
          </button>
        </div>
      </aside>
    )
  }

  // Expanded state
  const panelWidth = isWide ? 'w-[400px]' : 'w-80'

  return (
    <aside className={`fixed right-0 top-0 h-screen ${panelWidth} bg-white border-l border-ui-cardBorder flex flex-col z-30 transition-all duration-200`}>
      {/* Header — aligned with main header height */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-[#E5E5E5] flex-shrink-0">
        <div className="flex items-center gap-1 bg-[#F4F4F4] rounded-xl p-1 border border-[#E5E5E5] flex-1 min-w-0">
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex-1 px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors text-center ${
              activeTab === 'chat'
                ? 'bg-white text-[#3FAF7A] shadow-sm'
                : 'text-[#666666] hover:text-[#333333]'
            }`}
          >
            {isReviewActive ? (
              <>
                Review
                {totalOverlays > 0 && (
                  <span className="ml-1 text-[10px] font-normal text-[#999999]">
                    {reviewedCount}/{totalOverlays}
                  </span>
                )}
              </>
            ) : 'Chat'}
          </button>
          <button
            onClick={() => setActiveTab('collab')}
            className={`flex-1 px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors text-center ${
              activeTab === 'collab'
                ? 'bg-white text-[#3FAF7A] shadow-sm'
                : 'text-[#666666] hover:text-[#333333]'
            }`}
          >
            Collab
          </button>
          <button
            onClick={() => setActiveTab('activity')}
            className={`flex-1 px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors text-center relative ${
              activeTab === 'activity'
                ? 'bg-white text-[#3FAF7A] shadow-sm'
                : 'text-[#666666] hover:text-[#333333]'
            }`}
          >
            Activity
            {pendingCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 bg-[#3FAF7A] text-white text-[10px] font-bold rounded-full">
                {pendingCount}
              </span>
            )}
          </button>
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={handleToggleWide}
            className="p-1.5 rounded-lg text-[#999999] hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors"
            title={isWide ? 'Normal width' : 'Wide mode'}
          >
            {isWide ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={handleToggleCollapse}
            className="p-1.5 rounded-lg text-[#999999] hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors"
            title="Collapse panel"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden relative">
        {activeTab === 'chat' && (
          <div className="h-full">
            {isReviewActive && session ? (
              <ReviewPanel
                overlay={currentOverlay}
                tourStep={currentTourStep}
                isTourActive={isTourActive}
                allOverlays={allOverlays}
                visibleFeatureIds={visibleFeatureIds}
                session={session}
                sessionContext={sessionContext}
                prototypeId={prototypeId}
                onVerdictSubmit={onVerdictSubmit}
              />
            ) : (
              <WorkspaceChat
                projectId={projectId}
                messages={messages}
                isLoading={isChatLoading}
                onSendMessage={onSendMessage}
                onSendSignal={onSendSignal}
                onAddLocalMessage={onAddLocalMessage}
              />
            )}
          </div>
        )}

        {activeTab === 'collab' && (
          <CollaborationHub projectId={projectId} projectName={projectName} />
        )}

        {activeTab === 'activity' && (
          <ActivityFeed projectId={projectId} />
        )}
      </div>
    </aside>
  )
}

// =============================================================================
// Review Panel — Feature verdict cards during prototype review
// =============================================================================

interface ReviewPanelProps {
  overlay: FeatureOverlay | null
  tourStep: TourStep | null
  isTourActive: boolean
  allOverlays: FeatureOverlay[]
  visibleFeatureIds: string[]
  session: PrototypeSession
  sessionContext: SessionContext | null
  prototypeId?: string | null
  onVerdictSubmit?: (overlayId: string, verdict: FeatureVerdict) => void
}

function ReviewPanel({
  overlay,
  tourStep,
  isTourActive,
  allOverlays,
  session,
  sessionContext,
  prototypeId,
  onVerdictSubmit,
}: ReviewPanelProps) {
  // Verdict progress
  const reviewed = allOverlays.filter(o => o.consultant_verdict).length
  const total = allOverlays.length
  const verdictCounts = allOverlays.reduce(
    (acc, o) => {
      if (o.consultant_verdict === 'aligned') acc.aligned++
      else if (o.consultant_verdict === 'needs_adjustment') acc.needs_adjustment++
      else if (o.consultant_verdict === 'off_track') acc.off_track++
      return acc
    },
    { aligned: 0, needs_adjustment: 0, off_track: 0 }
  )

  return (
    <div className="flex flex-col h-full">
      {/* Scrollable content */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {overlay && prototypeId ? (
          /* Active feature — show verdict card */
          <div className="p-3">
            {tourStep?.vpStepLabel && (
              <div className="flex items-center gap-2 mb-2">
                <span className="text-[10px] font-medium text-[#3FAF7A]">{tourStep.vpStepLabel}</span>
              </div>
            )}
            <FeatureVerdictCard
              overlay={overlay}
              prototypeId={prototypeId}
              source="consultant"
              onVerdictSubmit={onVerdictSubmit}
            />

            {/* Verdict Chat — auto-opens when verdict is set */}
            {overlay.consultant_verdict && session && (
              <div className="mt-2">
                <VerdictChat
                  key={`${overlay.id}-${overlay.consultant_verdict}`}
                  overlay={overlay}
                  sessionId={session.id}
                  sessionContext={sessionContext}
                  verdict={overlay.consultant_verdict}
                  onDone={() => { /* notes saved via chat already */ }}
                />
              </div>
            )}
          </div>
        ) : (
          /* No feature selected — show compact scorecard */
          <div className="p-3">
            <div className="text-center py-4 mb-3">
              <Layers className="w-8 h-8 mx-auto mb-2 text-[#999999]" />
              <p className="text-xs text-[#666666]">
                {isTourActive ? 'Navigating to feature...' : 'Start the guided tour or click a feature'}
              </p>
            </div>

            {/* Feature list with verdict dots */}
            <div className="space-y-1">
              {allOverlays.filter(o => o.overlay_content).map(o => {
                const v = o.consultant_verdict
                return (
                  <div key={o.id} className="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-[#F4F4F4] transition-colors">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${
                      v === 'aligned' ? 'bg-[#25785A]' :
                      v === 'needs_adjustment' ? 'bg-amber-500' :
                      v === 'off_track' ? 'bg-red-500' :
                      'bg-[#E5E5E5]'
                    }`} />
                    <span className="text-xs text-[#333333] truncate flex-1">
                      {o.overlay_content!.feature_name}
                    </span>
                    {v && (
                      <span className={`text-[9px] font-medium px-1.5 py-px rounded-full ${
                        v === 'aligned' ? 'bg-[#E8F5E9] text-[#25785A]' :
                        v === 'needs_adjustment' ? 'bg-amber-50 text-amber-700' :
                        'bg-red-50 text-red-700'
                      }`}>
                        {v === 'aligned' ? 'Aligned' : v === 'needs_adjustment' ? 'Adjust' : 'Off Track'}
                      </span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Progress footer */}
      {total > 0 && (
        <div className="flex-shrink-0 border-t border-[#E5E5E5] px-3 py-2.5 bg-[#FAFAFA]">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-medium text-[#333333]">
              {reviewed}/{total} reviewed
            </span>
            <span className="text-[10px] text-[#999999]">
              {total - reviewed > 0 ? `${total - reviewed} remaining` : 'All done'}
            </span>
          </div>
          {/* Tri-color progress bar */}
          <div className="flex h-1.5 rounded-full overflow-hidden bg-[#E5E5E5]">
            {verdictCounts.aligned > 0 && (
              <div
                className="bg-[#25785A] transition-all"
                style={{ width: `${(verdictCounts.aligned / total) * 100}%` }}
              />
            )}
            {verdictCounts.needs_adjustment > 0 && (
              <div
                className="bg-amber-500 transition-all"
                style={{ width: `${(verdictCounts.needs_adjustment / total) * 100}%` }}
              />
            )}
            {verdictCounts.off_track > 0 && (
              <div
                className="bg-red-500 transition-all"
                style={{ width: `${(verdictCounts.off_track / total) * 100}%` }}
              />
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// =============================================================================
// Activity Feed — real collaboration events
// =============================================================================

interface ActivityEvent {
  id: string
  type: 'touchpoint' | 'package' | 'client' | 'phase' | 'agent'
  title: string
  detail?: string
  timestamp: string
  status?: string
}

function ActivityFeed({ projectId }: { projectId: string }) {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const [history, agentLogs] = await Promise.all([
          getCollaborationHistory(projectId).catch(() => null),
          getDIAgentLogs(projectId, { limit: 10 }).catch(() => null),
        ])

        if (cancelled) return

        const activityEvents: ActivityEvent[] = []

        // Touchpoint events
        if (history?.touchpoints) {
          for (const tp of history.touchpoints) {
            activityEvents.push({
              id: `tp-${tp.id}`,
              type: 'touchpoint',
              title: tp.title,
              detail: tp.outcomes_summary || undefined,
              timestamp: tp.completed_at || tp.created_at,
              status: tp.status,
            })
          }
        }

        // Agent log events (collaboration-relevant)
        if (agentLogs?.logs) {
          for (const log of agentLogs.logs) {
            const action = log.action_type || log.trigger || ''
            // Only show collaboration-relevant agent actions
            if (['generate_discovery_prep', 'send_to_portal', 'generate_package', 'process_responses', 'invite_client'].some(
              (a) => action.toLowerCase().includes(a) || (log.decision || '').toLowerCase().includes(a)
            )) {
              activityEvents.push({
                id: `agent-${log.id || Math.random()}`,
                type: 'agent',
                title: log.decision || action.replace(/_/g, ' '),
                detail: log.observation ? String(log.observation).slice(0, 80) : undefined,
                timestamp: log.created_at || new Date().toISOString(),
              })
            }
          }
        }

        // Sort by timestamp descending
        activityEvents.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())

        setEvents(activityEvents.slice(0, 20))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [projectId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-5 w-5 text-brand-teal animate-spin" />
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="p-4 text-center">
        <Bell className="w-8 h-8 mx-auto mb-2 text-ui-supportText/50" />
        <p className="text-xs text-ui-supportText">No activity yet</p>
        <p className="text-[11px] text-ui-supportText mt-1">
          Events will appear as you collaborate with clients
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="space-y-1">
        {events.map((event) => (
          <div key={event.id} className="flex items-start gap-2.5 py-2 border-b border-ui-cardBorder/50 last:border-0">
            <ActivityIcon type={event.type} status={event.status} />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-ui-bodyText leading-tight">{event.title}</p>
              {event.detail && (
                <p className="text-[11px] text-ui-supportText mt-0.5 truncate">{event.detail}</p>
              )}
              <p className="text-[10px] text-ui-supportText mt-0.5">
                {formatActivityTime(event.timestamp)}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ActivityIcon({ type, status }: { type: string; status?: string }) {
  const base = 'w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0'
  switch (type) {
    case 'touchpoint':
      return (
        <div className={`${base} ${status === 'completed' ? 'bg-green-100' : 'bg-blue-100'}`}>
          {status === 'completed' ? (
            <CheckCircle className="w-3 h-3 text-green-600" />
          ) : (
            <Clock className="w-3 h-3 text-blue-600" />
          )}
        </div>
      )
    case 'package':
      return <div className={`${base} bg-purple-100`}><Package className="w-3 h-3 text-purple-600" /></div>
    case 'client':
      return <div className={`${base} bg-teal-100`}><Users className="w-3 h-3 text-teal-600" /></div>
    case 'phase':
      return <div className={`${base} bg-amber-100`}><ArrowUpRight className="w-3 h-3 text-amber-600" /></div>
    case 'agent':
      return <div className={`${base} bg-gray-100`}><FileText className="w-3 h-3 text-gray-600" /></div>
    default:
      return <div className={`${base} bg-gray-100`}><Bell className="w-3 h-3 text-gray-500" /></div>
  }
}

function formatActivityTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHrs = Math.floor(diffMin / 60)
  const diffDays = Math.floor(diffHrs / 24)

  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  if (diffHrs < 24) return `${diffHrs}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export default CollaborationPanel
