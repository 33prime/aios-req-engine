/**
 * PatchFeed Component
 *
 * Displays history of surgical updates (patches applied and escalated).
 * Phase 1: Surgical Updates for Features
 */

'use client'

import React, { useState } from 'react'
import { CheckCircle, AlertTriangle, Info, ExternalLink, ChevronDown, ChevronUp } from 'lucide-react'
import { EvidenceGroup } from '@/components/evidence/EvidenceChip'

interface PatchItem {
  id: string
  timestamp: string
  entityType: 'feature' | 'persona' | 'vp_step' | 'business_driver'
  entityName: string
  entityId: string
  changeSummary: string
  status: 'applied' | 'escalated'
  classification: {
    changeType: string
    severity: 'minor' | 'moderate' | 'major'
    rationale: string
  }
  evidence: Array<{
    chunkId: string
    signalId: string
    excerpt: string
    rationale?: string
    sourceType?: string
    sourceLabel?: string
    timestamp?: string
    page?: number
    confidence?: number
  }>
  fieldsModified: string[]
}

interface PatchFeedProps {
  projectId: string
  limit?: number
  className?: string
}

export default function PatchFeed({ projectId, limit = 20, className = '' }: PatchFeedProps) {
  const [patches, setPatches] = useState<PatchItem[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedPatch, setExpandedPatch] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'applied' | 'escalated'>('all')

  // TODO: Load patches from API
  // useEffect(() => {
  //   loadPatches()
  // }, [projectId, filter])

  const filteredPatches = patches.filter(
    (p) => filter === 'all' || p.status === filter
  )

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'minor':
        return 'text-green-600 bg-green-50 border-green-200'
      case 'moderate':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200'
      case 'major':
        return 'text-red-600 bg-red-50 border-red-200'
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getEntityIcon = (type: string) => {
    switch (type) {
      case 'feature':
        return '🎯'
      case 'persona':
        return '👤'
      case 'vp_step':
        return '⚡'
      case 'business_driver':
        return '📊'
      default:
        return '📦'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
    return date.toLocaleDateString()
  }

  if (loading && patches.length === 0) {
    return (
      <div className={`bg-white rounded-lg border border-gray-200 p-6 ${className}`}>
        <div className="animate-pulse space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-100 rounded"></div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className={`bg-white rounded-lg border border-gray-200 ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-gray-900">Patch Feed</h3>
          <span className="text-sm text-gray-500">Last {limit} updates</span>
        </div>

        {/* Filter Tabs */}
        <div className="flex gap-2">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              filter === 'all'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            All
          </button>
          <button
            onClick={() => setFilter('applied')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1 ${
              filter === 'applied'
                ? 'bg-green-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <CheckCircle className="h-3 w-3" />
            Auto-Applied
          </button>
          <button
            onClick={() => setFilter('escalated')}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors flex items-center gap-1 ${
              filter === 'escalated'
                ? 'bg-yellow-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            <AlertTriangle className="h-3 w-3" />
            Escalated
          </button>
        </div>
      </div>

      {/* Patch List */}
      <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
        {filteredPatches.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <Info className="h-12 w-12 mx-auto mb-3 text-gray-400" />
            <p className="font-medium">No patches yet</p>
            <p className="text-sm mt-1">
              {filter === 'all'
                ? 'Patches will appear here when signals are processed in maintenance mode'
                : `No ${filter} patches`}
            </p>
          </div>
        ) : (
          filteredPatches.map((patch) => (
            <div key={patch.id} className="p-4 hover:bg-gray-50 transition-colors">
              {/* Patch Header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-start gap-3 flex-1">
                  {/* Status Icon */}
                  <div className="flex-shrink-0 mt-1">
                    {patch.status === 'applied' ? (
                      <CheckCircle className="h-5 w-5 text-green-600" />
                    ) : (
                      <AlertTriangle className="h-5 w-5 text-yellow-600" />
                    )}
                  </div>

                  {/* Content */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-lg">{getEntityIcon(patch.entityType)}</span>
                      <span className="font-semibold text-gray-900">{patch.entityName}</span>
                      <span className={`text-xs px-2 py-0.5 rounded border ${getSeverityColor(patch.classification.severity)}`}>
                        {patch.classification.severity}
                      </span>
                    </div>

                    <p className="text-sm text-gray-700 mb-2">{patch.changeSummary}</p>

                    {/* Fields Modified */}
                    {patch.fieldsModified.length > 0 && (
                      <div className="flex flex-wrap gap-1 mb-2">
                        {patch.fieldsModified.map((field) => (
                          <span
                            key={field}
                            className="text-xs bg-gray-100 text-gray-700 px-2 py-0.5 rounded"
                          >
                            {field}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Evidence Preview */}
                    {patch.evidence.length > 0 && (
                      <div className="mt-2">
                        <EvidenceGroup
                          evidence={patch.evidence as any}
                          maxDisplay={3}
                        />
                      </div>
                    )}

                    {/* Expanded Details */}
                    {expandedPatch === patch.id && (
                      <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <h5 className="text-xs font-semibold text-gray-700 mb-1">
                          Classification Rationale:
                        </h5>
                        <p className="text-xs text-gray-600 mb-2">
                          {patch.classification.rationale}
                        </p>

                        <div className="flex gap-2 mt-3">
                          <button className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1">
                            <ExternalLink className="h-3 w-3" />
                            View Entity
                          </button>
                          {patch.status === 'applied' && (
                            <button className="text-xs text-red-600 hover:text-red-800">
                              Revert
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right Side */}
                <div className="flex flex-col items-end gap-1 ml-4">
                  <span className="text-xs text-gray-500">{formatTimestamp(patch.timestamp)}</span>
                  <button
                    onClick={() =>
                      setExpandedPatch(expandedPatch === patch.id ? null : patch.id)
                    }
                    className="text-xs text-blue-600 hover:text-blue-800 flex items-center gap-1"
                  >
                    {expandedPatch === patch.id ? (
                      <>
                        <ChevronUp className="h-3 w-3" />
                        Less
                      </>
                    ) : (
                      <>
                        <ChevronDown className="h-3 w-3" />
                        Details
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
