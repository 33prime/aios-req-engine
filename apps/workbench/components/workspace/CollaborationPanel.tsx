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
  Send,
} from 'lucide-react'
import { WorkspaceChat, type ChatMessage } from './WorkspaceChat'
import { CollaborationHub } from './CollaborationHub'
import { getCollaborationHistory, getDIAgentLogs, submitPrototypeFeedback } from '@/lib/api'
import { FeatureInfoTabs } from '@/components/prototype/FeatureInfoCard'
import type { FeatureOverlay, TourStep, PrototypeSession, SubmitFeedbackRequest, SessionContext } from '@/types/prototype'

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
  answeredQuestionIds?: Set<string>
  onQuestionAnswered?: (questionId: string) => void
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
  answeredQuestionIds,
  onQuestionAnswered,
}: CollaborationPanelProps) {
  const [activeTab, setActiveTab] = useState<'chat' | 'collab' | 'activity'>('chat')

  const isCollapsed = panelState === 'collapsed'
  const isWide = panelState === 'wide'

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
      {/* Header — matches main header height (px-6 py-4) */}
      <div className="flex items-center justify-between px-4 py-4 border-b border-[#E5E5E5] flex-shrink-0">
        <div className="flex items-center gap-1 bg-[#F4F4F4] rounded-xl p-1 border border-[#E5E5E5]">
          <button
            onClick={() => setActiveTab('chat')}
            className={`px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors ${
              activeTab === 'chat'
                ? 'bg-white text-[#3FAF7A] shadow-sm'
                : 'text-[#666666] hover:text-[#333333]'
            }`}
          >
            {isReviewActive ? 'Review' : 'Chat'}
          </button>
          <button
            onClick={() => setActiveTab('collab')}
            className={`px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors ${
              activeTab === 'collab'
                ? 'bg-white text-[#3FAF7A] shadow-sm'
                : 'text-[#666666] hover:text-[#333333]'
            }`}
          >
            Collab
          </button>
          <button
            onClick={() => setActiveTab('activity')}
            className={`px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors relative ${
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
        <div className="flex items-center gap-0.5">
          {/* Wide toggle */}
          <button
            onClick={handleToggleWide}
            className="p-1.5 rounded-lg text-[#999999] hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors"
            title={isWide ? 'Normal width' : 'Wide mode'}
          >
            {isWide ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          {/* Collapse */}
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
                answeredQuestionIds={answeredQuestionIds}
                onQuestionAnswered={onQuestionAnswered}
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
// Review Panel — Conversational question-answering during prototype review
// =============================================================================

const MAX_QUESTIONS_PER_FEATURE = 3

interface ReviewPanelProps {
  overlay: FeatureOverlay | null
  tourStep: TourStep | null
  isTourActive: boolean
  allOverlays: FeatureOverlay[]
  visibleFeatureIds: string[]
  session: PrototypeSession
  sessionContext: SessionContext | null
  answeredQuestionIds?: Set<string>
  onQuestionAnswered?: (questionId: string) => void
}

interface FeatureQuestionGroup {
  featureName: string
  featureId: string
  status: string
  confidence: number
  questions: Array<{ id: string; question: string; category: string; priority: string; answer: string | null }>
}

function ReviewPanel({
  overlay,
  tourStep,
  isTourActive,
  allOverlays,
  visibleFeatureIds,
  session,
  sessionContext,
  answeredQuestionIds,
  onQuestionAnswered,
}: ReviewPanelProps) {
  const [answerText, setAnswerText] = useState('')
  const [activeQuestionId, setActiveQuestionId] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Build question groups: single feature during tour, all visible features otherwise
  const questionGroups: FeatureQuestionGroup[] = (() => {
    if (isTourActive && overlay?.overlay_content) {
      // Tour mode: single feature, top 3 questions
      const content = overlay.overlay_content
      const unanswered = content.questions
        .filter((q) => !q.answer && !answeredQuestionIds?.has(q.id))
        .sort((a, b) => {
          const prio: Record<string, number> = { high: 0, medium: 1, low: 2 }
          return (prio[a.priority] ?? 2) - (prio[b.priority] ?? 2)
        })
        .slice(0, MAX_QUESTIONS_PER_FEATURE)
      return [{
        featureName: content.feature_name,
        featureId: overlay.feature_id || overlay.id,
        status: content.status,
        confidence: content.confidence,
        questions: unanswered,
      }]
    }

    if (overlay?.overlay_content && !isTourActive) {
      // Radar dot clicked: show that feature's top 3 questions
      const content = overlay.overlay_content
      const unanswered = content.questions
        .filter((q) => !q.answer && !answeredQuestionIds?.has(q.id))
        .sort((a, b) => {
          const prio: Record<string, number> = { high: 0, medium: 1, low: 2 }
          return (prio[a.priority] ?? 2) - (prio[b.priority] ?? 2)
        })
        .slice(0, MAX_QUESTIONS_PER_FEATURE)
      return [{
        featureName: content.feature_name,
        featureId: overlay.feature_id || overlay.id,
        status: content.status,
        confidence: content.confidence,
        questions: unanswered,
      }]
    }

    // No specific feature: show all visible features' questions
    const groups: FeatureQuestionGroup[] = []
    for (const ov of allOverlays) {
      if (!ov.overlay_content) continue
      const fid = ov.feature_id || ov.id
      // Show all overlays when no visible features tracked yet, otherwise filter
      if (visibleFeatureIds.length > 0 && !visibleFeatureIds.includes(fid)) continue
      const content = ov.overlay_content
      const unanswered = content.questions
        .filter((q) => !q.answer && !answeredQuestionIds?.has(q.id))
        .sort((a, b) => {
          const prio: Record<string, number> = { high: 0, medium: 1, low: 2 }
          return (prio[a.priority] ?? 2) - (prio[b.priority] ?? 2)
        })
        .slice(0, MAX_QUESTIONS_PER_FEATURE)
      if (unanswered.length > 0) {
        groups.push({
          featureName: content.feature_name,
          featureId: fid,
          status: content.status,
          confidence: content.confidence,
          questions: unanswered,
        })
      }
    }
    return groups
  })()

  const totalOpen = questionGroups.reduce((sum, g) => sum + g.questions.length, 0)

  const handleAnswerSubmit = async () => {
    if (!activeQuestionId || !answerText.trim() || !session) return

    setIsSubmitting(true)
    try {
      const req: SubmitFeedbackRequest = {
        content: answerText.trim(),
        feedback_type: 'answer',
        answers_question_id: activeQuestionId,
        feature_id: overlay?.feature_id || undefined,
        page_path: sessionContext?.current_page,
        component_name: overlay?.component_name || undefined,
        context: sessionContext || undefined,
      }
      await submitPrototypeFeedback(session.id, req)
      onQuestionAnswered?.(activeQuestionId)
      setAnswerText('')
      setActiveQuestionId(null)
    } catch (err) {
      console.error('Failed to submit answer:', err)
    } finally {
      setIsSubmitting(false)
    }
  }

  const activeOverlayContent = overlay?.overlay_content

  return (
    <div className="flex flex-col h-full">
      {/* Compact feature header — shown when a specific feature is selected */}
      {activeOverlayContent && (
        <div className="flex-shrink-0 border-b border-ui-cardBorder px-3 py-2.5">
          <div className="flex items-center gap-2">
            <p className="text-xs font-semibold text-ui-headingDark truncate">
              {activeOverlayContent.feature_name}
            </p>
            <span className={`text-[9px] font-medium px-1.5 py-px rounded-full flex-shrink-0 ${
              activeOverlayContent.status === 'understood' ? 'bg-emerald-100 text-emerald-700' :
              activeOverlayContent.status === 'partial' ? 'bg-amber-100 text-amber-700' :
              'bg-gray-100 text-gray-500'
            }`}>
              {activeOverlayContent.status}
            </span>
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <div className="w-12 h-1 bg-gray-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full ${
                  activeOverlayContent.confidence >= 0.7 ? 'bg-emerald-400' :
                  activeOverlayContent.confidence >= 0.4 ? 'bg-amber-400' : 'bg-red-400'
                }`}
                style={{ width: `${activeOverlayContent.confidence * 100}%` }}
              />
            </div>
            <span className="text-[10px] text-ui-supportText">
              {Math.round(activeOverlayContent.confidence * 100)}% confidence
            </span>
            {tourStep?.vpStepLabel && (
              <span className="text-[10px] text-brand-primary">{tourStep.vpStepLabel}</span>
            )}
          </div>
        </div>
      )}

      {/* Scrollable content: info tabs + questions */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {/* Feature info tabs — Overview, Impact, Gaps, Flow */}
        {activeOverlayContent && (
          <div className="border-b border-ui-cardBorder">
            <FeatureInfoTabs content={activeOverlayContent} tourStep={tourStep} />
          </div>
        )}

        <div className="px-3 py-2 sticky top-0 bg-white/90 backdrop-blur-sm border-b border-ui-cardBorder/50 z-10">
          <span className="text-[11px] font-semibold text-ui-headingDark uppercase tracking-wide">
            {totalOpen > 0 ? `${totalOpen} questions to review` : 'All caught up'}
          </span>
        </div>

        <div className="p-3 space-y-4">
          {questionGroups.length === 0 && (
            <div className="text-center py-8">
              <div className="w-10 h-10 mx-auto mb-2 rounded-full bg-emerald-50 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-emerald-500" />
              </div>
              <p className="text-xs text-ui-supportText">
                {isTourActive ? 'No questions for this feature' : 'Click a feature dot in the prototype to see its questions'}
              </p>
            </div>
          )}

          {questionGroups.map((group) => (
            <div key={group.featureId}>
              {/* Feature group header — only show when multiple features */}
              {(questionGroups.length > 1 || !isTourActive) && (
                <div className="flex items-center gap-2 mb-2">
                  <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                    group.status === 'understood' ? 'bg-emerald-400' :
                    group.status === 'partial' ? 'bg-amber-400' : 'bg-gray-300'
                  }`} />
                  <span className="text-[11px] font-medium text-ui-headingDark truncate">{group.featureName}</span>
                  <span className="text-[10px] text-ui-supportText ml-auto">{group.questions.length}</span>
                </div>
              )}

              {/* Question thread */}
              <div className="space-y-2">
                {group.questions.map((q) => (
                  <div key={q.id}>
                    {/* Question bubble — left aligned like incoming message */}
                    <div
                      onClick={() => setActiveQuestionId(activeQuestionId === q.id ? null : q.id)}
                      className={`rounded-xl px-3 py-2 cursor-pointer transition-all ${
                        activeQuestionId === q.id
                          ? 'bg-brand-primary/8 ring-1 ring-brand-primary/20'
                          : 'bg-ui-background hover:bg-gray-100'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${
                          q.priority === 'high' ? 'bg-brand-primary' :
                          q.priority === 'medium' ? 'bg-brand-accent' : 'bg-gray-300'
                        }`} />
                        <p className="text-xs text-ui-bodyText leading-relaxed">{q.question}</p>
                      </div>
                    </div>

                    {/* Answer input — right aligned like outgoing message */}
                    {activeQuestionId === q.id && (
                      <div className="mt-1.5 ml-4 flex items-center gap-1.5">
                        <input
                          type="text"
                          value={answerText}
                          onChange={(e) => setAnswerText(e.target.value)}
                          onKeyDown={(e) => e.key === 'Enter' && handleAnswerSubmit()}
                          placeholder="Type your answer..."
                          className="flex-1 px-3 py-2 text-xs bg-white border border-ui-cardBorder rounded-xl focus:outline-none focus:ring-1 focus:ring-brand-teal/30 focus:border-brand-teal"
                          disabled={isSubmitting}
                          autoFocus
                        />
                        <button
                          onClick={handleAnswerSubmit}
                          disabled={!answerText.trim() || isSubmitting}
                          className="p-2 rounded-xl bg-brand-teal text-white hover:bg-brand-tealDark disabled:opacity-40 transition-colors"
                        >
                          <Send className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
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
