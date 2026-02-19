/**
 * Supabase Realtime hooks for SWR cache invalidation.
 *
 * These hooks subscribe to Postgres Changes on entity tables and trigger
 * SWR global `mutate()` to refetch shaped data from FastAPI. Realtime is
 * purely a push notification layer — all data still flows through the API.
 */

import { useEffect, useRef, useMemo, useCallback } from 'react'
import { mutate } from 'swr'
import { supabase } from '@/lib/supabase'
import { SWR_KEYS } from '@/lib/hooks/use-api'

interface RealtimeTableConfig {
  table: string
  filter?: string
}

// ---------------------------------------------------------------------------
// Generic hook: subscribe to Postgres Changes, debounce, then invalidate SWR
// ---------------------------------------------------------------------------

export function useRealtimeInvalidation(
  channelName: string,
  tables: RealtimeTableConfig[],
  onInvalidate: () => void,
  enabled = true,
) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  // Use a ref for the callback so channel subscriptions don't re-create on every render
  const invalidateRef = useRef(onInvalidate)
  invalidateRef.current = onInvalidate

  // Stable serialization of tables config for effect dependency
  const tablesKey = useMemo(
    () => tables.map((t) => `${t.table}:${t.filter ?? ''}`).join('|'),
    [tables],
  )

  useEffect(() => {
    if (!enabled || !supabase) return
    const client = supabase

    const debouncedInvalidate = () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      timerRef.current = setTimeout(() => {
        invalidateRef.current()
      }, 500)
    }

    const channel = client.channel(channelName)

    for (const { table, filter } of tables) {
      channel.on(
        'postgres_changes' as any,
        {
          event: '*',
          schema: 'public',
          table,
          ...(filter ? { filter } : {}),
        },
        debouncedInvalidate,
      )
    }

    channel.subscribe()

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
      client.removeChannel(channel)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [channelName, enabled, tablesKey])
}

// ---------------------------------------------------------------------------
// BRD page: invalidate BRD + workspace SWR caches on any entity change
// ---------------------------------------------------------------------------

const BRD_TABLE_NAMES = [
  'features',
  'personas',
  'vp_steps',
  'workflows',
  'business_drivers',
  'constraints',
  'data_entities',
  'stakeholders',
  'competitor_references',
  'pending_items',
  'company_info',
] as const

export function useRealtimeBRD(projectId: string | undefined) {
  const tables = useMemo<RealtimeTableConfig[]>(
    () =>
      projectId
        ? BRD_TABLE_NAMES.map((table) => ({
            table,
            filter: `project_id=eq.${projectId}`,
          }))
        : [],
    [projectId],
  )

  const onInvalidate = useCallback(() => {
    if (!projectId) return
    mutate(SWR_KEYS.brd(projectId))
    mutate(SWR_KEYS.workspace(projectId))
  }, [projectId])

  useRealtimeInvalidation(`brd:${projectId}`, tables, onInvalidate, !!projectId)
}

// ---------------------------------------------------------------------------
// Dashboard: invalidate project list caches on any project change
// ---------------------------------------------------------------------------

const DASHBOARD_TABLES: RealtimeTableConfig[] = [{ table: 'projects' }]

const invalidateDashboard = () => {
  mutate(
    (key) => typeof key === 'string' && key.startsWith('projects:'),
    undefined,
    { revalidate: true },
  )
}

export function useRealtimeDashboard() {
  useRealtimeInvalidation('dashboard', DASHBOARD_TABLES, invalidateDashboard, true)
}
