/**
 * SWR-wrapped data hooks for cross-page caching and request deduplication.
 *
 * Benefits:
 * - getMyProfile() called once, cached across all pages (AppSidebar, Home, etc.)
 * - listProjects() shared between home and projects pages
 * - Automatic revalidation on focus/reconnect
 * - Stale-while-revalidate for instant navigation
 */

import useSWR, { type SWRConfiguration } from 'swr'
import {
  getMyProfile,
  listProjects,
  getBRDWorkspaceData,
  getNextActions,
  getUnifiedActions,
  getContextFrame,
  getIntelligenceBriefing,
  listOpenQuestions,
  getQuestionCounts,
  batchGetDashboardData,
  getHomeDashboard,
  listUpcomingMeetings,
  listMeetings,
  listTasks,
  listMyTasks,
  getTaskById,
  listTaskComments,
  getWorkspaceData,
  getMemoryVisualization,
  getIntelligenceOverview,
  getIntelligenceGraph,
  getIntelligenceEvolution,
  getSalesIntelligence,
  getUnifiedMemory,
} from '@/lib/api'
import type {
  NextAction,
  ProjectContextFrame,
  UnifiedActionsResult,
  Task,
  TaskWithProject,
  TaskStatsResponse,
  MyTasksResponse,
  TaskCommentListResponse,
  BatchDashboardData,
  HomeDashboardData,
  MemoryVisualizationResponse,
  UnifiedMemoryResponse,
} from '@/lib/api'
import type { Profile, ProjectDetailWithDashboard, Meeting } from '@/types/api'
import type {
  BRDWorkspaceData,
  CanvasData,
  IntelligenceBriefing,
  OpenQuestion,
  QuestionCounts,
  IntelOverviewResponse,
  IntelGraphResponse,
  IntelEvolutionResponse,
  IntelSalesResponse,
} from '@/types/workspace'

// --- SWR key constants (shared with realtime invalidation) ---
export const SWR_KEYS = {
  brd: (pid: string) => `brd:${pid}:evidence=true`,
  workspace: (pid: string) => `workspace:${pid}`,
  projects: (status: string) => `projects:${status}`,
  contextFrame: (pid: string) => `context-frame:${pid}`,
  briefing: (pid: string) => `briefing:${pid}`,
  memoryViz: (pid: string) => `memory-viz:${pid}`,
  intelOverview: (pid: string) => `intel-overview:${pid}`,
  intelGraph: (pid: string) => `intel-graph:${pid}`,
  intelEvolution: (pid: string, filter?: string, days?: number) =>
    `intel-evolution:${pid}:${filter || 'all'}:${days || 30}`,
  salesIntel: (pid: string) => `sales-intel:${pid}`,
  unifiedMemory: (pid: string) => `unified-memory:${pid}`,
} as const

// --- Cache TTL presets (in milliseconds) ---
const LONG_CACHE = 5 * 60 * 1000   // 5 min — stable data (profile)
const MED_CACHE = 60 * 1000         // 1 min — list data (projects)
const SHORT_CACHE = 15 * 1000       // 15s — workspace data

// --- Profile (globally shared, rarely changes) ---
export function useProfile(config?: SWRConfiguration<Profile>) {
  return useSWR<Profile>('profile:me', () => getMyProfile(), {
    dedupingInterval: LONG_CACHE,
    revalidateOnFocus: false,
    ...config,
  })
}

// --- Projects list ---
type ProjectsListResult = {
  projects: ProjectDetailWithDashboard[]
  total: number
  owner_profiles: Record<string, { first_name?: string; last_name?: string; photo_url?: string }>
}

export function useProjects(
  status = 'active',
  search?: string,
  config?: SWRConfiguration<ProjectsListResult>,
) {
  const key = search
    ? `projects:${status}:${search}`
    : SWR_KEYS.projects(status)
  return useSWR<ProjectsListResult>(key, () => listProjects(status, search), {
    dedupingInterval: MED_CACHE,
    ...config,
  })
}

// --- Upcoming meetings ---
export function useUpcomingMeetings(
  limit = 30,
  config?: SWRConfiguration<Meeting[]>,
) {
  return useSWR<Meeting[]>(
    `meetings:upcoming:${limit}`,
    () => listUpcomingMeetings(limit),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- All meetings (for meetings page) ---
export function useMeetings(
  projectId?: string,
  status?: string,
  config?: SWRConfiguration<Meeting[]>,
) {
  const key = `meetings:all:${projectId || 'all'}:${status || 'all'}`
  return useSWR<Meeting[]>(
    key,
    () => listMeetings(projectId, status),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Batch dashboard data (task stats + next actions + portal sync + tasks) ---
export function useBatchDashboardData(
  projectIds: string[] | undefined,
  opts?: { includePortalSync?: boolean; includePendingTasks?: boolean; pendingTasksLimit?: number },
  config?: SWRConfiguration<BatchDashboardData>,
) {
  // Stable key: sort IDs so order doesn't matter
  const sortedIds = projectIds ? [...projectIds].sort() : null
  const ps = opts?.includePortalSync ? ':ps' : ''
  const pt = opts?.includePendingTasks ? ':pt' : ''
  const key = sortedIds && sortedIds.length > 0
    ? `batch-dashboard:${sortedIds.join(',')}${ps}${pt}`
    : null

  return useSWR<BatchDashboardData>(
    key,
    () => batchGetDashboardData(sortedIds!, opts),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Home dashboard (single-call, no waterfall) ---
export function useHomeDashboard(
  status = 'active',
  config?: SWRConfiguration<HomeDashboardData>,
) {
  return useSWR<HomeDashboardData>(
    `home-dashboard:${status}`,
    () => getHomeDashboard(status),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: true,
      ...config,
    },
  )
}

// --- Cross-project tasks (for home dashboard) ---
export function useCrossProjectTasks(
  projectIds: string[] | undefined,
  limit = 5,
  config?: SWRConfiguration<Task[]>,
) {
  const sortedIds = projectIds ? [...projectIds].sort() : null
  const key = sortedIds && sortedIds.length > 0
    ? `cross-project-tasks:${sortedIds.join(',')}`
    : null

  return useSWR<Task[]>(
    key,
    async () => {
      const results = await Promise.all(
        sortedIds!.map((pid) =>
          listTasks(pid, {
            status: 'pending',
            limit: 10,
            sort_by: 'created_at',
            sort_order: 'desc',
          }).catch(() => ({ tasks: [], total: 0, has_more: false }))
        )
      )
      // Merge, filter out tasks older than 10 days, sort by latest first
      const tenDaysAgo = Date.now() - 10 * 24 * 60 * 60 * 1000
      const all = results.flatMap((r) => r.tasks)
        .filter((t) => new Date(t.created_at).getTime() >= tenDaysAgo)
      all.sort((a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
      return all.slice(0, limit)
    },
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- My tasks (cross-project, server-side aggregation) ---
export function useMyTasks(
  view: 'assigned_to_me' | 'created_by_me' | 'all' = 'all',
  config?: SWRConfiguration<MyTasksResponse>,
) {
  return useSWR<MyTasksResponse>(
    `my-tasks:${view}`,
    () => listMyTasks({ view, limit: 200 }),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Single task detail ---
export function useTaskDetail(
  taskId: string | undefined,
  config?: SWRConfiguration<TaskWithProject>,
) {
  return useSWR<TaskWithProject>(
    taskId ? `task-detail:${taskId}` : null,
    () => getTaskById(taskId!),
    {
      dedupingInterval: SHORT_CACHE,
      ...config,
    },
  )
}

// --- Task comments ---
export function useTaskComments(
  taskId: string | undefined,
  config?: SWRConfiguration<TaskCommentListResponse>,
) {
  return useSWR<TaskCommentListResponse>(
    taskId ? `task-comments:${taskId}` : null,
    () => listTaskComments(taskId!),
    {
      dedupingInterval: SHORT_CACHE,
      ...config,
    },
  )
}

// --- Canvas workspace data (per-project) ---
export function useWorkspaceData(
  projectId: string | undefined,
  config?: SWRConfiguration<CanvasData>,
) {
  return useSWR<CanvasData>(
    projectId ? SWR_KEYS.workspace(projectId) : null,
    () => getWorkspaceData(projectId!),
    {
      dedupingInterval: SHORT_CACHE,
      ...config,
    },
  )
}

// --- BRD workspace data (per-project) ---
// Uses MED_CACHE: data only changes on entity mutations (signals, features, etc.)
// The realtime hook (useRealtimeBRD) handles instant invalidation after mutations.
export function useBRDData(
  projectId: string | undefined,
  includeEvidence = true,
  config?: SWRConfiguration<BRDWorkspaceData>,
) {
  const key = projectId
    ? (includeEvidence ? SWR_KEYS.brd(projectId) : `brd:${projectId}:evidence=false`)
    : null
  return useSWR<BRDWorkspaceData>(
    key,
    () => getBRDWorkspaceData(projectId!, includeEvidence),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Next actions (per-project) ---
export function useNextActions(
  projectId: string | undefined,
  config?: SWRConfiguration<{ actions: NextAction[] }>,
) {
  return useSWR<{ actions: NextAction[] }>(
    projectId ? `next-actions:${projectId}` : null,
    () => getNextActions(projectId!),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Context frame (v3 — action count for BrainBubble badge) ---
// Backend uses fingerprint-based caching: only calls Haiku LLM when entity data
// actually changes. Safe to cache longer on the frontend side.
export function useContextFrame(
  projectId: string | undefined,
  config?: SWRConfiguration<ProjectContextFrame>,
) {
  return useSWR<ProjectContextFrame>(
    projectId ? SWR_KEYS.contextFrame(projectId) : null,
    () => getContextFrame(projectId!, 5),
    {
      dedupingInterval: LONG_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Unified actions (per-project, enriched with phase/memory/questions) ---
export function useUnifiedActions(
  projectId: string | undefined,
  config?: SWRConfiguration<UnifiedActionsResult>,
) {
  return useSWR<UnifiedActionsResult>(
    projectId ? `unified-actions:${projectId}` : null,
    () => getUnifiedActions(projectId!),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Open questions (per-project) ---
export function useOpenQuestions(
  projectId: string | undefined,
  status?: string,
  config?: SWRConfiguration<OpenQuestion[]>,
) {
  const key = projectId
    ? `open-questions:${projectId}:${status || 'all'}`
    : null
  return useSWR<OpenQuestion[]>(
    key,
    () => listOpenQuestions(projectId!, { status }),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Question counts (per-project) ---
export function useQuestionCounts(
  projectId: string | undefined,
  config?: SWRConfiguration<QuestionCounts>,
) {
  return useSWR<QuestionCounts>(
    projectId ? `question-counts:${projectId}` : null,
    () => getQuestionCounts(projectId!),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Intelligence briefing (per-project, per-user temporal diff) ---
export function useIntelligenceBriefing(
  projectId: string | undefined,
  config?: SWRConfiguration<IntelligenceBriefing>,
) {
  return useSWR<IntelligenceBriefing>(
    projectId ? SWR_KEYS.briefing(projectId) : null,
    () => getIntelligenceBriefing(projectId!, 5),
    {
      dedupingInterval: SHORT_CACHE,
      refreshInterval: 30_000,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Memory visualization (per-project) ---
export function useMemoryVisualization(
  projectId: string | undefined,
  config?: SWRConfiguration<MemoryVisualizationResponse>,
) {
  return useSWR<MemoryVisualizationResponse>(
    projectId ? SWR_KEYS.memoryViz(projectId) : null,
    () => getMemoryVisualization(projectId!),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Intelligence overview (per-project, expensive call) ---
export function useIntelOverview(
  projectId: string | undefined,
  config?: SWRConfiguration<IntelOverviewResponse>,
) {
  return useSWR<IntelOverviewResponse>(
    projectId ? SWR_KEYS.intelOverview(projectId) : null,
    () => getIntelligenceOverview(projectId!),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Intelligence graph (per-project) ---
export function useIntelGraph(
  projectId: string | undefined,
  config?: SWRConfiguration<IntelGraphResponse>,
) {
  return useSWR<IntelGraphResponse>(
    projectId ? SWR_KEYS.intelGraph(projectId) : null,
    () => getIntelligenceGraph(projectId!),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Intelligence evolution (per-project, parameterized) ---
export function useIntelEvolution(
  projectId: string | undefined,
  params?: { event_type?: string; days?: number; limit?: number },
  config?: SWRConfiguration<IntelEvolutionResponse>,
) {
  return useSWR<IntelEvolutionResponse>(
    projectId
      ? SWR_KEYS.intelEvolution(projectId, params?.event_type, params?.days)
      : null,
    () => getIntelligenceEvolution(projectId!, params),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Sales intelligence (per-project, rarely changes) ---
export function useSalesIntel(
  projectId: string | undefined,
  config?: SWRConfiguration<IntelSalesResponse>,
) {
  return useSWR<IntelSalesResponse>(
    projectId ? SWR_KEYS.salesIntel(projectId) : null,
    () => getSalesIntelligence(projectId!),
    {
      dedupingInterval: LONG_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}

// --- Unified memory (per-project, LLM-synthesized, expensive) ---
export function useUnifiedMemory(
  projectId: string | undefined,
  config?: SWRConfiguration<UnifiedMemoryResponse>,
) {
  return useSWR<UnifiedMemoryResponse>(
    projectId ? SWR_KEYS.unifiedMemory(projectId) : null,
    () => getUnifiedMemory(projectId!),
    {
      dedupingInterval: LONG_CACHE,
      revalidateOnFocus: false,
      ...config,
    },
  )
}
