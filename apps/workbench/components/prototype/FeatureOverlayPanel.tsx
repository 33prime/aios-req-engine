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
  partial: 'bg-brand-accent/10 text-brand-primary',
  unknown: 'bg-gray-100 text-gray-600',
}

const PRIORITY_DOT = {
  high: 'bg-brand-primary',
  medium: 'bg-brand-accent',
  low: 'bg-gray-300',
}

/**
 * Right sidebar showing feature overlays during prototype review.
 * Expandable cards with analysis data, questions, and personas.
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
    <div className="w-[380px] flex-shrink-0 bg-white border-l border-ui-cardBorder flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-ui-cardBorder">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-semibold text-ui-headingDark">Feature Overlays</h3>
          <span className="text-support text-ui-supportText">
            {understood}/{total}
          </span>
        </div>
        <input
          type="text"
          placeholder="Search features..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full px-3 py-1.5 text-sm border border-ui-cardBorder rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-primary/20 focus:border-brand-primary"
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
              className={`border rounded-card transition-all duration-200 ${
                isActive
                  ? 'border-brand-primary bg-brand-primary/[0.02]'
                  : 'border-ui-cardBorder bg-white hover:border-brand-accent'
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
                  <span className="text-xs text-ui-supportText">
                    {isExpanded ? '\u25BC' : '\u25B6'}
                  </span>
                  <span className="text-sm font-medium text-ui-headingDark truncate">
                    {featureName}
                  </span>
                </div>
                <span
                  className={`text-badge px-2 py-0.5 rounded-full whitespace-nowrap ${
                    STATUS_STYLES[overlay.status as keyof typeof STATUS_STYLES] || STATUS_STYLES.unknown
                  }`}
                >
                  {overlay.status}
                </span>
              </button>

              {/* Expanded content */}
              {isExpanded && content && (
                <div className="px-4 pb-4 space-y-3 border-t border-ui-cardBorder/50">
                  {/* Confidence + gaps */}
                  <div className="flex items-center gap-4 pt-3 text-support text-ui-supportText">
                    <span>Confidence: {Math.round(content.confidence * 100)}%</span>
                    <span>{content.gaps_count} gaps remaining</span>
                  </div>

                  {/* Triggers */}
                  {content.triggers.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">
                        Triggers
                      </h4>
                      <ul className="space-y-0.5">
                        {content.triggers.map((t, i) => (
                          <li key={i} className="text-sm text-ui-bodyText flex items-start gap-1.5">
                            <span className="text-ui-supportText mt-1">&bull;</span>
                            {t}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Questions */}
                  {content.questions.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">
                        Questions ({content.questions.length})
                      </h4>
                      <ul className="space-y-1">
                        {content.questions.map((q, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-ui-bodyText">
                            <span
                              className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${
                                PRIORITY_DOT[q.priority as keyof typeof PRIORITY_DOT] || PRIORITY_DOT.low
                              }`}
                            />
                            <span className={q.answer ? 'line-through text-ui-supportText' : ''}>
                              {q.question}
                            </span>
                            <span className="text-badge text-ui-supportText ml-auto flex-shrink-0">
                              {q.priority[0].toUpperCase()}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Personas */}
                  {content.personas.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">
                        Used by
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {content.personas.map((p) => (
                          <span
                            key={p.persona_id}
                            className="text-support bg-ui-buttonGray px-2 py-0.5 rounded"
                          >
                            {p.persona_name}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Dependencies */}
                  {content.dependencies.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">
                        Dependencies
                      </h4>
                      <ul className="space-y-0.5">
                        {content.dependencies.map((d, i) => (
                          <li key={i} className="text-sm text-ui-bodyText">
                            {d.direction === 'upstream' ? '\u2192' : '\u2190'} {d.feature_name}
                            {d.relationship && (
                              <span className="text-ui-supportText"> ({d.relationship})</span>
                            )}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Business rules */}
                  {content.business_rules.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-ui-headingDark uppercase tracking-wide mb-1">
                        Business Rules
                      </h4>
                      <ul className="space-y-0.5">
                        {content.business_rules.map((br, i) => (
                          <li key={i} className="text-sm text-ui-bodyText flex items-start gap-1.5">
                            <span
                              className={`text-badge mt-0.5 ${
                                br.source === 'confirmed'
                                  ? 'text-emerald-700'
                                  : br.source === 'aios'
                                    ? 'text-brand-primary'
                                    : 'text-ui-supportText'
                              }`}
                            >
                              [{br.source}]
                            </span>
                            <span>{br.rule}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}

        {filtered.length === 0 && (
          <p className="text-sm text-ui-supportText text-center py-8">
            {searchTerm ? 'No features match your search.' : 'No overlays yet.'}
          </p>
        )}
      </div>
    </div>
  )
}
