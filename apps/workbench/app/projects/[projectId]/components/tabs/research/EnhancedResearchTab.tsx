/**
 * Enhanced Research Tab Component
 *
 * Advanced research browsing with semantic search, evidence linking, and gap analysis
 *
 * Features:
 * - Semantic search across all research chunks
 * - Evidence linking to features/PRD/VP/personas
 * - Gap analysis showing entities without evidence
 * - Smart filtering and sorting
 */

'use client'

import { useState, useEffect } from 'react'
import { Search, AlertTriangle, Link2, Filter, TrendingUp, FileText, Star, Zap, Users } from 'lucide-react'

interface EnhancedResearchTabProps {
  projectId: string
}

interface ResearchChunk {
  id: string
  content: string
  chunk_type: string
  source_name?: string
  created_at: string
  evidence_links?: number
}

interface EvidenceGap {
  entity_type: string
  entity_id: string
  entity_name: string
  has_evidence: boolean
}

interface ResearchSource {
  id: string
  source_type: string
  source_url?: string
  source_name: string
  created_at: string
  chunk_count?: number
  metadata?: any
}

export function EnhancedResearchTab({ projectId }: EnhancedResearchTabProps) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<ResearchChunk[]>([])
  const [recentChunks, setRecentChunks] = useState<ResearchChunk[]>([])
  const [evidenceGaps, setEvidenceGaps] = useState<EvidenceGap[]>([])
  const [sources, setSources] = useState<ResearchSource[]>([])
  const [loading, setLoading] = useState(false)
  const [searchLoading, setSearchLoading] = useState(false)
  const [activeView, setActiveView] = useState<'browse' | 'search' | 'gaps' | 'sources'>('browse')

  // Evidence stats
  const [evidenceStats, setEvidenceStats] = useState({
    total_chunks: 0,
    linked_chunks: 0,
    features_with_evidence: 0,
    total_features: 0,
  })

  useEffect(() => {
    loadResearchData()
  }, [projectId])

  const loadResearchData = async () => {
    try {
      setLoading(true)
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || ''

      // Load recent chunks
      const chunksRes = await fetch(`${apiBase}/v1/projects/${projectId}/research/chunks?limit=20`)
      if (chunksRes.ok) {
        const data = await chunksRes.json()
        setRecentChunks(data.chunks || [])
      }

      // Load evidence stats
      const statsRes = await fetch(`${apiBase}/v1/projects/${projectId}/research/evidence-stats`)
      if (statsRes.ok) {
        const data = await statsRes.json()
        setEvidenceStats(data)
      }

      // Load evidence gaps
      const gapsRes = await fetch(`${apiBase}/v1/projects/${projectId}/research/gaps`)
      if (gapsRes.ok) {
        const data = await gapsRes.json()
        setEvidenceGaps(data.gaps || [])
      }

      // Load sources
      const sourcesRes = await fetch(`${apiBase}/v1/projects/${projectId}/research/sources`)
      if (sourcesRes.ok) {
        const data = await sourcesRes.json()
        setSources(data.sources || [])
      }
    } catch (error) {
      console.error('Failed to load research data:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSemanticSearch = async () => {
    if (!searchQuery.trim()) return

    try {
      setSearchLoading(true)
      const apiBase = process.env.NEXT_PUBLIC_API_BASE || ''

      const response = await fetch(`${apiBase}/v1/chat/tools`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          tool_name: 'semantic_search_research',
          tool_input: {
            query: searchQuery,
            limit: 20,
          },
        }),
      })

      if (response.ok) {
        const data = await response.json()
        setSearchResults(data.results || [])
        setActiveView('search')
      }
    } catch (error) {
      console.error('Search failed:', error)
    } finally {
      setSearchLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSemanticSearch()
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto mb-4"></div>
          <p className="text-ui-supportText">Loading research...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto p-6 space-y-6">
      {/* Header with search */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-ui-headingDark">Research & Evidence</h1>
            <p className="text-sm text-ui-supportText mt-1">
              Search research, link evidence, and identify gaps
            </p>
          </div>
        </div>

        {/* Semantic Search Bar */}
        <div className="flex gap-2 mb-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-ui-supportText" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Semantic search across all research (e.g., 'competitor pricing strategies')..."
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary focus:border-transparent"
            />
          </div>
          <button
            onClick={handleSemanticSearch}
            disabled={searchLoading || !searchQuery.trim()}
            className="px-6 py-3 bg-brand-primary text-white rounded-lg hover:bg-brand-primaryHover disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {searchLoading ? 'Searching...' : 'Search'}
          </button>
        </div>

        {/* Evidence Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Research Chunks"
            value={evidenceStats.total_chunks}
            subtext={`${evidenceStats.linked_chunks} linked`}
          />
          <StatCard
            label="Evidence Coverage"
            value={`${Math.round((evidenceStats.features_with_evidence / evidenceStats.total_features) * 100)}%`}
            subtext={`${evidenceStats.features_with_evidence}/${evidenceStats.total_features} features`}
          />
          <StatCard
            label="Evidence Gaps"
            value={evidenceGaps.length}
            alert={evidenceGaps.length > 0}
            subtext="entities need evidence"
          />
          <StatCard
            label="Recent Activity"
            value={recentChunks.length}
            subtext="chunks this week"
          />
        </div>
      </div>

      {/* View Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        <ViewTab
          label="Browse Research"
          active={activeView === 'browse'}
          count={recentChunks.length}
          onClick={() => setActiveView('browse')}
        />
        <ViewTab
          label="Search Results"
          active={activeView === 'search'}
          count={searchResults.length}
          onClick={() => setActiveView('search')}
        />
        <ViewTab
          label="Sources"
          active={activeView === 'sources'}
          count={sources.length}
          onClick={() => setActiveView('sources')}
        />
        <ViewTab
          label="Evidence Gaps"
          active={activeView === 'gaps'}
          count={evidenceGaps.length}
          onClick={() => setActiveView('gaps')}
          alert={evidenceGaps.length > 0}
        />
      </div>

      {/* Content based on active view */}
      {activeView === 'browse' && (
        <BrowseView chunks={recentChunks} projectId={projectId} onRefresh={loadResearchData} />
      )}

      {activeView === 'search' && (
        <SearchResultsView
          chunks={searchResults}
          query={searchQuery}
          projectId={projectId}
          onRefresh={loadResearchData}
        />
      )}

      {activeView === 'sources' && (
        <SourcesView sources={sources} projectId={projectId} onRefresh={loadResearchData} />
      )}

      {activeView === 'gaps' && (
        <EvidenceGapsView gaps={evidenceGaps} projectId={projectId} onRefresh={loadResearchData} />
      )}
    </div>
  )
}

// Sub-components

function StatCard({
  label,
  value,
  subtext,
  alert = false,
}: {
  label: string
  value: number | string
  subtext?: string
  alert?: boolean
}) {
  return (
    <div className={`p-4 rounded-lg border ${alert ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'}`}>
      <div className={`text-2xl font-bold ${alert ? 'text-red-700' : 'text-ui-bodyText'}`}>{value}</div>
      <div className="text-xs text-ui-supportText font-medium mt-1">{label}</div>
      {subtext && <div className="text-xs text-ui-supportText mt-0.5">{subtext}</div>}
    </div>
  )
}

function ViewTab({
  label,
  active,
  count,
  onClick,
  alert = false,
}: {
  label: string
  active: boolean
  count?: number
  onClick: () => void
  alert?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
        active
          ? 'border-brand-primary text-brand-primary'
          : 'border-transparent text-ui-supportText hover:text-ui-bodyText'
      }`}
    >
      {label}
      {count !== undefined && count > 0 && (
        <span
          className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
            alert
              ? 'bg-red-100 text-red-700'
              : active
              ? 'bg-brand-primary/10 text-brand-primary'
              : 'bg-gray-100 text-gray-600'
          }`}
        >
          {count}
        </span>
      )}
    </button>
  )
}

function BrowseView({
  chunks,
  projectId,
  onRefresh,
}: {
  chunks: ResearchChunk[]
  projectId: string
  onRefresh: () => void
}) {
  if (chunks.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-ui-bodyText mb-2">No Research Yet</h3>
        <p className="text-sm text-ui-supportText">
          Run a research agent query to populate this tab with findings
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {chunks.map((chunk) => (
        <ResearchChunkCard key={chunk.id} chunk={chunk} projectId={projectId} onRefresh={onRefresh} />
      ))}
    </div>
  )
}

function SearchResultsView({
  chunks,
  query,
  projectId,
  onRefresh,
}: {
  chunks: ResearchChunk[]
  query: string
  projectId: string
  onRefresh: () => void
}) {
  if (chunks.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-ui-bodyText mb-2">No Results Found</h3>
        <p className="text-sm text-ui-supportText">
          Try a different search query or run a research agent
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="text-sm text-ui-supportText">
        Found {chunks.length} results for <span className="font-semibold text-ui-bodyText">"{query}"</span>
      </div>
      <div className="space-y-3">
        {chunks.map((chunk) => (
          <ResearchChunkCard key={chunk.id} chunk={chunk} projectId={projectId} onRefresh={onRefresh} />
        ))}
      </div>
    </div>
  )
}

function EvidenceGapsView({
  gaps,
  projectId,
  onRefresh,
}: {
  gaps: EvidenceGap[]
  projectId: string
  onRefresh: () => void
}) {
  if (gaps.length === 0) {
    return (
      <div className="bg-green-50 rounded-lg border border-green-200 p-12 text-center">
        <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="h-6 w-6 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <h3 className="text-lg font-semibold text-green-900 mb-2">No Evidence Gaps!</h3>
        <p className="text-sm text-green-700">All your features, PRD sections, and VP steps have evidence</p>
      </div>
    )
  }

  // Group by entity type
  const gapsByType = gaps.reduce((acc, gap) => {
    if (!acc[gap.entity_type]) acc[gap.entity_type] = []
    acc[gap.entity_type].push(gap)
    return acc
  }, {} as Record<string, EvidenceGap[]>)

  return (
    <div className="space-y-4">
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-yellow-900 mb-1">
              {gaps.length} Entities Need Evidence
            </h3>
            <p className="text-sm text-yellow-800">
              These features, PRD sections, or VP steps lack research evidence. Link relevant research to strengthen your prototype foundation.
            </p>
          </div>
        </div>
      </div>

      {Object.entries(gapsByType).map(([entityType, entityGaps]) => (
        <div key={entityType} className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
          <div className="flex items-center gap-2 mb-4">
            {getEntityIcon(entityType)}
            <h3 className="font-semibold text-ui-bodyText capitalize">
              {entityType.replace('_', ' ')}s Without Evidence ({entityGaps.length})
            </h3>
          </div>
          <div className="space-y-2">
            {entityGaps.map((gap) => (
              <GapItem key={gap.entity_id} gap={gap} projectId={projectId} onRefresh={onRefresh} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function getEntityIcon(entityType: string) {
  switch (entityType) {
    case 'feature':
      return <Star className="h-5 w-5 text-yellow-600" />
    case 'prd_section':
      return <FileText className="h-5 w-5 text-blue-600" />
    case 'vp_step':
      return <Zap className="h-5 w-5 text-purple-600" />
    case 'persona':
      return <Users className="h-5 w-5 text-green-600" />
    default:
      return <AlertTriangle className="h-5 w-5 text-gray-600" />
  }
}

function GapItem({ gap, projectId, onRefresh }: { gap: EvidenceGap; projectId: string; onRefresh: () => void }) {
  const [finding, setFinding] = useState(false)

  const handleFindEvidence = async () => {
    setFinding(true)
    // Trigger semantic search for this entity
    // This would open a search with entity name as query
    // For now, just a placeholder
    setTimeout(() => {
      setFinding(false)
      onRefresh()
    }, 1000)
  }

  return (
    <div className="flex items-center justify-between p-3 border border-gray-200 rounded hover:border-brand-primary transition-colors">
      <div className="flex-1">
        <h4 className="font-medium text-ui-bodyText">{gap.entity_name}</h4>
        <p className="text-xs text-ui-supportText mt-0.5">No research evidence linked</p>
      </div>
      <button
        onClick={handleFindEvidence}
        disabled={finding}
        className="px-3 py-1.5 text-sm bg-brand-primary text-white rounded hover:bg-brand-primaryHover disabled:opacity-50 transition-colors flex items-center gap-2"
      >
        <Search className="h-4 w-4" />
        {finding ? 'Finding...' : 'Find Evidence'}
      </button>
    </div>
  )
}

function ResearchChunkCard({
  chunk,
  projectId,
  onRefresh,
}: {
  chunk: ResearchChunk
  projectId: string
  onRefresh: () => void
}) {
  const [linking, setLinking] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const handleLinkEvidence = () => {
    setLinking(true)
    // Show link modal or inline picker
    // For now, placeholder
    setTimeout(() => {
      setLinking(false)
      onRefresh()
    }, 500)
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:border-brand-primary transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
              {chunk.chunk_type}
            </span>
            {chunk.source_name && (
              <span className="text-xs text-ui-supportText">{chunk.source_name}</span>
            )}
            {chunk.evidence_links && chunk.evidence_links > 0 && (
              <span className="flex items-center gap-1 px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">
                <Link2 className="h-3 w-3" />
                {chunk.evidence_links} linked
              </span>
            )}
          </div>
          <p className="text-sm text-ui-bodyText line-clamp-3">
            {chunk.content}
          </p>
          {chunk.content.length > 200 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="text-xs text-brand-primary hover:underline mt-1"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 pt-3 border-t border-gray-100">
        <button
          onClick={handleLinkEvidence}
          disabled={linking}
          className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-ui-bodyText rounded transition-colors flex items-center gap-1.5"
        >
          <Link2 className="h-3 w-3" />
          {linking ? 'Linking...' : 'Link to Entity'}
        </button>
        <span className="text-xs text-ui-supportText">
          {new Date(chunk.created_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  )
}

function SourcesView({
  sources,
  projectId,
  onRefresh,
}: {
  sources: ResearchSource[]
  projectId: string
  onRefresh: () => void
}) {
  if (sources.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <h3 className="text-lg font-semibold text-ui-bodyText mb-2">No Sources Yet</h3>
        <p className="text-sm text-ui-supportText">
          Research sources will appear here as you add signals and run research agents
        </p>
      </div>
    )
  }

  // Group by source type
  const sourcesByType = sources.reduce((acc, source) => {
    if (!acc[source.source_type]) acc[source.source_type] = []
    acc[source.source_type].push(source)
    return acc
  }, {} as Record<string, ResearchSource[]>)

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center gap-3">
          <FileText className="h-5 w-5 text-blue-600" />
          <div>
            <h3 className="font-semibold text-blue-900">
              {sources.length} Research Sources
            </h3>
            <p className="text-sm text-blue-800 mt-1">
              {Object.keys(sourcesByType).length} different source types
            </p>
          </div>
        </div>
      </div>

      {/* Sources by Type */}
      {Object.entries(sourcesByType).map(([type, typeSources]) => (
        <div key={type} className="space-y-3">
          <h3 className="font-semibold text-ui-bodyText capitalize flex items-center gap-2">
            {getSourceTypeIcon(type)}
            {type.replace('_', ' ')} ({typeSources.length})
          </h3>
          <div className="space-y-3">
            {typeSources.map((source) => (
              <SourceCard key={source.id} source={source} projectId={projectId} onRefresh={onRefresh} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function getSourceTypeIcon(type: string) {
  switch (type.toLowerCase()) {
    case 'url':
    case 'web':
      return '🌐'
    case 'document':
    case 'pdf':
      return '📄'
    case 'interview':
      return '🎤'
    case 'survey':
      return '📊'
    case 'api':
      return '🔌'
    default:
      return '📁'
  }
}

function SourceCard({
  source,
  projectId,
  onRefresh,
}: {
  source: ResearchSource
  projectId: string
  onRefresh: () => void
}) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:border-brand-primary transition-colors">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">
              {source.source_type}
            </span>
            {source.chunk_count && source.chunk_count > 0 && (
              <span className="text-xs text-ui-supportText">
                {source.chunk_count} chunks
              </span>
            )}
          </div>

          <h4 className="font-medium text-ui-bodyText mb-1">{source.source_name}</h4>

          {source.source_url && (
            <a
              href={source.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-brand-primary hover:underline break-all"
            >
              {source.source_url}
            </a>
          )}

          {source.metadata && expanded && (
            <div className="mt-3 p-3 bg-gray-50 rounded border border-gray-200">
              <div className="text-xs text-ui-supportText font-medium mb-2">Metadata:</div>
              <pre className="text-xs text-ui-bodyText whitespace-pre-wrap">
                {JSON.stringify(source.metadata, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 pt-3 border-t border-gray-100">
        <span className="text-xs text-ui-supportText">
          Added {new Date(source.created_at).toLocaleDateString()}
        </span>
        {source.metadata && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-xs text-brand-primary hover:underline"
          >
            {expanded ? 'Hide metadata' : 'Show metadata'}
          </button>
        )}
      </div>
    </div>
  )
}
