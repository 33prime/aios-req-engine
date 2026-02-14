/**
 * OverviewPanel - Hero Action + Pulse Grid dashboard
 *
 * Layout:
 *   Hero Action Banner (full-width, top next action)
 *   Three-column grid: Project Pulse | Next Best Actions | Tasks
 *   Recent Activity strip (full-width)
 */

'use client'

import { useState, useEffect } from 'react'
import {
  Target,
  Lightbulb,
  Users,
  FileText,
  ListTodo,
  ArrowRight,
  Activity,
  CheckCircle,
} from 'lucide-react'
import { TaskListCompact } from '@/components/tasks'
import { CompletenessRing } from '@/components/workspace/brd/components/CompletenessRing'
import {
  getTaskStats,
  getCollaborationHistory,
} from '@/lib/api'
import type { CanvasData, BRDWorkspaceData, SectionScore } from '@/types/workspace'
import type { ReadinessScore, NextAction, TaskStatsResponse, CollaborationHistoryResponse } from '@/lib/api'

interface OverviewPanelProps {
  projectId: string
  canvasData: CanvasData
  readinessData: ReadinessScore | null
  brdData: BRDWorkspaceData | null
  nextActions: NextAction[] | null
  onNavigateToPhase: (phase: 'discovery' | 'build') => void
}

const ACTION_ICONS: Record<string, typeof Target> = {
  confirm_critical: Target,
  stakeholder_gap: Users,
  section_gap: FileText,
  missing_evidence: FileText,
  validate_pains: Target,
  missing_vision: Lightbulb,
  missing_metrics: Target,
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
  readinessData,
  brdData,
  nextActions,
  onNavigateToPhase,
}: OverviewPanelProps) {
  const [taskStats, setTaskStats] = useState<TaskStatsResponse | null>(null)
  const [taskRefreshKey, setTaskRefreshKey] = useState(0)
  const [history, setHistory] = useState<CollaborationHistoryResponse | null>(null)

  useEffect(() => {
    const load = async () => {
      const [stats, hist] = await Promise.all([
        getTaskStats(projectId).catch(() => null),
        getCollaborationHistory(projectId).catch(() => null),
      ])
      setTaskStats(stats)
      setHistory(hist)
    }
    load()
  }, [projectId])

  const pendingCount = taskStats?.by_status?.pending ?? 0
  const actions = nextActions ?? []
  const heroAction = actions[0] ?? null
  const remainingActions = actions.length > 1 ? actions.slice(1, 3) : actions.length === 1 ? [actions[0]] : []
  const completeness = brdData?.completeness ?? null
  const touchpoints = history?.touchpoints ?? []
  const prototypeReadiness = readinessData?.score ?? canvasData.readiness_score ?? 0

  return (
    <div className="space-y-4">
      {/* Hero Action Banner */}
      <HeroActionBanner
        action={heroAction}
        onNavigateToPhase={onNavigateToPhase}
      />

      {/* Three-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Column 1: Project Pulse */}
        <ProjectPulseCard
          completeness={completeness}
          sections={completeness?.sections ?? []}
          prototypeReadiness={prototypeReadiness}
          hasReadinessData={!!readinessData}
        />

        {/* Column 2: Next Best Actions */}
        <NextActionsCard
          actions={remainingActions}
          startIndex={actions.length > 1 ? 2 : 1}
        />

        {/* Column 3: Tasks */}
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

      {/* Recent Activity strip */}
      <ActivityStrip touchpoints={touchpoints} />
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components (internal only)
// ---------------------------------------------------------------------------

function HeroActionBanner({
  action,
  onNavigateToPhase,
}: {
  action: NextAction | null
  onNavigateToPhase: (phase: 'discovery' | 'build') => void
}) {
  if (!action) {
    return (
      <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] p-5 flex items-center gap-4">
        <div className="flex items-center justify-center w-10 h-10 rounded-full bg-[#E8F5E9]">
          <CheckCircle className="w-5 h-5 text-[#25785A]" />
        </div>
        <div className="flex-1">
          <h2 className="text-[15px] font-semibold text-[#333333]">
            Your BRD is looking great!
          </h2>
          <p className="text-[13px] text-[#666666] mt-0.5">
            No recommended actions right now. Keep refining your discovery.
          </p>
        </div>
      </div>
    )
  }

  const Icon = ACTION_ICONS[action.action_type] || Target

  return (
    <div className="bg-white rounded-2xl shadow-md border border-[#E5E5E5] border-l-4 border-l-[#3FAF7A] p-5 flex items-start gap-4">
      <span className="flex items-center justify-center w-7 h-7 rounded-full bg-[#E8F5E9] text-[13px] font-semibold text-[#25785A] flex-shrink-0 mt-0.5">
        1
      </span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <Icon className="w-4 h-4 text-[#999999] flex-shrink-0" />
          <h2 className="text-[15px] font-semibold text-[#333333]">{action.title}</h2>
        </div>
        <p className="text-[13px] text-[#666666] leading-relaxed">{action.description}</p>
        {(action.suggested_stakeholder_role || action.suggested_artifact) && (
          <div className="flex items-center gap-2 mt-2">
            {action.suggested_stakeholder_role && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                <Users className="w-2.5 h-2.5" />
                {action.suggested_stakeholder_role}
              </span>
            )}
            {action.suggested_artifact && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-[#F0F0F0] text-[#666666] rounded-full">
                <FileText className="w-2.5 h-2.5" />
                {action.suggested_artifact}
              </span>
            )}
          </div>
        )}
      </div>
      <button
        onClick={() => onNavigateToPhase('discovery')}
        className="flex-shrink-0 inline-flex items-center gap-1.5 px-4 py-2 text-[12px] font-medium text-white bg-[#3FAF7A] rounded-xl hover:bg-[#25785A] transition-colors"
      >
        Go to Discovery
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

function ProjectPulseCard({
  completeness,
  sections,
  prototypeReadiness,
  hasReadinessData,
}: {
  completeness: BRDWorkspaceData['completeness'] | null
  sections: SectionScore[]
  prototypeReadiness: number
  hasReadinessData: boolean
}) {
  const overallScore = completeness?.overall_score ?? 0
  const overallLabel = completeness?.overall_label ?? 'Poor'
  const gapCount = completeness?.top_gaps?.length ?? 0

  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
      <div className="flex items-center gap-1.5 mb-4">
        <Target className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[13px] font-semibold text-[#333333]">Project Pulse</h2>
      </div>

      {/* Ring + overall label */}
      <div className="flex items-center gap-4 mb-4">
        <CompletenessRing score={overallScore} size="lg" />
        <div>
          <p className="text-[22px] font-bold text-[#333333] leading-none">{Math.round(overallScore)}%</p>
          <p className="text-[12px] text-[#666666] mt-0.5">{overallLabel}</p>
        </div>
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
      </div>

      {/* Gap count footer */}
      {gapCount > 0 && (
        <p className="text-[11px] text-[#999999] pt-2 border-t border-[#E5E5E5]">
          {gapCount} gap{gapCount !== 1 ? 's' : ''} to address
        </p>
      )}

      {/* Prototype readiness (secondary) */}
      {hasReadinessData && (
        <div className="flex items-center gap-2 mt-2 pt-2 border-t border-[#E5E5E5]">
          <span className="text-[10px] text-[#999999]">Prototype Readiness:</span>
          <div className="flex-1 h-1 bg-[#E5E5E5] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-[#3FAF7A] transition-all duration-500"
              style={{ width: `${Math.min(prototypeReadiness, 100)}%` }}
            />
          </div>
          <span className="text-[10px] font-medium text-[#666666] tabular-nums">
            {Math.round(prototypeReadiness)}%
          </span>
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
  const barColor = pct >= 80 ? 'bg-[#25785A]' : pct >= 60 ? 'bg-[#3FAF7A]' : 'bg-[#E5E5E5]'
  const fillBg = pct < 60 ? 'bg-[#999999]' : barColor

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

function NextActionsCard({
  actions,
  startIndex,
}: {
  actions: NextAction[]
  startIndex: number
}) {
  return (
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-5">
      <div className="flex items-center gap-1.5 mb-3">
        <Lightbulb className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[13px] font-semibold text-[#333333]">Next Best Actions</h2>
      </div>

      {actions.length > 0 ? (
        <div className="space-y-2.5">
          {actions.map((action, idx) => {
            const Icon = ACTION_ICONS[action.action_type] || Target
            const displayNum = startIndex + idx
            return (
              <div key={idx} className="p-3 bg-[#F4F4F4] rounded-xl">
                <div className="flex items-start gap-2.5">
                  <span className="flex items-center justify-center w-5 h-5 rounded-full bg-[#F0F0F0] text-[11px] font-medium text-[#666666] flex-shrink-0 mt-0.5">
                    {displayNum}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <Icon className="w-3.5 h-3.5 text-[#999999] flex-shrink-0" />
                      <p className="text-[12px] font-medium text-[#333333]">{action.title}</p>
                    </div>
                    <p className="text-[11px] text-[#666666] mt-0.5 ml-5 leading-relaxed">{action.description}</p>
                    {(action.suggested_stakeholder_role || action.suggested_artifact) && (
                      <div className="flex items-center gap-1.5 mt-1.5 ml-5">
                        {action.suggested_stakeholder_role && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-[#E8F5E9] text-[#25785A] rounded-full">
                            <Users className="w-2.5 h-2.5" />
                            {action.suggested_stakeholder_role}
                          </span>
                        )}
                        {action.suggested_artifact && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-white text-[#666666] rounded-full">
                            <FileText className="w-2.5 h-2.5" />
                            {action.suggested_artifact}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="text-center py-6">
          <Lightbulb className="w-8 h-8 text-[#E5E5E5] mx-auto mb-2" />
          <p className="text-[12px] text-[#999999]">
            No recommendations — your BRD is well-defined
          </p>
        </div>
      )}
    </div>
  )
}

function ActivityStrip({
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
    <div className="bg-white rounded-2xl border border-[#E5E5E5] shadow-md p-4">
      <div className="flex items-center gap-1.5 mb-3">
        <Activity className="w-4 h-4 text-[#3FAF7A]" />
        <h2 className="text-[13px] font-semibold text-[#333333]">Recent Activity</h2>
      </div>

      {items.length > 0 ? (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {items.map((tp) => (
            <div
              key={tp.id}
              className="flex-shrink-0 w-56 bg-[#F4F4F4] rounded-xl p-3"
            >
              <div className="flex items-center gap-1.5 mb-1.5">
                <Activity className="w-3 h-3 text-[#999999]" />
                <span className="text-[11px] font-medium text-[#333333] truncate">{tp.title}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className={`px-1.5 py-0.5 text-[10px] font-medium rounded-full ${statusBadgeClass(tp.status)}`}>
                  {tp.status}
                </span>
                <span className="text-[10px] text-[#999999]">
                  {formatRelativeTime(tp.completed_at || tp.created_at)}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-[12px] text-[#999999] py-2">
          No activity yet — process a signal to get started
        </p>
      )}
    </div>
  )
}

export default OverviewPanel
