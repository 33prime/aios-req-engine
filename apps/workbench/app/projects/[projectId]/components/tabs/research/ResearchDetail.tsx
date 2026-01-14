/**
 * ResearchDetail Component
 *
 * Right column: Displays query details and findings browser
 */

'use client'

import { useState, useEffect } from 'react'
import { Card, CardHeader, EmptyState } from '@/components/ui'
import { Search, ExternalLink } from 'lucide-react'
import { getSignalChunks } from '@/lib/api'
import type { Job, SignalChunk } from '@/types/api'

interface ResearchDetailProps {
  job: Job | null
  onRefresh: () => void
}

export function ResearchDetail({ job, onRefresh }: ResearchDetailProps) {
  const [findings, setFindings] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    if (job?.output?.signal_id) {
      loadFindings(job.output.signal_id)
    } else {
      setFindings([])
    }
  }, [job])

  const loadFindings = async (signalId: string) => {
    try {
      setLoading(true)
      const response = await getSignalChunks(signalId)
      setFindings(response.chunks || [])
    } catch (error) {
      console.error('Failed to load findings:', error)
      setFindings([])
    } finally {
      setLoading(false)
    }
  }

  if (!job) {
    return (
      <EmptyState
        icon={<Search className="h-16 w-16" />}
        title="No Research Selected"
        description="Select a research query from the list to view findings."
      />
    )
  }

  const filteredFindings = findings.filter((finding) => {
    const matchesCategory = categoryFilter === 'all' || finding.metadata?.category === categoryFilter
    const matchesSearch = !searchQuery ||
      finding.content.toLowerCase().includes(searchQuery.toLowerCase())
    return matchesCategory && matchesSearch
  })

  const categories = [
    { id: 'all', label: 'All Findings', count: findings.length },
    { id: 'competitive_features', label: 'Competitive Features', count: findings.filter(f => f.metadata?.category === 'competitive_features').length },
    { id: 'market_insights', label: 'Market Insights', count: findings.filter(f => f.metadata?.category === 'market_insights').length },
    { id: 'pain_points', label: 'Pain Points', count: findings.filter(f => f.metadata?.category === 'pain_points').length },
    { id: 'technical_considerations', label: 'Technical', count: findings.filter(f => f.metadata?.category === 'technical_considerations').length },
  ]

  return (
    <div className="space-y-6">
      {/* Query metadata */}
      <Card>
        <CardHeader
          title={job.input?.seed_context?.client_name || 'Research Query'}
          subtitle={`Executed ${new Date(job.created_at).toLocaleString()}`}
        />

        <div className="mt-4 space-y-3">
          {job.input?.seed_context?.industry && (
            <div>
              <span className="text-xs font-medium text-ui-supportText">Industry:</span>
              <p className="text-sm text-ui-bodyText">{job.input.seed_context.industry}</p>
            </div>
          )}

          {job.input?.seed_context?.competitors?.length > 0 && (
            <div>
              <span className="text-xs font-medium text-ui-supportText">Competitors:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {job.input.seed_context.competitors.map((comp: string, i: number) => (
                  <span key={i} className="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
                    {comp}
                  </span>
                ))}
              </div>
            </div>
          )}

          {job.status === 'completed' && job.output && (
            <div className="flex items-center gap-2 pt-2 border-t border-ui-cardBorder">
              <span className="text-xs px-2 py-1 bg-green-50 text-green-700 rounded font-medium">
                ✓ {Object.values(job.output?.findings_summary || {}).reduce((sum: number, val: any) => sum + (val || 0), 0)} findings
              </span>
              <span className="text-xs text-ui-supportText">
                from {job.output?.queries_executed || 0} queries
              </span>
            </div>
          )}
        </div>
      </Card>

      {/* Findings browser */}
      <Card>
        <CardHeader title="Research Findings" />

        {/* Category filter */}
        <div className="flex gap-2 mb-4 overflow-x-auto">
          {categories.map((cat) => (
            <button
              key={cat.id}
              onClick={() => setCategoryFilter(cat.id)}
              className={`px-3 py-1.5 text-xs rounded-lg whitespace-nowrap transition-colors ${
                categoryFilter === cat.id
                  ? 'bg-brand-primary text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {cat.label} ({cat.count})
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="mb-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search findings..."
            className="w-full px-3 py-2 border border-ui-cardBorder rounded-lg text-sm"
          />
        </div>

        {/* Findings list */}
        {loading ? (
          <div className="text-center py-8 text-ui-supportText">Loading findings...</div>
        ) : filteredFindings.length === 0 ? (
          <div className="text-center py-8 bg-ui-background rounded-lg border border-ui-cardBorder">
            <p className="text-sm text-ui-bodyText">No findings match your filters</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredFindings.map((finding) => (
              <div key={finding.chunk_index} className="bg-ui-background border border-ui-cardBorder rounded-lg p-3">
                <p className="text-sm text-ui-bodyText mb-2">{finding.content}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                    {finding.metadata?.category?.replace(/_/g, ' ') || 'General'}
                  </span>
                  {finding.metadata?.source_url && (
                    <a
                      href={finding.metadata.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-brand-primary hover:underline flex items-center gap-1"
                    >
                      Source <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
