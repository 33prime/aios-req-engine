import { useState, useEffect, useCallback, useRef } from 'react'
import {
  getBRDWorkspaceData,
  getBRDHealth,
  processCascades,
  listOpenQuestions,
  getConfirmationClusters,
} from '@/lib/api'
import type { NextAction } from '@/lib/api'
import type { BRDWorkspaceData, BRDHealthData, OpenQuestion, ConfirmationCluster } from '@/types/workspace'

// In-component cache TTL for supplementary BRD data (health, questions, clusters).
// Avoids re-fetching on every tab switch — these only change after signal processing.
const CACHE_TTL = 60_000 // 60 seconds

interface CacheEntry<T> {
  data: T
  fetchedAt: number
}

function isCacheFresh<T>(cache: CacheEntry<T> | null): cache is CacheEntry<T> {
  return cache !== null && Date.now() - cache.fetchedAt < CACHE_TTL
}

export function useBRDDataLoading(
  projectId: string,
  initialData?: BRDWorkspaceData | null,
  initialNextActions?: NextAction[] | null,
  onActiveSectionChange?: (sectionId: string) => void,
) {
  const [data, setData] = useState<BRDWorkspaceData | null>(initialData ?? null)
  const [isLoading, setIsLoading] = useState(!initialData)
  const [error, setError] = useState<string | null>(null)

  // Sync from parent when SWR revalidates (e.g. triggered by Realtime)
  useEffect(() => {
    if (initialData) {
      setData(initialData)
    }
  }, [initialData])

  // Scroll tracking — report active BRD section via IntersectionObserver
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const container = scrollContainerRef.current
    if (!container || !onActiveSectionChange) return

    const sectionIds = [
      'brd-section-questions', 'brd-section-business-context', 'brd-section-personas',
      'brd-section-workflows', 'brd-section-solution-flow', 'brd-section-features',
      'brd-section-data-entities', 'brd-section-stakeholders', 'brd-section-constraints',
    ]
    const visibleRatios = new Map<string, number>()
    let debounceTimer: ReturnType<typeof setTimeout> | null = null

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          visibleRatios.set(entry.target.id, entry.intersectionRatio)
        }
        if (debounceTimer) clearTimeout(debounceTimer)
        debounceTimer = setTimeout(() => {
          let maxRatio = 0
          let maxId = ''
          for (const [id, ratio] of visibleRatios) {
            if (ratio > maxRatio) { maxRatio = ratio; maxId = id }
          }
          if (maxId && maxRatio > 0) {
            onActiveSectionChange(maxId.replace('brd-section-', ''))
          }
        }, 200)
      },
      { root: container, threshold: [0, 0.1, 0.3, 0.5, 0.7, 1.0] }
    )

    for (const id of sectionIds) {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    }

    return () => {
      observer.disconnect()
      if (debounceTimer) clearTimeout(debounceTimer)
    }
  }, [onActiveSectionChange, data]) // re-observe when data loads

  // Health data (lifted from HealthPanel for IntelligenceSection)
  const [health, setHealth] = useState<BRDHealthData | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [isRefreshingHealth, setIsRefreshingHealth] = useState(false)

  // In-component caches — survive tab switches without re-fetching
  const healthCacheRef = useRef<CacheEntry<BRDHealthData> | null>(null)
  const questionsCacheRef = useRef<CacheEntry<OpenQuestion[]> | null>(null)
  const clustersCacheRef = useRef<CacheEntry<ConfirmationCluster[]> | null>(null)

  // Next Best Actions — now handled by BrainPanel (separate API call)
  // Legacy: keep for pendingAction backward compat from OverviewPanel
  const nextActions: NextAction[] = data?.next_actions ?? initialNextActions ?? []

  // Open Questions
  const [openQuestions, setOpenQuestions] = useState<OpenQuestion[]>([])
  const [questionsLoading, setQuestionsLoading] = useState(true)

  const loadOpenQuestions = useCallback(async () => {
    if (isCacheFresh(questionsCacheRef.current)) {
      setOpenQuestions(questionsCacheRef.current.data)
      setQuestionsLoading(false)
      return
    }
    try {
      setQuestionsLoading(true)
      const result = await listOpenQuestions(projectId, { status: 'open', limit: 20 })
      setOpenQuestions(result)
      questionsCacheRef.current = { data: result, fetchedAt: Date.now() }
    } catch (err) {
      console.error('Failed to load open questions:', err)
    } finally {
      setQuestionsLoading(false)
    }
  }, [projectId])

  // Confirmation Clusters
  const [clusters, setClusters] = useState<ConfirmationCluster[]>([])

  const loadClusters = useCallback(async () => {
    if (isCacheFresh(clustersCacheRef.current)) {
      setClusters(clustersCacheRef.current.data)
      return
    }
    try {
      const result = await getConfirmationClusters(projectId)
      setClusters(result.clusters)
      clustersCacheRef.current = { data: result.clusters, fetchedAt: Date.now() }
    } catch {
      // Silent — clusters are supplementary
    }
  }, [projectId])

  const loadHealth = useCallback(async () => {
    if (isCacheFresh(healthCacheRef.current)) {
      setHealth(healthCacheRef.current.data)
      setHealthLoading(false)
      return
    }
    try {
      setHealthLoading(true)
      const result = await getBRDHealth(projectId)
      setHealth(result)
      healthCacheRef.current = { data: result, fetchedAt: Date.now() }
    } catch (err) {
      console.error('Failed to load BRD health:', err)
    } finally {
      setHealthLoading(false)
    }
  }, [projectId])

  const handleRefreshHealth = useCallback(async () => {
    setIsRefreshingHealth(true)
    // Invalidate cache — user explicitly requested a refresh
    healthCacheRef.current = null
    try {
      await processCascades(projectId)
      await loadHealth()
    } catch (err) {
      console.error('Failed to process cascades:', err)
    } finally {
      setIsRefreshingHealth(false)
    }
  }, [projectId, loadHealth])

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)
      const result = await getBRDWorkspaceData(projectId)
      setData(result)
    } catch (err) {
      console.error('Failed to load BRD data:', err)
      setError('Failed to load BRD data')
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    // Skip BRD data fetch if parent already provided it (next_actions are included in BRD response)
    if (!initialData) loadData()
    // Health is always loaded fresh (lightweight, not duplicated by parent)
    loadHealth()
    loadOpenQuestions()
    loadClusters()
  }, [loadData, loadHealth, loadOpenQuestions, loadClusters, initialData])

  return {
    data,
    setData,
    isLoading,
    error,
    loadData,
    health,
    healthLoading,
    isRefreshingHealth,
    handleRefreshHealth,
    openQuestions,
    questionsLoading,
    loadOpenQuestions,
    clusters,
    loadClusters,
    nextActions,
    scrollContainerRef,
  }
}
