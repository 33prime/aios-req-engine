/**
 * HistoryPanel - Memory & Activity view
 *
 * Two sub-tabs:
 * - Memory: decisions, learnings, synthesis
 * - Activity: DI Agent action log timeline
 */

'use client'

import { useState, useEffect } from 'react'
import {
  Zap,
  Brain,
  CheckCircle,
  AlertTriangle,
  Lightbulb,
  MessageSquare,
  RefreshCw,
  Clock,
} from 'lucide-react'
import { getProjectMemory, synthesizeMemory } from '@/lib/api'
import { formatDate } from '@/lib/date-utils'
import type { ProjectMemory } from '@/lib/api'

interface HistoryPanelProps {
  projectId: string
}

type HistoryTab = 'memory' | 'activity'

export function HistoryPanel({ projectId }: HistoryPanelProps) {
  const [activeTab, setActiveTab] = useState<HistoryTab>('memory')

  return (
    <div>
      {/* Tab Navigation */}
      <div className="flex gap-1 mb-4 -mt-1">
        <button
          onClick={() => setActiveTab('memory')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
            activeTab === 'memory'
              ? 'bg-brand-primary-light text-brand-primary'
              : 'text-text-placeholder hover:text-text-body hover:bg-surface-muted'
          }`}
        >
          <Brain className="w-3.5 h-3.5" />
          Memory
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium transition-colors ${
            activeTab === 'activity'
              ? 'bg-brand-primary-light text-brand-primary'
              : 'text-text-placeholder hover:text-text-body hover:bg-surface-muted'
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          Activity
        </button>
      </div>

      {activeTab === 'memory' && <MemoryTab projectId={projectId} />}
      {activeTab === 'activity' && <ActivityTab projectId={projectId} />}
    </div>
  )
}

// Memory Tab

function MemoryTab({ projectId }: { projectId: string }) {
  const [memory, setMemory] = useState<ProjectMemory | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSynthesizing, setIsSynthesizing] = useState(false)

  useEffect(() => {
    getProjectMemory(projectId)
      .then(setMemory)
      .catch(() => setMemory(null))
      .finally(() => setIsLoading(false))
  }, [projectId])

  const handleSynthesize = async () => {
    setIsSynthesizing(true)
    try {
      await synthesizeMemory(projectId)
      // Reload memory after synthesis
      const updated = await getProjectMemory(projectId)
      setMemory(updated)
    } catch {
      // Silently handle - synthesis may fail if no data
    } finally {
      setIsSynthesizing(false)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-primary" />
      </div>
    )
  }

  const hasData = memory && (
    memory.decisions.length > 0 ||
    memory.learnings.length > 0 ||
    memory.questions.length > 0
  )

  if (!hasData) {
    return (
      <div className="text-center py-6">
        <Brain className="w-8 h-8 text-gray-300 mx-auto mb-2" />
        <p className="text-sm text-text-placeholder mb-3">No memory entries yet.</p>
        <button
          onClick={handleSynthesize}
          disabled={isSynthesizing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-brand-primary hover:bg-brand-primary-light rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isSynthesizing ? 'animate-spin' : ''}`} />
          Synthesize Memory
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Synthesize button */}
      <div className="flex justify-end">
        <button
          onClick={handleSynthesize}
          disabled={isSynthesizing}
          className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-brand-primary hover:bg-brand-primary-light rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-3 h-3 ${isSynthesizing ? 'animate-spin' : ''}`} />
          Synthesize
        </button>
      </div>

      {/* Decisions */}
      {memory!.decisions.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-text-body uppercase tracking-wide mb-2">
            Decisions ({memory!.decisions.length})
          </h5>
          <div className="space-y-2">
            {memory!.decisions.map((d) => (
              <div key={d.id} className="bg-surface-muted rounded-lg px-3 py-2">
                <p className="text-sm text-text-body">{d.content}</p>
                {d.rationale && (
                  <p className="text-[11px] text-text-placeholder mt-1">{d.rationale}</p>
                )}
                <p className="text-[10px] text-text-placeholder mt-1">
                  {formatDate(d.created_at)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Learnings */}
      {memory!.learnings.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-text-body uppercase tracking-wide mb-2">
            Learnings ({memory!.learnings.length})
          </h5>
          <div className="space-y-2">
            {memory!.learnings.map((l) => (
              <div key={l.id} className="flex items-start gap-2 bg-surface-muted rounded-lg px-3 py-2">
                <Lightbulb className="w-4 h-4 text-amber-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-text-body">{l.content}</p>
                  <p className="text-[10px] text-text-placeholder mt-1">
                    {formatDate(l.created_at)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Open Questions */}
      {memory!.questions.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-text-body uppercase tracking-wide mb-2">
            Open Questions ({memory!.questions.filter((q) => !q.resolved).length})
          </h5>
          <div className="space-y-2">
            {memory!.questions.map((q) => (
              <div key={q.id} className="flex items-start gap-2 bg-surface-muted rounded-lg px-3 py-2">
                <MessageSquare className={`w-4 h-4 flex-shrink-0 mt-0.5 ${q.resolved ? 'text-green-500' : 'text-blue-500'}`} />
                <div>
                  <p className={`text-sm ${q.resolved ? 'text-text-placeholder line-through' : 'text-text-body'}`}>
                    {q.content}
                  </p>
                  <p className="text-[10px] text-text-placeholder mt-1">
                    {formatDate(q.created_at)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Activity Tab

const ACTION_BADGES: Record<string, { label: string; color: string; icon: typeof Zap }> = {
  extract: { label: 'Extract', color: 'bg-blue-100 text-brand-primary-hover', icon: Brain },
  enrich: { label: 'Enrich', color: 'bg-purple-100 text-purple-700', icon: Zap },
  validate: { label: 'Validate', color: 'bg-green-100 text-green-700', icon: CheckCircle },
  warn: { label: 'Warning', color: 'bg-amber-100 text-amber-700', icon: AlertTriangle },
  observe: { label: 'Observe', color: 'bg-gray-100 text-gray-700', icon: Brain },
}

function formatTimestamp(dateStr: string) {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHrs = Math.floor(diffMins / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  const diffDays = Math.floor(diffHrs / 24)
  return `${diffDays}d ago`
}

function ActivityTab({ projectId }: { projectId: string }) {
  const [logs, setLogs] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // DI Agent removed — activity tab shows empty until replaced
    setLogs([])
    setIsLoading(false)
  }, [projectId])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-brand-primary" />
      </div>
    )
  }

  if (logs.length === 0) {
    return (
      <p className="text-sm text-text-placeholder text-center py-8">
        No activity recorded yet. Agent actions will appear here.
      </p>
    )
  }

  return (
    <div className="space-y-0">
      {logs.map((log, idx) => {
        const actionType = log.action_type || 'observe'
        const badge = ACTION_BADGES[actionType] || ACTION_BADGES.observe
        const Icon = badge.icon

        return (
          <div key={log.id || idx} className="flex items-start gap-3 py-3 border-b border-gray-100 last:border-0">
            <div className="flex-shrink-0 mt-0.5">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${badge.color}`}>
                <Icon className="w-3 h-3" />
                {badge.label}
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-text-body line-clamp-2">
                {log.observation || log.decision || 'Agent action completed'}
              </p>
            </div>
            <span className="text-[11px] text-text-placeholder flex-shrink-0">
              {log.created_at ? formatTimestamp(log.created_at) : ''}
            </span>
          </div>
        )
      })}
    </div>
  )
}
