/**
 * ResearchList Component
 *
 * Left column: Displays list of research query history
 */

'use client'

import { Button } from '@/components/ui'
import { Search, CheckCircle, XCircle, Clock } from 'lucide-react'
import type { Job } from '@/types/api'

interface ResearchListProps {
  jobs: Job[]
  selectedId: string | null
  onSelect: (job: Job) => void
  onRunResearch: () => void
}

export function ResearchList({ jobs, selectedId, onSelect, onRunResearch }: ResearchListProps) {
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-600" />
      default:
        return <Clock className="h-4 w-4 text-yellow-600" />
    }
  }

  const getTimeAgo = (timestamp: string) => {
    const now = new Date()
    const past = new Date(timestamp)
    const diffMs = now.getTime() - past.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return `${diffDays}d ago`
  }

  return (
    <div className="space-y-4">
      {/* Header with Run Research button */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-ui-bodyText">Research History</h3>
        <Button
          variant="primary"
          size="sm"
          icon={<Search className="h-4 w-4" />}
          onClick={onRunResearch}
        >
          New Research
        </Button>
      </div>

      {/* Jobs list */}
      <div className="space-y-2">
        {jobs.length === 0 ? (
          <div className="text-center py-12 bg-ui-background rounded-lg border border-ui-cardBorder">
            <Search className="h-12 w-12 text-ui-supportText mx-auto mb-3" />
            <p className="text-sm text-ui-bodyText mb-1">No research queries yet</p>
            <p className="text-xs text-ui-supportText">Click "New Research" to get started</p>
          </div>
        ) : (
          jobs.map((job) => {
            const findings = job.output?.findings_summary || {}
            const totalFindings = Object.values(findings).reduce((sum: number, val: any) => sum + (val || 0), 0)

            return (
              <button
                key={job.id}
                onClick={() => onSelect(job)}
                className={`w-full p-4 rounded-lg border text-left transition-colors ${
                  selectedId === job.id
                    ? 'border-brand-primary bg-brand-primary/5'
                    : 'border-ui-cardBorder hover:border-brand-primary/50 hover:bg-ui-cardBg'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {getStatusIcon(job.status)}
                      <span className="text-sm font-medium text-ui-bodyText">
                        {job.input?.seed_context?.client_name || 'Research Query'}
                      </span>
                    </div>
                    <p className="text-xs text-ui-supportText">
                      {job.input?.seed_context?.industry || 'General research'}
                    </p>
                  </div>
                  <span className="text-xs text-ui-supportText whitespace-nowrap">
                    {getTimeAgo(job.created_at)}
                  </span>
                </div>

                {job.status === 'completed' && (
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded">
                      {totalFindings} findings
                    </span>
                    <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-700 rounded">
                      {job.output?.queries_executed || 0} queries
                    </span>
                  </div>
                )}
              </button>
            )
          })
        )}
      </div>
    </div>
  )
}
