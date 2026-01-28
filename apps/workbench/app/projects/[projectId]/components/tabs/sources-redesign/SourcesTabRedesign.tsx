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
  getProjectMemory,
  type DocumentSummaryItem,
  type SourceUsageItem,
  type EvidenceQualityResponse,
  type SourceSearchResponse,
  type ProjectMemory,
} from '@/lib/api'

interface SourcesTabRedesignProps {
  projectId: string
  onUploadClick: () => void
}

export function SourcesTabRedesign({ projectId, onUploadClick }: SourcesTabRedesignProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  // Get active sub-tab from URL, default to 'documents'
  const activeTab = (searchParams.get('sources_tab') as SourcesSubTab) || 'documents'

  // Data state
  const [documents, setDocuments] = useState<DocumentSummaryItem[]>([])
  const [sources, setSources] = useState<SourceUsageItem[]>([])
  const [evidenceQuality, setEvidenceQuality] = useState<EvidenceQualityResponse | null>(null)
  const [memoryContent, setMemoryContent] = useState<string | null>(null)

  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SourceSearchResponse | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  // Loading states
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true)
  const [isLoadingSources, setIsLoadingSources] = useState(true)
  const [isLoadingEvidence, setIsLoadingEvidence] = useState(true)
  const [isLoadingMemory, setIsLoadingMemory] = useState(true)

  // Tab change handler - updates URL
  const handleTabChange = useCallback((tab: SourcesSubTab) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('sources_tab', tab)
    router.push(`${pathname}?${params.toString()}`, { scroll: false })
  }, [pathname, router, searchParams])

  // Load documents
  useEffect(() => {
    const loadDocuments = async () => {
      setIsLoadingDocuments(true)
      try {
        const data = await getDocumentsSummary(projectId)
        setDocuments(data.documents)
      } catch (error) {
        console.error('Failed to load documents:', error)
      } finally {
        setIsLoadingDocuments(false)
      }
    }
    loadDocuments()
  }, [projectId])

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

  // Load memory and format as markdown
  useEffect(() => {
    const loadMemory = async () => {
      setIsLoadingMemory(true)
      try {
        const data = await getProjectMemory(projectId)
        const formattedMemory = formatMemoryAsMarkdown(data)
        setMemoryContent(formattedMemory)
      } catch (error) {
        console.error('Failed to load memory:', error)
      } finally {
        setIsLoadingMemory(false)
      }
    }
    loadMemory()
  }, [projectId])

  // Format ProjectMemory as markdown
  function formatMemoryAsMarkdown(memory: ProjectMemory): string | null {
    const sections: string[] = []

    if (memory.decisions.length > 0) {
      sections.push('## Key Decisions\n')
      memory.decisions.forEach((d, i) => {
        const date = new Date(d.created_at).toLocaleDateString()
        sections.push(`${i + 1}. **[${date}]** ${d.content}`)
        if (d.rationale) {
          sections.push(`   - *Rationale:* ${d.rationale}`)
        }
      })
      sections.push('')
    }

    if (memory.learnings.length > 0) {
      sections.push('## Learnings\n')
      memory.learnings.forEach((l) => {
        sections.push(`- ${l.content}`)
      })
      sections.push('')
    }

    if (memory.questions.length > 0) {
      sections.push('## Open Questions\n')
      memory.questions.forEach((q) => {
        const checkbox = q.resolved ? '[x]' : '[ ]'
        sections.push(`- ${checkbox} ${q.content}`)
      })
      sections.push('')
    }

    if (sections.length === 0) {
      return null
    }

    return sections.join('\n')
  }

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
  const counts = {
    documents: documents.length,
    signals: sources.filter(s => s.signal_type !== 'research').length,
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
          />
        )}

        {activeTab === 'signals' && (
          <SignalsTab
            signals={sources}
            isLoading={isLoadingSources}
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
            memoryContent={memoryContent}
            isLoading={isLoadingMemory}
          />
        )}
      </div>
    </div>
  )
}
