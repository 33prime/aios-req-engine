/**
 * SourcesTabRedesign Component
 *
 * Main container for the redesigned Sources tab.
 * Manages state, data fetching, and tab routing.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useRouter, usePathname } from 'next/navigation'
import { SourcesHeader } from './SourcesHeader'
import { SourcesTabBar, type SourcesSubTab } from './SourcesTabBar'
import { DocumentsTab } from './documents/DocumentsTab'
import { SignalsTab } from './signals/SignalsTab'
import { ResearchTab } from './research/ResearchTab'
import { IntelligenceTab } from './intelligence/IntelligenceTab'
import { MemoryTab } from './memory/MemoryTab'
import {
  getDocumentsSummary,
  getSourceUsage,
  getEvidenceQuality,
  searchSources,
  getUnifiedMemory,
  refreshUnifiedMemory,
  type DocumentSummaryItem,
  type SourceUsageItem,
  type EvidenceQualityResponse,
  type SourceSearchResponse,
  type UnifiedMemoryResponse,
} from '@/lib/api'

interface SourcesTabRedesignProps {
  projectId: string
  onUploadClick: () => void
}

export function SourcesTabRedesign({ projectId, onUploadClick }: SourcesTabRedesignProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  // Get active sub-tab from URL, default to 'signals'
  const activeTab = (searchParams.get('sources_tab') as SourcesSubTab) || 'signals'

  // Data state
  const [documents, setDocuments] = useState<DocumentSummaryItem[]>([])
  const [sources, setSources] = useState<SourceUsageItem[]>([])
  const [evidenceQuality, setEvidenceQuality] = useState<EvidenceQualityResponse | null>(null)
  const [unifiedMemory, setUnifiedMemory] = useState<UnifiedMemoryResponse | null>(null)

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SourceSearchResponse | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  // Loading states
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true)
  const [isLoadingSources, setIsLoadingSources] = useState(true)
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(true)
  const [isLoadingMemory, setIsLoadingMemory] = useState(true)
  const [isRefreshingMemory, setIsRefreshingMemory] = useState(false)

  // Tab change handler - updates URL
  const handleTabChange = useCallback((tab: SourcesSubTab) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('sources_tab', tab)
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
  }, [pathname, router, searchParams])

  // Load documents function (extracted for reuse)
  const loadDocuments = useCallback(async () => {
    setIsLoadingDocuments(true)
    try {
      const data = await getDocumentsSummary(projectId)
      setDocuments(data.documents)
    } catch (error) {
      console.error('Failed to load documents:', error)
    } finally {
      setIsLoadingDocuments(false)
    }
  }, [projectId])

  // Load documents on mount
  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  // Load sources (signals)
  useEffect(() => {
    const loadSources = async () => {
      setIsLoadingSources(true)
      try {
        const data = await getSourceUsage(projectId)
        setSources(data.sources)
      } catch (error) {
        console.error('Failed to load sources:', error)
      } finally {
        setIsLoadingSources(false)
      }
    }
    loadSources()
  }, [projectId])

  // Load evidence quality
  useEffect(() => {
    const loadEvidence = async () => {
      setIsLoadingEvidence(true)
      try {
        const data = await getEvidenceQuality(projectId)
        setEvidenceQuality(data)
      } catch (error) {
        console.error('Failed to load evidence quality:', error)
      } finally {
        setIsLoadingEvidence(false)
      }
    }
    loadEvidence()
  }, [projectId])

  // Load unified memory (extracted for reuse)
  const loadMemory = useCallback(async () => {
    setIsLoadingMemory(true)
    try {
      const data = await getUnifiedMemory(projectId)
      setUnifiedMemory(data)
    } catch (error) {
      console.error('Failed to load unified memory:', error)
      // On error, set to null to show empty state
      setUnifiedMemory(null)
    } finally {
      setIsLoadingMemory(false)
    }
  }, [projectId])

  // Load memory on mount
  useEffect(() => {
    loadMemory()
  }, [loadMemory])

  // Refresh memory handler (force refresh)
  const handleRefreshMemory = useCallback(async () => {
    setIsRefreshingMemory(true)
    try {
      const data = await refreshUnifiedMemory(projectId)
      setUnifiedMemory(data)
    } catch (error) {
      console.error('Failed to refresh memory:', error)
    } finally {
      setIsRefreshingMemory(false)
    }
  }, [projectId])

  // Combined refresh after document processing (refreshes docs + memory)
  const refreshAfterDocumentProcessing = useCallback(async () => {
    await loadDocuments()
    // Also refresh memory since document processing creates memory entries
    await loadMemory()
  }, [loadDocuments, loadMemory])

  // Search handler
  const handleSearch = async () => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults(null)
      return
    }

    setIsSearching(true)
    try {
      const results = await searchSources(projectId, searchQuery)
      setSearchResults(results)
      // TODO: Show search results overlay
      console.log('Search results:', results)
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setIsSearching(false)
    }
  }

  // Navigate to Intelligence tab when clicking evidence badge
  const handleEvidenceClick = () => {
    handleTabChange('intelligence')
  }

  // Calculate tab counts
  // Signals tab now shows ALL sources (signals + research + documents) as a unified timeline
  const counts = {
    documents: documents.length,
    signals: sources.length + documents.length,  // Total of all sources
    research: sources.filter(s => s.signal_type === 'research').length,
    intelligence: undefined, // Don't show count
    memory: undefined, // Don't show count
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <SourcesHeader
        evidencePercentage={evidenceQuality?.strong_evidence_percentage || 0}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSearchSubmit={handleSearch}
        onUploadClick={onUploadClick}
        onEvidenceClick={handleEvidenceClick}
      />

      {/* Tab bar */}
      <SourcesTabBar
        activeTab={activeTab}
        onTabChange={handleTabChange}
        counts={counts}
      />

      {/* Tab content */}
      <div className="min-h-[400px]">
        {activeTab === 'documents' && (
          <DocumentsTab
            documents={documents}
            isLoading={isLoadingDocuments}
            onUploadClick={onUploadClick}
            onRefresh={refreshAfterDocumentProcessing}
          />
        )}

        {activeTab === 'signals' && (
          <SignalsTab
            signals={sources}
            documents={documents}
            isLoading={isLoadingSources || isLoadingDocuments}
            onNavigateToTab={handleTabChange}
          />
        )}

        {activeTab === 'research' && (
          <ResearchTab
            signals={sources}
            isLoading={isLoadingSources}
          />
        )}

        {activeTab === 'intelligence' && (
          <IntelligenceTab
            evidenceQuality={evidenceQuality}
            isLoading={isLoadingEvidence}
          />
        )}

        {activeTab === 'memory' && (
          <MemoryTab
            unifiedMemory={unifiedMemory}
            isLoading={isLoadingMemory}
            isRefreshing={isRefreshingMemory}
            onRefresh={handleRefreshMemory}
          />
        )}
      </div>
    </div>
  )
}
