/**
 * CollaborationPanel - Right sidebar for chat + activity in non-review mode.
 *
 * Review mode is now handled by ReviewBubble instead.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import {
  MessageSquare,
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
} from 'lucide-react'
import { WorkspaceChat, type ChatMessage } from './WorkspaceChat'
import { getCollaborationHistory } from '@/lib/api'

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
}: CollaborationPanelProps) {
  const [activeTab, setActiveTab] = useState<'chat' | 'activity'>('chat')

  const isCollapsed = panelState === 'collapsed'

  const handleToggleCollapse = useCallback(() => {
    if (isCollapsed) {
      onPanelStateChange('normal')
    } else {
      onPanelStateChange('collapsed')
    }
  }, [isCollapsed, onPanelStateChange])

  // Collapsed state — icon strip
  if (isCollapsed) {
    return (
      <aside className="fixed right-0 top-0 h-screen w-12 bg-white border-l border-border flex flex-col items-center py-4 z-30">
        <button
          onClick={handleToggleCollapse}
          className="p-2 rounded-lg text-text-placeholder hover:bg-surface-muted hover:text-text-body transition-colors mb-4"
          title="Expand panel"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <div className="flex flex-col gap-2">
          <button
            onClick={() => { setActiveTab('chat'); handleToggleCollapse() }}
            className={`p-2 rounded-lg transition-colors ${
              activeTab === 'chat' ? 'bg-brand-primary-light text-brand-primary' : 'text-text-placeholder hover:bg-surface-muted'
            }`}
            title="Chat"
          >
            <MessageSquare className="w-5 h-5" />
          </button>
          <button
            onClick={() => { setActiveTab('activity'); handleToggleCollapse() }}
            className={`p-2 rounded-lg transition-colors relative ${
              activeTab === 'activity' ? 'bg-brand-primary-light text-brand-primary' : 'text-text-placeholder hover:bg-surface-muted'
            }`}
            title="Activity"
          >
            <Bell className="w-5 h-5" />
            {pendingCount > 0 && (
              <span className="absolute -top-1 -right-1 w-4 h-4 bg-brand-primary text-white text-xs rounded-full flex items-center justify-center">
                {pendingCount > 9 ? '9+' : pendingCount}
              </span>
            )}
          </button>
        </div>
      </aside>
    )
  }

  // Normal mode — Chat | Activity tabs
  const panelWidth = panelState === 'wide' ? 'w-[400px]' : 'w-80'
  const isWide = panelState === 'wide'

  return (
    <aside className={`fixed right-0 top-0 h-screen ${panelWidth} bg-white border-l border-border flex flex-col z-30 transition-all duration-200`}>
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-border flex-shrink-0">
        <div className="flex items-center gap-1 bg-[#F4F4F4] rounded-xl p-1 border border-border flex-1 min-w-0">
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex-1 px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors text-center ${
              activeTab === 'chat'
                ? 'bg-white text-brand-primary shadow-sm'
                : 'text-[#666666] hover:text-text-body'
            }`}
          >
            Chat
          </button>
          <button
            onClick={() => setActiveTab('activity')}
            className={`flex-1 px-3 py-1.5 text-[13px] font-medium rounded-lg transition-colors text-center relative ${
              activeTab === 'activity'
                ? 'bg-white text-brand-primary shadow-sm'
                : 'text-[#666666] hover:text-text-body'
            }`}
          >
            Activity
            {pendingCount > 0 && (
              <span className="ml-1 px-1.5 py-0.5 bg-brand-primary text-white text-[10px] font-bold rounded-full">
                {pendingCount}
              </span>
            )}
          </button>
        </div>
        <div className="flex items-center gap-0.5 shrink-0">
          <button
            onClick={() => onPanelStateChange(isWide ? 'normal' : 'wide')}
            className="p-1.5 rounded-lg text-text-placeholder hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors"
            title={isWide ? 'Normal width' : 'Wide mode'}
          >
            {isWide ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={handleToggleCollapse}
            className="p-1.5 rounded-lg text-text-placeholder hover:bg-[#F4F4F4] hover:text-[#666666] transition-colors"
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
            <WorkspaceChat
              projectId={projectId}
              messages={messages}
              isLoading={isChatLoading}
              onSendMessage={onSendMessage}
              onSendSignal={onSendSignal}
              onAddLocalMessage={onAddLocalMessage}
            />
          </div>
        )}

        {activeTab === 'activity' && (
          <ActivityFeed projectId={projectId} />
        )}
      </div>
    </aside>
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
        const history = await getCollaborationHistory(projectId).catch(() => null)

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
        <Loader2 className="h-5 w-5 text-brand-primary animate-spin" />
      </div>
    )
  }

  if (events.length === 0) {
    return (
      <div className="p-4 text-center">
        <Bell className="w-8 h-8 mx-auto mb-2 text-text-placeholder/50" />
        <p className="text-xs text-text-placeholder">No activity yet</p>
        <p className="text-[11px] text-text-placeholder mt-1">
          Events will appear as you collaborate with clients
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-3">
      <div className="space-y-1">
        {events.map((event) => (
          <div key={event.id} className="flex items-start gap-2.5 py-2 border-b border-border/50 last:border-0">
            <ActivityIcon type={event.type} status={event.status} />
            <div className="flex-1 min-w-0">
              <p className="text-xs text-text-body leading-tight">{event.title}</p>
              {event.detail && (
                <p className="text-[11px] text-text-placeholder mt-0.5 truncate">{event.detail}</p>
              )}
              <p className="text-[10px] text-text-placeholder mt-0.5">
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
            <Clock className="w-3 h-3 text-brand-primary" />
          )}
        </div>
      )
    case 'package':
      return <div className={`${base} bg-[#E8F5E9]`}><Package className="w-3 h-3 text-[#25785A]" /></div>
    case 'client':
      return <div className={`${base} bg-[#E8F5E9]`}><Users className="w-3 h-3 text-[#25785A]" /></div>
    case 'phase':
      return <div className={`${base} bg-[#F4F4F4]`}><ArrowUpRight className="w-3 h-3 text-[#666666]" /></div>
    case 'agent':
      return <div className={`${base} bg-[#F4F4F4]`}><FileText className="w-3 h-3 text-[#666666]" /></div>
    default:
      return <div className={`${base} bg-[#F4F4F4]`}><Bell className="w-3 h-3 text-[#666666]" /></div>
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
