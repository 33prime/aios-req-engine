'use client'

import { useState, useMemo } from 'react'
import type { FeatureOverlay } from '@/types/prototype'

interface FeatureOverlayPanelProps {
  overlays: FeatureOverlay[]
  activeFeatureId: string | null
  onFeatureSelect: (featureId: string | null) => void
}

const STATUS_STYLES = {
  understood: 'bg-emerald-100 text-emerald-800',
  partial: 'bg-brand-primary-light text-brand-primary',
  unknown: 'bg-gray-100 text-gray-600',
}

const IMPL_STATUS_LABELS: Record<string, string> = {
  functional: 'Functional',
  partial: 'Partial',
  placeholder: 'Placeholder',
}

/**
 * Right sidebar showing feature overlays during prototype review.
 * Expandable cards with overview delta, gaps, and persona impact.
 */
export default function FeatureOverlayPanel({
  overlays,
  activeFeatureId,
  onFeatureSelect,
}: FeatureOverlayPanelProps) {
  const [searchTerm, setSearchTerm] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  // Auto-expand active feature
  const effectiveExpandedId = activeFeatureId || expandedId

  const filtered = useMemo(() => {
    if (!searchTerm) return overlays
    const term = searchTerm.toLowerCase()
    return overlays.filter(
      (o) =>
        o.overlay_content?.feature_name.toLowerCase().includes(term) ||
        o.handoff_feature_name?.toLowerCase().includes(term)
    )
  }, [overlays, searchTerm])

  const understood = overlays.filter((o) => o.status === 'understood').length
  const total = overlays.length

  return (
    <div className="w-[380px] flex-shrink-0 bg-white border-l border-border flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-text-body">Feature Overlays</h3>
          <span className="text-[12px] text-text-placeholder">
            {understood}/{total}
          </span>
        </div>
        <input
          type="text"
          placeholder="Search features..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-3 py-1.5 text-sm border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
        />
      </div>

      {/* Overlay cards */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 custom-scrollbar">
        {filtered.map((overlay) => {
          const content = overlay.overlay_content
          const featureName = content?.feature_name || overlay.handoff_feature_name || 'Unknown'
          const isExpanded = effectiveExpandedId === overlay.feature_id
          const isActive = activeFeatureId === overlay.feature_id

          return (
            <div
              key={overlay.id}
              className={`border rounded-lg transition-all duration-200 ${
                isActive
                  ? 'border-brand-primary bg-brand-primary-light'
                  : 'border-border bg-white hover:border-brand-primary'
              }`}
            >
              {/* Card header — always visible */}
              <button
                className="w-full px-4 py-3 flex items-center justify-between text-left"
                onClick={() => {
                  const newId = isExpanded ? null : overlay.feature_id
                  setExpandedId(newId)
                  onFeatureSelect(newId)
                }}
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs text-text-placeholder">
                    {isExpanded ? '\u25BC' : '\u25B6'}
                  </span>
                  <span className="text-sm font-medium text-text-body truncate">
                    {featureName}
                  </span>
                </div>
                <span
                  className={`text-xs font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${
                    STATUS_STYLES[overlay.status as keyof typeof STATUS_STYLES] || STATUS_STYLES.unknown
                  }`}
                >
                  {overlay.status}
                </span>
              </button>

              {/* Expanded content */}
              {isExpanded && content && (
                <div className="px-4 pb-4 space-y-3 border-t border-border/50">
                  {/* Confidence + implementation status */}
                  <div className="flex items-center gap-4 pt-3 text-[12px] text-text-placeholder">
                    <span>Confidence: {Math.round(content.confidence * 100)}%</span>
                    {content.overview?.implementation_status && (
                      <span>{IMPL_STATUS_LABELS[content.overview.implementation_status] || content.overview.implementation_status}</span>
                    )}
                  </div>

                  {/* Delta */}
                  {content.overview?.delta && content.overview.delta.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-text-body uppercase tracking-wide mb-1">
                        Spec vs Code Gaps
                      </h4>
                      <ul className="space-y-0.5">
                        {content.overview.delta.map((d, i) => (
                          <li key={i} className="text-sm text-text-body flex items-start gap-1.5">
                            <span className="text-text-placeholder mt-1">&bull;</span>
                            {d}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Gap questions */}
                  {content.gaps && content.gaps.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-text-body uppercase tracking-wide mb-1">
                        Gap Questions ({content.gaps.length})
                      </h4>
                      <ul className="space-y-1">
                        {content.gaps.map((g, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-text-body">
                            <span className="mt-1.5 w-2 h-2 rounded-full flex-shrink-0 bg-brand-primary" />
                            <span>{g.question}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Personas affected */}
                  {content.impact?.personas_affected && content.impact.personas_affected.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-text-body uppercase tracking-wide mb-1">
                        Personas Affected
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {content.impact.personas_affected.map((p, i) => (
                          <span
                            key={i}
                            className="text-[12px] bg-surface-subtle px-2 py-0.5 rounded"
                            title={p.how_affected}
                          >
                            {p.name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Downstream risk */}
                  {content.impact?.downstream_risk && (
                    <div>
                      <h4 className="text-xs font-semibold text-text-body uppercase tracking-wide mb-1">
                        Downstream Risk
                      </h4>
                      <p className="text-sm text-text-body">{content.impact.downstream_risk}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {filtered.length === 0 && (
          <p className="text-sm text-text-placeholder text-center py-8">
            {searchTerm ? 'No features match your search.' : 'No overlays yet.'}
          </p>
        )}
      </div>
    </div>
  )
}
