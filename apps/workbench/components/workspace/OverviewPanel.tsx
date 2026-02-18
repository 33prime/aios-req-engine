/**
 * OverviewPanel - Project Dashboard
 *
 * Layout:
 *   Hero: Project name + vision + completeness ring + phase
 *   Row 1: Project Pulse (with health) | Next Best Actions (top 3) | Tasks
 *   Row 2: Recent Activity | Upcoming Meetings | Client Portal
 */

'use client'

import { useState, useEffect } from 'react'
import {
  ListTodo,
  ArrowRight,
  Activity,
  CheckCircle,
  MessageCircle,
  AlertTriangle,
  RefreshCw,
  Calendar,
  Globe,
  Sparkles,
} from 'lucide-react'
import { TaskListCompact } from '@/components/tasks'
import { CompletenessRing } from '@/components/workspace/brd/components/CompletenessRing'
import {
  getTaskStats,
  getCollaborationHistory,
  getQuestionCounts,
  getBRDHealth,
} from '@/lib/api'
import type { CanvasData, BRDWorkspaceData, SectionScore, QuestionCounts, BRDHealthData } from '@/types/workspace'
import type { ReadinessScore, NextAction, TaskStatsResponse, CollaborationHistoryResponse, TerseAction } from '@/lib/api'
import { GAP_SOURCE_ICONS, GAP_SOURCE_COLORS, PHASE_LABELS } from '@/lib/action-constants'

interface OverviewPanelProps {
  projectId: string
  canvasData: CanvasData
  readinessData: ReadinessScore | null
  brdData: BRDWorkspaceData | null
  nextActions: NextAction[] | null
  contextActions?: TerseAction[]
  initialTaskStats?: TaskStatsResponse | null
  initialHistory?: CollaborationHistoryResponse | null
  initialQuestionCounts?: QuestionCounts | null
  onNavigateToPhase: (phase: 'discovery' | 'build') => void
  onActionExecute?: (action: NextAction) => void
}

const SECTION_LABELS: Record<string, string> = {
  vision: 'Vision',
  constraints: 'Constraints',
  data_entities: 'Data Entities',
  stakeholders: 'Stakeholders',
  workflows: 'Workflows',
  features: 'Features',
}

export function OverviewPanel({
  projectId,
  canvasData,
  brdData,
  contextActions,
  initialTaskStats,
  initialHistory,
  initialQuestionCounts,
  onNavigateToPhase,
}: OverviewPanelProps) {
  const [taskStats, setTaskStats] = useState<TaskStatsResponse | null>(initialTaskStats ?? null)
  const [taskRefreshKey, setTaskRefreshKey] = useState(0)
  const [history, setHistory] = useState<CollaborationHistoryResponse | null>(initialHistory ?? null)
  const [questionCounts, setQuestionCounts] = useState<QuestionCounts | null>(initialQuestionCounts ?? null)
  const [healthData, setHealthData] = useState<BRDHealthData | null>(null)

  useEffect(() => {
    // Fetch data not prefetched by parent
    const promises: Promise<unknown>[] = []
    if (initialTaskStats === undefined) promises.push(getTaskStats(projectId).then(setTaskStats).catch(() => null))
    if (initialHistory === undefined) promises.push(getCollaborationHistory(projectId).then(setHistory).catch(() => null))
    if (initialQuestionCounts === undefined) promises.push(getQuestionCounts(projectId).then(setQuestionCounts).catch(() => null))
    // Always fetch health data (not prefetched)
    promises.push(getBRDHealth(projectId).then(setHealthData).catch(() => null))
    Promise.all(promises)
  }, [projectId, initialTaskStats, initialHistory, initialQuestionCounts])

  const pendingCount = taskStats?.by_status?.pending ?? 0
  const completeness = brdData?.completeness ?? null
  const touchpoints = history?.touchpoints ?? []
  const overallScore = completeness?.overall_score ?? 0
  const phase = canvasData.collaboration_phase || 'discovery'

  // Use context frame actions (top 3) for the actions card
  const topActions = contextActions?.slice(0, 3) ?? []

  return (
    <div className="space-y-4">
      {/* Hero: Project Dashboard Header */}
      <HeroDashboard
        projectName={canvasData.project_name}
        pitchLine={canvasData.pitch_line}
        overallScore={overallScore}
        overallLabel={completeness?.overall_label ?? 'Getting Started'}
        phase={phase}
        onNavigateToPhase={onNavigateToPhase}
      />

      {/* Row 1: Pulse | Actions | Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ProjectPulseCard
          completeness={completeness}
          sections={completeness?.sections ?? []}
          questionCounts={questionCounts}
          healthData={healthData}
        />

        <ContextActionsCard
          actions={topActions}
          onNavigateToPhase={onNavigateToPhase}
        />

        <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5 overflow-hidden">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-1.5">
              <ListTodo className="w-4 h-4 text-[#3FAF7A]" />
              <h2 className="text-[13px] font-semibold text-[#333333]">Tasks</h2>
            </div>
            {pendingCount > 0 && (
              <span className="text-[10px] font-medium text-[#25785A] bg-[#E8F5E9] px-1.5 py-0.5 rounded-full">
                {pendingCount} pending
              </span>
            )}
          </div>
          <div className="overflow-hidden [&_label]:text-xs [&_span]:text-[11px] [&_p]:text-xs [&_.task-card]:p-2">
            <TaskListCompact
              projectId={projectId}
              maxItems={3}
              filter="pending"
              refreshKey={taskRefreshKey}
              onTasksChange={() => {
                setTaskRefreshKey((k) => k + 1)
                getTaskStats(projectId).then(setTaskStats).catch(() => {})
              }}
            />
          </div>
        </div>
      </div>

      {/* Row 2: Activity | Meetings | Portal */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ActivityCard touchpoints={touchpoints} />
        <UpcomingMeetingsCard />
        <ClientPortalCard />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Hero Dashboard Header
// ---------------------------------------------------------------------------

function HeroDashboard({
  projectName,
  pitchLine,
  overallScore,
  overallLabel,
  phase,
  onNavigateToPhase,
}: {
  projectName: string
  pitchLine?: string | null
  overallScore: number
  overallLabel: string
  phase: string
  onNavigateToPhase: (phase: 'discovery' | 'build') => void
}) {
  const phaseLabel = PHASE_LABELS[phase] || phase

  return (
    <div className="bg-[#0A1E2F] rounded-2xl shadow-md p-6 flex items-center gap-6">
      {/* Completeness ring */}
      <div className="flex-shrink-0">
        <div className="relative w-20 h-20">
          <svg className="w-20 h-20 -rotate-90" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="42" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="6" />
            <circle
              cx="50"
              cy="50"
              r="42"
              fill="none"
              stroke="#3FAF7A"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 42}
              strokeDashoffset={2 * Math.PI * 42 - (overallScore / 100) * 2 * Math.PI * 42}
              className="transition-all duration-1000 ease-out"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[20px] font-bold text-white leading-none">{Math.round(overallScore)}%</span>
            <span className="text-[10px] text-white/50 mt-0.5">{overallLabel}</span>
          </div>
        </div>
      </div>

      {/* Project info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h1 className="text-[18px] font-bold text-white truncate">{projectName}</h1>
          <span className="flex-shrink-0 px-2 py-0.5 text-[10px] font-medium text-[#3FAF7A] bg-[#3FAF7A]/10 rounded-full">
            {phaseLabel}
          </span>
        </div>
        {pitchLine && (
          <p className="text-[13px] text-white/60 leading-relaxed line-clamp-2">{pitchLine}</p>
        )}
      </div>

      {/* CTA */}
      <button
        onClick={() => onNavigateToPhase('discovery')}
        className="flex-shrink-0 inline-flex items-center gap-1.5 px-5 py-2.5 text-[13px] font-medium text-[#0A1E2F] bg-[#3FAF7A] rounded-xl hover:bg-[#4CC08C] transition-colors"
      >
        Open BRD
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Project Pulse (merged with Health)
// ---------------------------------------------------------------------------

function ProjectPulseCard({
  completeness,
  sections,
  questionCounts,
  healthData,
}: {
  completeness: BRDWorkspaceData['completeness'] | null
  sections: SectionScore[]
  questionCounts: QuestionCounts | null
  healthData: BRDHealthData | null
}) {
  const gapCount = completeness?.top_gaps?.length ?? 0
  const totalStale = healthData?.stale_entities?.total_stale ?? 0
  const scopeAlerts = healthData?.scope_alerts ?? []
  const hasAlerts = totalStale > 0 || scopeAlerts.length > 0

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
      <div className="flex items-center gap-1.5 mb-4">
        <Activity className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[13px] font-semibold text-[#333333]">Project Pulse</h2>
      </div>

      {/* Section bars */}
      <div className="space-y-2 mb-3">
        {sections.map((sec) => (
          <SectionBar
            key={sec.section}
            label={SECTION_LABELS[sec.section] || sec.section}
            score={sec.score}
            maxScore={sec.max_score}
          />
        ))}
        {sections.length === 0 && (
          <p className="text-[11px] text-[#999999] py-2">No data yet — start uploading signals</p>
        )}
      </div>

      {/* Gap + question counts */}
      {(gapCount > 0 || (questionCounts && questionCounts.open > 0)) && (
        <div className="flex items-center gap-3 pt-2 border-t border-[#E5E5E5] mb-3">
          {gapCount > 0 && (
            <p className="text-[11px] text-[#999999]">
              {gapCount} gap{gapCount !== 1 ? 's' : ''} to address
            </p>
          )}
          {questionCounts && questionCounts.open > 0 && (
            <span className="inline-flex items-center gap-1 text-[11px] text-[#999999]">
              <MessageCircle className="w-3 h-3" />
              {questionCounts.open} open question{questionCounts.open !== 1 ? 's' : ''}
              {questionCounts.critical_open > 0 && (
                <span className="text-[10px] font-medium text-[#991B1B]">
                  ({questionCounts.critical_open} critical)
                </span>
              )}
            </span>
          )}
        </div>
      )}

      {/* Health alerts (merged from ProjectHealthOverlay) */}
      {hasAlerts && (
        <div className="space-y-1.5 pt-2 border-t border-[#E5E5E5]">
          {totalStale > 0 && (
            <div className="flex items-center gap-2 px-2.5 py-1.5 bg-[#FFF8F0] rounded-lg">
              <RefreshCw className="w-3 h-3 text-amber-500 flex-shrink-0" />
              <p className="text-[11px] text-[#666666]">
                {totalStale} stale {totalStale === 1 ? 'entity' : 'entities'} need refreshing
              </p>
            </div>
          )}
          {scopeAlerts.slice(0, 2).map((alert, i) => (
            <div key={i} className="flex items-center gap-2 px-2.5 py-1.5 bg-[#FFF8F0] rounded-lg">
              <AlertTriangle className="w-3 h-3 text-amber-500 flex-shrink-0" />
              <p className="text-[11px] text-[#666666]">{alert.message}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function SectionBar({
  label,
  score,
  maxScore,
}: {
  label: string
  score: number
  maxScore: number
}) {
  const pct = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0
  const fillBg = pct >= 80 ? 'bg-[#25785A]' : pct >= 60 ? 'bg-[#3FAF7A]' : 'bg-[#999999]'

  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[10px] text-[#666666] w-20 truncate">{label}</span>
      <div className="flex-1 h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${fillBg}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] font-medium text-[#666666] w-8 text-right tabular-nums">{pct}%</span>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Context Frame Actions (top 3)
// ---------------------------------------------------------------------------

function ContextActionsCard({
  actions,
  onNavigateToPhase,
}: {
  actions: TerseAction[]
  onNavigateToPhase: (phase: 'discovery' | 'build') => void
}) {
  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5 flex flex-col">
      <div className="flex items-center gap-1.5 mb-3">
        <Sparkles className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[13px] font-semibold text-[#333333]">Next Best Actions</h2>
      </div>

      {actions.length > 0 ? (
        <div className="flex-1 flex flex-col gap-2">
          {actions.map((action, idx) => {
            const sourceColor = GAP_SOURCE_COLORS[action.gap_source] || '#999999'
            const Icon = GAP_SOURCE_ICONS[action.gap_type] || GAP_SOURCE_ICONS[action.gap_source] || Sparkles
            return (
              <button
                key={action.action_id}
                onClick={() => onNavigateToPhase('discovery')}
                className="flex-1 flex items-start gap-3 p-3 bg-[#F4F4F4] rounded-xl text-left hover:bg-[#EEEEEE] transition-colors cursor-pointer group"
              >
                <span
                  className="flex items-center justify-center w-5 h-5 rounded-full text-[11px] font-semibold flex-shrink-0 mt-0.5"
                  style={{
                    backgroundColor: sourceColor + '18',
                    color: sourceColor,
                  }}
                >
                  {idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <Icon className="w-3 h-3 flex-shrink-0" style={{ color: sourceColor }} />
                    <span
                      className="text-[10px] font-medium uppercase tracking-wide"
                      style={{ color: sourceColor }}
                    >
                      {action.gap_source}
                    </span>
                  </div>
                  <p className="text-[12px] text-[#333333] leading-relaxed">{action.sentence}</p>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[#E5E5E5] group-hover:text-[#3FAF7A] transition-colors flex-shrink-0 mt-0.5" />
              </button>
            )
          })}
        </div>
      ) : (
        <div className="flex-1 flex flex-col items-center justify-center py-4">
          <div className="w-10 h-10 rounded-full bg-[#E8F5E9] flex items-center justify-center mb-2">
            <CheckCircle className="w-5 h-5 text-[#25785A]" />
          </div>
          <p className="text-[12px] font-medium text-[#333333]">Looking good</p>
          <p className="text-[11px] text-[#999999] mt-0.5">No actions needed right now</p>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Activity Card (resized from strip to card)
// ---------------------------------------------------------------------------

function ActivityCard({
  touchpoints,
}: {
  touchpoints: CollaborationHistoryResponse['touchpoints']
}) {
  const items = touchpoints.slice(0, 4)

  const formatRelativeTime = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    const hours = Math.floor(mins / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  const statusBadgeClass = (status: string) => {
    if (status === 'completed') return 'bg-[#E8F5E9] text-[#25785A]'
    return 'bg-[#F0F0F0] text-[#666666]'
  }

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
      <div className="flex items-center gap-1.5 mb-3">
        <Activity className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[13px] font-semibold text-[#333333]">Recent Activity</h2>
      </div>

      {items.length > 0 ? (
        <div className="space-y-2">
          {items.map((tp) => (
            <div
              key={tp.id}
              className="flex items-center gap-2.5 p-2.5 bg-[#F4F4F4] rounded-xl"
            >
              <Activity className="w-3 h-3 text-[#999999] flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-medium text-[#333333] truncate">{tp.title}</p>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded-full ${statusBadgeClass(tp.status)}`}>
                    {tp.status}
                  </span>
                  <span className="text-[10px] text-[#999999]">
                    {formatRelativeTime(tp.completed_at || tp.created_at)}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-4">
          <Activity className="w-6 h-6 text-[#E5E5E5] mb-2" />
          <p className="text-[11px] text-[#999999]">No activity yet</p>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Upcoming Meetings (placeholder)
// ---------------------------------------------------------------------------

function UpcomingMeetingsCard() {
  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
      <div className="flex items-center gap-1.5 mb-3">
        <Calendar className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[13px] font-semibold text-[#333333]">Upcoming Meetings</h2>
      </div>
      <div className="flex flex-col items-center justify-center py-4">
        <div className="w-10 h-10 rounded-full bg-[#F4F4F4] flex items-center justify-center mb-2">
          <Calendar className="w-5 h-5 text-[#E5E5E5]" />
        </div>
        <p className="text-[12px] font-medium text-[#333333]">Coming soon</p>
        <p className="text-[11px] text-[#999999] mt-0.5 text-center">
          Calendar sync and meeting prep
        </p>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Client Portal (placeholder)
// ---------------------------------------------------------------------------

function ClientPortalCard() {
  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
      <div className="flex items-center gap-1.5 mb-3">
        <Globe className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[13px] font-semibold text-[#333333]">Client Portal</h2>
      </div>
      <div className="flex flex-col items-center justify-center py-4">
        <div className="w-10 h-10 rounded-full bg-[#F4F4F4] flex items-center justify-center mb-2">
          <Globe className="w-5 h-5 text-[#E5E5E5]" />
        </div>
        <p className="text-[12px] font-medium text-[#333333]">Coming soon</p>
        <p className="text-[11px] text-[#999999] mt-0.5 text-center">
          Client review notifications
        </p>
      </div>
    </div>
  )
}

export default OverviewPanel
