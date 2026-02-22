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

  // Next Best Actions — now handled by BrainPanel (separate API call)
  // Legacy: keep for pendingAction backward compat from OverviewPanel
  const nextActions: NextAction[] = data?.next_actions ?? initialNextActions ?? []

  // Open Questions
  const [openQuestions, setOpenQuestions] = useState<OpenQuestion[]>([])
  const [questionsLoading, setQuestionsLoading] = useState(true)

  const loadOpenQuestions = useCallback(async () => {
    try {
      setQuestionsLoading(true)
      const result = await listOpenQuestions(projectId, { status: 'open', limit: 20 })
      setOpenQuestions(result)
    } catch (err) {
      console.error('Failed to load open questions:', err)
    } finally {
      setQuestionsLoading(false)
    }
  }, [projectId])

  // Confirmation Clusters
  const [clusters, setClusters] = useState<ConfirmationCluster[]>([])

  const loadClusters = useCallback(async () => {
    try {
      const result = await getConfirmationClusters(projectId)
      setClusters(result.clusters)
    } catch {
      // Silent — clusters are supplementary
    }
  }, [projectId])

  const loadHealth = useCallback(async () => {
    try {
      setHealthLoading(true)
      const result = await getBRDHealth(projectId)
      setHealth(result)
    } catch (err) {
      console.error('Failed to load BRD health:', err)
    } finally {
      setHealthLoading(false)
    }
  }, [projectId])

  const handleRefreshHealth = useCallback(async () => {
    setIsRefreshingHealth(true)
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
