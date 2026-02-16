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
  batchGetDashboardData,
  listUpcomingMeetings,
  getWorkspaceData,
} from '@/lib/api'
import type {
  NextAction,
  TaskStatsResponse,
  BatchDashboardData,
} from '@/lib/api'
import type { Profile, ProjectDetailWithDashboard, Meeting } from '@/types/api'
import type { BRDWorkspaceData, CanvasData } from '@/types/workspace'

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
    : `projects:${status}`
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

// --- Batch dashboard data (task stats + next actions for multiple projects) ---
export function useBatchDashboardData(
  projectIds: string[] | undefined,
  config?: SWRConfiguration<BatchDashboardData>,
) {
  // Stable key: sort IDs so order doesn't matter
  const sortedIds = projectIds ? [...projectIds].sort() : null
  const key = sortedIds && sortedIds.length > 0
    ? `batch-dashboard:${sortedIds.join(',')}`
    : null

  return useSWR<BatchDashboardData>(
    key,
    () => batchGetDashboardData(sortedIds!),
    {
      dedupingInterval: MED_CACHE,
      revalidateOnFocus: false,
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
    projectId ? `workspace:${projectId}` : null,
    () => getWorkspaceData(projectId!),
    {
      dedupingInterval: SHORT_CACHE,
      ...config,
    },
  )
}

// --- BRD workspace data (per-project) ---
export function useBRDData(
  projectId: string | undefined,
  includeEvidence = false,
  config?: SWRConfiguration<BRDWorkspaceData>,
) {
  const key = projectId
    ? `brd:${projectId}:evidence=${includeEvidence}`
    : null
  return useSWR<BRDWorkspaceData>(
    key,
    () => getBRDWorkspaceData(projectId!, includeEvidence),
    {
      dedupingInterval: SHORT_CACHE,
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
