/**
 * ContextWindowTab - AI Context Viewer
 *
 * Shows the unified memory document that gets injected into the AI's context window.
 * Token usage bar, formatted/raw toggle, copy, refresh, section breakdown.
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { Copy, RefreshCw, AlertTriangle, Check } from 'lucide-react'
import { getMemoryContent } from '@/lib/api'
import type { UnifiedMemoryResponse } from '@/lib/api'
import { Markdown } from '@/components/ui/Markdown'

interface ContextWindowTabProps {
  projectId: string
  unifiedMemory: UnifiedMemoryResponse | null
  onRefresh: () => void
  isSynthesizing: boolean
}

const MAX_TOKENS = 4000

export function ContextWindowTab({
  projectId,
  unifiedMemory,
  onRefresh,
  isSynthesizing,
}: ContextWindowTabProps) {
  const [viewMode, setViewMode] = useState<'formatted' | 'raw'>('formatted')
  const [copied, setCopied] = useState(false)
  const [memoryContent, setMemoryContent] = useState<{
    content: string | null
    tokens_estimate: number | null
  } | null>(null)

  useEffect(() => {
    getMemoryContent(projectId)
      .then(setMemoryContent)
      .catch(() => setMemoryContent(null))
  }, [projectId])

  const content = unifiedMemory?.content || memoryContent?.content || ''
  const tokensEstimate = memoryContent?.tokens_estimate || Math.round(content.length / 4)
  const tokenPct = Math.min(100, Math.round((tokensEstimate / MAX_TOKENS) * 100))

  // Compute section-level token breakdown
  const sectionBreakdown = useMemo(() => {
    if (!content) return []
    const sections = content.split(/^## /m)
    return sections
      .filter((s) => s.trim())
      .map((s) => {
        const firstLine = s.split('\n')[0].trim()
        const label = firstLine.startsWith('#') ? firstLine.replace(/^#+\s*/, '') : firstLine
        const tokens = Math.round(s.length / 4)
        return { label: label || 'Header', tokens }
      })
  }, [content])

  const handleCopy = async () => {
    if (!content) return
    await navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-4">
      {/* 1. Token usage bar */}
      <div>
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-semibold text-ui-headingDark">
            {tokensEstimate.toLocaleString()} / {MAX_TOKENS.toLocaleString()} tokens used
          </span>
          <span className="text-[11px] text-ui-supportText">{tokenPct}%</span>
        </div>
        <div className="h-2 rounded-full bg-gray-100 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              tokenPct > 90 ? 'bg-gray-400' : 'bg-brand-teal'
            }`}
            style={{ width: `${tokenPct}%` }}
          />
        </div>
      </div>

      {/* 2. Freshness + actions row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {unifiedMemory?.freshness && (
            <span className="text-[11px] text-ui-supportText">
              Last synthesized: {unifiedMemory.freshness.age_human}
            </span>
          )}
          {unifiedMemory?.is_stale && (
            <span className="inline-flex items-center gap-1 text-[11px] text-gray-500">
              <AlertTriangle className="w-3 h-3" />
              Stale
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onRefresh}
            disabled={isSynthesizing}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-brand-teal hover:bg-brand-teal/10 rounded-lg transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${isSynthesizing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-medium text-ui-supportText hover:text-ui-headingDark hover:bg-ui-background rounded-lg transition-colors"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>

      {/* 3. View toggle */}
      <div className="flex gap-1">
        <button
          onClick={() => setViewMode('formatted')}
          className={`px-3 py-1 rounded-lg text-[12px] font-medium transition-colors ${
            viewMode === 'formatted'
              ? 'bg-brand-teal/10 text-brand-teal'
              : 'text-ui-supportText hover:text-ui-headingDark'
          }`}
        >
          Formatted
        </button>
        <button
          onClick={() => setViewMode('raw')}
          className={`px-3 py-1 rounded-lg text-[12px] font-medium transition-colors ${
            viewMode === 'raw'
              ? 'bg-brand-teal/10 text-brand-teal'
              : 'text-ui-supportText hover:text-ui-headingDark'
          }`}
        >
          Raw Markdown
        </button>
      </div>

      {/* Content display */}
      {content ? (
        viewMode === 'formatted' ? (
          <div className="bg-ui-background rounded-lg p-5">
            <Markdown
              content={content}
              className="text-sm text-ui-bodyText prose prose-sm max-w-none [&_h1]:text-sm [&_h1]:font-bold [&_h1]:text-ui-headingDark [&_h2]:text-[13px] [&_h2]:font-semibold [&_h2]:text-ui-headingDark [&_h3]:text-[13px] [&_h3]:font-medium [&_p]:text-sm [&_p]:text-ui-bodyText [&_li]:text-sm [&_li]:text-ui-bodyText [&_strong]:text-ui-headingDark"
            />
          </div>
        ) : (
          <pre className="text-xs font-mono bg-gray-50 p-4 rounded-lg overflow-x-auto whitespace-pre-wrap text-ui-bodyText">
            {content}
          </pre>
        )
      ) : (
        <div className="text-center py-8">
          <p className="text-sm text-ui-supportText">
            No unified memory synthesized yet. Click &quot;Refresh&quot; to generate.
          </p>
        </div>
      )}

      {/* 4. Token breakdown */}
      {sectionBreakdown.length > 0 && (
        <div>
          <h5 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-2">
            Token Breakdown
          </h5>
          <div className="space-y-1.5">
            {sectionBreakdown.map((section, i) => {
              const sectionPct = Math.min(100, Math.round((section.tokens / tokensEstimate) * 100))
              return (
                <div key={i} className="flex items-center gap-2">
                  <span className="text-[11px] text-ui-bodyText w-40 truncate flex-shrink-0">
                    {section.label}
                  </span>
                  <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-brand-teal/50 transition-all"
                      style={{ width: `${sectionPct}%` }}
                    />
                  </div>
                  <span className="text-[10px] text-ui-supportText w-12 text-right flex-shrink-0">
                    ~{section.tokens}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
